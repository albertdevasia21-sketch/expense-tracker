from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import hashlib
import jwt
import csv
import io
from fastapi.responses import StreamingResponse

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Settings
JWT_SECRET = os.environ.get('JWT_SECRET', 'expense-tracker-secret-key-2024')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Create the main app
app = FastAPI()
api_router = APIRouter(prefix="/api")
security = HTTPBearer()

# ==================== MODELS ====================

class UserCreate(BaseModel):
    email: str
    password: str
    name: str = "User"

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    household_id: str
    currency: str = "CAD"
    timezone: str = "America/Toronto"

class HouseholdMember(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    household_id: str
    name: str
    color: str = "#3B82F6"
    avatar_url: Optional[str] = None
    is_active: bool = True
    is_default: bool = False

class HouseholdMemberCreate(BaseModel):
    name: str
    color: str = "#3B82F6"
    avatar_url: Optional[str] = None
    is_default: bool = False

class Category(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    household_id: str
    group_name: str
    category_name: str
    type: str  # expense | income
    is_fixed: bool = False
    sort_order: int = 0
    is_active: bool = True
    color: str = "#64748B"  # Category color for charts

class CategoryCreate(BaseModel):
    group_name: str
    category_name: str
    type: str = "expense"
    is_fixed: bool = False
    sort_order: int = 0
    color: str = "#64748B"

# Subcategory model
class Subcategory(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    household_id: str
    category_id: str
    name: str
    sort_order: int = 0
    is_active: bool = True

class SubcategoryCreate(BaseModel):
    category_id: str
    name: str
    sort_order: int = 0

class Merchant(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    household_id: str
    name: str
    default_category_id: Optional[str] = None

class MerchantCreate(BaseModel):
    name: str
    default_category_id: Optional[str] = None

class Account(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    household_id: str
    name: str
    type: str  # cash | checking | savings | credit | loan | other
    opening_balance: float = 0
    is_active: bool = True

class AccountCreate(BaseModel):
    name: str
    type: str
    opening_balance: float = 0

class Transaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    household_id: str
    date: str  # YYYY-MM-DD
    amount: float
    type: str  # income | expense | transfer
    merchant_id: Optional[str] = None
    merchant_name: Optional[str] = None
    category_id: Optional[str] = None
    subcategory_id: Optional[str] = None
    account_id: Optional[str] = None
    member_id: Optional[str] = None
    notes: Optional[str] = None
    tags: List[str] = []
    is_recurring_instance: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class TransactionCreate(BaseModel):
    date: str
    amount: float
    type: str
    merchant_id: Optional[str] = None
    merchant_name: Optional[str] = None
    category_id: Optional[str] = None
    subcategory_id: Optional[str] = None
    account_id: Optional[str] = None
    member_id: Optional[str] = None
    notes: Optional[str] = None
    tags: List[str] = []
    is_recurring_instance: bool = False

class TransactionUpdate(BaseModel):
    date: Optional[str] = None
    amount: Optional[float] = None
    type: Optional[str] = None
    merchant_id: Optional[str] = None
    merchant_name: Optional[str] = None
    category_id: Optional[str] = None
    subcategory_id: Optional[str] = None
    account_id: Optional[str] = None
    member_id: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None

class Budget(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    household_id: str
    month: str  # YYYY-MM
    category_group: Optional[str] = None
    category_id: Optional[str] = None
    amount: float
    rollover: bool = False

class BudgetCreate(BaseModel):
    month: str
    category_group: Optional[str] = None
    category_id: Optional[str] = None
    amount: float
    rollover: bool = False

class RecurringRule(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    household_id: str
    name: str
    type: str  # income | expense
    amount: float
    frequency: str  # weekly | biweekly | monthly | yearly
    next_date: str  # YYYY-MM-DD
    category_id: Optional[str] = None
    account_id: Optional[str] = None
    member_id: Optional[str] = None
    autopost: bool = False
    notes: Optional[str] = None
    active: bool = True

class RecurringRuleCreate(BaseModel):
    name: str
    type: str
    amount: float
    frequency: str
    next_date: str
    category_id: Optional[str] = None
    account_id: Optional[str] = None
    member_id: Optional[str] = None
    autopost: bool = False
    notes: Optional[str] = None

class Goal(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    household_id: str
    name: str
    target_amount: float
    target_date: Optional[str] = None
    current_amount: float = 0
    icon: Optional[str] = None
    color: str = "#3B82F6"
    active: bool = True

class GoalCreate(BaseModel):
    name: str
    target_amount: float
    target_date: Optional[str] = None
    current_amount: float = 0
    icon: Optional[str] = None
    color: str = "#3B82F6"

class Tag(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    household_id: str
    name: str
    color: str = "#64748B"

class TagCreate(BaseModel):
    name: str
    color: str = "#64748B"

class Rule(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    household_id: str
    merchant_contains: str
    set_category_id: Optional[str] = None
    set_member_id: Optional[str] = None
    active: bool = True

class RuleCreate(BaseModel):
    merchant_contains: str
    set_category_id: Optional[str] = None
    set_member_id: Optional[str] = None

class SettingsUpdate(BaseModel):
    name: Optional[str] = None
    currency: Optional[str] = None
    timezone: Optional[str] = None

# ==================== HELPERS ====================

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def create_token(user_id: str, household_id: str) -> str:
    payload = {
        "user_id": user_id,
        "household_id": household_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user = await db.users.find_one({"id": payload["user_id"]}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ==================== DEFAULT DATA ====================

# Category colors for consistent visualization
CATEGORY_COLORS = {
    "Housing": "#8B5CF6",
    "Transportation": "#F59E0B",
    "Utilities": "#06B6D4",
    "Insurance": "#EC4899",
    "Subscriptions": "#6366F1",
    "Food": "#10B981",
    "Shopping": "#F97316",
    "Health": "#EF4444",
    "Entertainment": "#A855F7",
    "Travel": "#3B82F6",
    "Gifts & Donations": "#14B8A6",
    "Other": "#64748B",
    "Income": "#22C55E",
}

DEFAULT_CATEGORIES = [
    # Fixed Expenses
    {"group_name": "Housing", "category_name": "Rent", "type": "expense", "is_fixed": True, "sort_order": 1, "color": "#8B5CF6"},
    {"group_name": "Housing", "category_name": "Maintenance/Repairs", "type": "expense", "is_fixed": True, "sort_order": 2, "color": "#8B5CF6"},
    {"group_name": "Transportation", "category_name": "Car Loan", "type": "expense", "is_fixed": True, "sort_order": 3, "color": "#F59E0B"},
    {"group_name": "Transportation", "category_name": "Fuel", "type": "expense", "is_fixed": True, "sort_order": 4, "color": "#F59E0B"},
    {"group_name": "Transportation", "category_name": "Insurance (Vehicle)", "type": "expense", "is_fixed": True, "sort_order": 5, "color": "#F59E0B"},
    {"group_name": "Transportation", "category_name": "Maintenance", "type": "expense", "is_fixed": True, "sort_order": 6, "color": "#F59E0B"},
    {"group_name": "Transportation", "category_name": "Parking/Tolls", "type": "expense", "is_fixed": True, "sort_order": 7, "color": "#F59E0B"},
    {"group_name": "Transportation", "category_name": "Transit", "type": "expense", "is_fixed": True, "sort_order": 8, "color": "#F59E0B"},
    {"group_name": "Utilities", "category_name": "Electricity", "type": "expense", "is_fixed": True, "sort_order": 9, "color": "#06B6D4"},
    {"group_name": "Utilities", "category_name": "Water", "type": "expense", "is_fixed": True, "sort_order": 10, "color": "#06B6D4"},
    {"group_name": "Utilities", "category_name": "Internet", "type": "expense", "is_fixed": True, "sort_order": 11, "color": "#06B6D4"},
    {"group_name": "Utilities", "category_name": "Mobile Plan", "type": "expense", "is_fixed": True, "sort_order": 12, "color": "#06B6D4"},
    {"group_name": "Insurance", "category_name": "Health Insurance", "type": "expense", "is_fixed": True, "sort_order": 13, "color": "#EC4899"},
    {"group_name": "Insurance", "category_name": "Life Insurance", "type": "expense", "is_fixed": True, "sort_order": 14, "color": "#EC4899"},
    {"group_name": "Insurance", "category_name": "Other Insurance", "type": "expense", "is_fixed": True, "sort_order": 15, "color": "#EC4899"},
    {"group_name": "Subscriptions", "category_name": "Streaming", "type": "expense", "is_fixed": True, "sort_order": 16, "color": "#6366F1"},
    {"group_name": "Subscriptions", "category_name": "Software/Apps", "type": "expense", "is_fixed": True, "sort_order": 17, "color": "#6366F1"},
    {"group_name": "Subscriptions", "category_name": "Memberships", "type": "expense", "is_fixed": True, "sort_order": 18, "color": "#6366F1"},
    # Flexible Expenses
    {"group_name": "Food", "category_name": "Groceries", "type": "expense", "is_fixed": False, "sort_order": 19, "color": "#10B981"},
    {"group_name": "Food", "category_name": "Dining Out", "type": "expense", "is_fixed": False, "sort_order": 20, "color": "#10B981"},
    {"group_name": "Shopping", "category_name": "Clothing", "type": "expense", "is_fixed": False, "sort_order": 21, "color": "#F97316"},
    {"group_name": "Shopping", "category_name": "Household Items", "type": "expense", "is_fixed": False, "sort_order": 22, "color": "#F97316"},
    {"group_name": "Shopping", "category_name": "Personal Care", "type": "expense", "is_fixed": False, "sort_order": 23, "color": "#F97316"},
    {"group_name": "Health", "category_name": "Pharmacy", "type": "expense", "is_fixed": False, "sort_order": 24, "color": "#EF4444"},
    {"group_name": "Health", "category_name": "Medical", "type": "expense", "is_fixed": False, "sort_order": 25, "color": "#EF4444"},
    {"group_name": "Health", "category_name": "Fitness", "type": "expense", "is_fixed": False, "sort_order": 26, "color": "#EF4444"},
    {"group_name": "Entertainment", "category_name": "Movies/Events", "type": "expense", "is_fixed": False, "sort_order": 27, "color": "#A855F7"},
    {"group_name": "Entertainment", "category_name": "Hobbies", "type": "expense", "is_fixed": False, "sort_order": 28, "color": "#A855F7"},
    {"group_name": "Travel", "category_name": "Flights", "type": "expense", "is_fixed": False, "sort_order": 29, "color": "#3B82F6"},
    {"group_name": "Travel", "category_name": "Hotels", "type": "expense", "is_fixed": False, "sort_order": 30, "color": "#3B82F6"},
    {"group_name": "Travel", "category_name": "Local Travel", "type": "expense", "is_fixed": False, "sort_order": 31, "color": "#3B82F6"},
    {"group_name": "Gifts & Donations", "category_name": "Gifts", "type": "expense", "is_fixed": False, "sort_order": 32, "color": "#14B8A6"},
    {"group_name": "Gifts & Donations", "category_name": "Charity", "type": "expense", "is_fixed": False, "sort_order": 33, "color": "#14B8A6"},
    {"group_name": "Other", "category_name": "Miscellaneous", "type": "expense", "is_fixed": False, "sort_order": 34, "color": "#64748B"},
    {"group_name": "Other", "category_name": "One-time Expenses", "type": "expense", "is_fixed": False, "sort_order": 35, "color": "#64748B"},
    # Income
    {"group_name": "Income", "category_name": "Salary", "type": "income", "is_fixed": False, "sort_order": 36, "color": "#22C55E"},
    {"group_name": "Income", "category_name": "Freelance", "type": "income", "is_fixed": False, "sort_order": 37, "color": "#22C55E"},
    {"group_name": "Income", "category_name": "Investment", "type": "income", "is_fixed": False, "sort_order": 38, "color": "#22C55E"},
    {"group_name": "Income", "category_name": "Other Income", "type": "income", "is_fixed": False, "sort_order": 39, "color": "#22C55E"},
]

# Default subcategories for each category
DEFAULT_SUBCATEGORIES = {
    "Groceries": ["General", "Produce", "Meat & Seafood", "Dairy", "Frozen", "Snacks", "Beverages"],
    "Dining Out": ["General", "Restaurants", "Fast Food", "Coffee Shops", "Delivery"],
    "Clothing": ["General", "Work Clothes", "Casual", "Shoes", "Accessories"],
    "Fuel": ["General", "Gas", "Electric Charging"],
    "Entertainment": ["General", "Movies", "Concerts", "Sports Events"],
    "Streaming": ["General", "Video", "Music", "Gaming"],
}

async def create_default_data(household_id: str, me_member_id: str, wife_member_id: str):
    """Create default categories, subcategories, accounts, and seed data for a new household"""
    
    # Create categories
    categories = []
    category_map = {}
    for cat_data in DEFAULT_CATEGORIES:
        cat = Category(
            household_id=household_id,
            **cat_data
        )
        categories.append(cat.model_dump())
        category_map[f"{cat_data['group_name']}_{cat_data['category_name']}"] = cat.id
        category_map[cat_data['category_name']] = cat.id  # Also map by name for subcategories
    
    if categories:
        await db.categories.insert_many(categories)
    
    # Create default subcategories
    subcategories = []
    for cat_name, subcat_names in DEFAULT_SUBCATEGORIES.items():
        cat_id = category_map.get(cat_name)
        if cat_id:
            for idx, subcat_name in enumerate(subcat_names):
                subcat = Subcategory(
                    household_id=household_id,
                    category_id=cat_id,
                    name=subcat_name,
                    sort_order=idx
                )
                subcategories.append(subcat.model_dump())
    
    if subcategories:
        await db.subcategories.insert_many(subcategories)
    
    # Create default accounts
    accounts = [
        Account(household_id=household_id, name="Checking Account", type="checking", opening_balance=5000),
        Account(household_id=household_id, name="Savings Account", type="savings", opening_balance=10000),
        Account(household_id=household_id, name="Credit Card", type="credit", opening_balance=0),
        Account(household_id=household_id, name="Cash", type="cash", opening_balance=200),
    ]
    account_docs = [a.model_dump() for a in accounts]
    await db.accounts.insert_many(account_docs)
    checking_id = accounts[0].id
    credit_id = accounts[2].id
    
    # Create seed transactions for current month
    today = datetime.now(timezone.utc)
    current_month = today.strftime("%Y-%m")
    
    transactions = [
        # Me's transactions
        Transaction(household_id=household_id, date=f"{current_month}-01", amount=5000, type="income",
                   merchant_name="Employer Inc", category_id=category_map.get("Income_Salary"),
                   account_id=checking_id, member_id=me_member_id, notes="Monthly salary"),
        Transaction(household_id=household_id, date=f"{current_month}-03", amount=-1800, type="expense",
                   merchant_name="Landlord", category_id=category_map.get("Housing_Rent"),
                   account_id=checking_id, member_id=me_member_id, notes="Monthly rent"),
        Transaction(household_id=household_id, date=f"{current_month}-05", amount=-85, type="expense",
                   merchant_name="Costco", category_id=category_map.get("Food_Groceries"),
                   account_id=credit_id, member_id=me_member_id),
        Transaction(household_id=household_id, date=f"{current_month}-07", amount=-45, type="expense",
                   merchant_name="Shell Gas", category_id=category_map.get("Transportation_Fuel"),
                   account_id=credit_id, member_id=me_member_id),
        Transaction(household_id=household_id, date=f"{current_month}-10", amount=-65, type="expense",
                   merchant_name="Rogers", category_id=category_map.get("Utilities_Mobile Plan"),
                   account_id=checking_id, member_id=me_member_id),
        
        # Wife's transactions
        Transaction(household_id=household_id, date=f"{current_month}-01", amount=4200, type="income",
                   merchant_name="Company ABC", category_id=category_map.get("Income_Salary"),
                   account_id=checking_id, member_id=wife_member_id, notes="Monthly salary"),
        Transaction(household_id=household_id, date=f"{current_month}-04", amount=-120, type="expense",
                   merchant_name="Loblaws", category_id=category_map.get("Food_Groceries"),
                   account_id=credit_id, member_id=wife_member_id),
        Transaction(household_id=household_id, date=f"{current_month}-06", amount=-75, type="expense",
                   merchant_name="The Restaurant", category_id=category_map.get("Food_Dining Out"),
                   account_id=credit_id, member_id=wife_member_id),
        Transaction(household_id=household_id, date=f"{current_month}-08", amount=-150, type="expense",
                   merchant_name="H&M", category_id=category_map.get("Shopping_Clothing"),
                   account_id=credit_id, member_id=wife_member_id),
        Transaction(household_id=household_id, date=f"{current_month}-12", amount=-80, type="expense",
                   merchant_name="Bell", category_id=category_map.get("Utilities_Internet"),
                   account_id=checking_id, member_id=wife_member_id),
    ]
    
    tx_docs = [t.model_dump() for t in transactions]
    await db.transactions.insert_many(tx_docs)
    
    # Create recurring rules
    recurring = [
        RecurringRule(household_id=household_id, name="Rent", type="expense", amount=-1800,
                     frequency="monthly", next_date=f"{current_month}-01",
                     category_id=category_map.get("Housing_Rent"), account_id=checking_id,
                     member_id=me_member_id, autopost=False),
        RecurringRule(household_id=household_id, name="Mobile Plan - Me", type="expense", amount=-65,
                     frequency="monthly", next_date=f"{current_month}-10",
                     category_id=category_map.get("Utilities_Mobile Plan"), account_id=checking_id,
                     member_id=me_member_id, autopost=False),
        RecurringRule(household_id=household_id, name="Internet", type="expense", amount=-80,
                     frequency="monthly", next_date=f"{current_month}-12",
                     category_id=category_map.get("Utilities_Internet"), account_id=checking_id,
                     member_id=wife_member_id, autopost=False),
        RecurringRule(household_id=household_id, name="Paycheck - Me", type="income", amount=5000,
                     frequency="monthly", next_date=f"{current_month}-01",
                     category_id=category_map.get("Income_Salary"), account_id=checking_id,
                     member_id=me_member_id, autopost=False),
    ]
    
    rec_docs = [r.model_dump() for r in recurring]
    await db.recurring_rules.insert_many(rec_docs)
    
    # Create goals
    goals = [
        Goal(household_id=household_id, name="Vacation Fund", target_amount=5000,
             target_date="2025-12-31", current_amount=1200, icon="plane", color="#3B82F6"),
        Goal(household_id=household_id, name="Emergency Fund", target_amount=15000,
             target_date="2026-06-30", current_amount=8500, icon="shield", color="#10B981"),
    ]
    
    goal_docs = [g.model_dump() for g in goals]
    await db.goals.insert_many(goal_docs)
    
    # Create budgets for current month
    budgets = [
        Budget(household_id=household_id, month=current_month, category_id=category_map.get("Housing_Rent"), amount=1800),
        Budget(household_id=household_id, month=current_month, category_id=category_map.get("Food_Groceries"), amount=600),
        Budget(household_id=household_id, month=current_month, category_id=category_map.get("Food_Dining Out"), amount=200),
        Budget(household_id=household_id, month=current_month, category_id=category_map.get("Transportation_Fuel"), amount=150),
        Budget(household_id=household_id, month=current_month, category_id=category_map.get("Shopping_Clothing"), amount=200),
        Budget(household_id=household_id, month=current_month, category_id=category_map.get("Utilities_Mobile Plan"), amount=130),
        Budget(household_id=household_id, month=current_month, category_id=category_map.get("Utilities_Internet"), amount=80),
    ]
    
    budget_docs = [b.model_dump() for b in budgets]
    await db.budgets.insert_many(budget_docs)

# ==================== AUTH ROUTES ====================

@api_router.post("/auth/register")
async def register(user_data: UserCreate):
    # Check if user exists
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create household
    household_id = str(uuid.uuid4())
    
    # Create user
    user_id = str(uuid.uuid4())
    user = {
        "id": user_id,
        "email": user_data.email,
        "password_hash": hash_password(user_data.password),
        "name": user_data.name,
        "household_id": household_id,
        "currency": "CAD",
        "timezone": "America/Toronto",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(user)
    
    # Create default household members
    me_member = HouseholdMember(
        household_id=household_id,
        name="Me",
        color="#3B82F6",
        avatar_url="https://images.unsplash.com/photo-1755519024827-fd05075a7200?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzNzl8MHwxfHNlYXJjaHwzfHxwb3J0cmFpdCUyMHNtaWxpbmclMjBtYW4lMjBwcm9mZXNzaW9uYWwlMjBwcm9maWxlJTIwcGljdHVyZXxlbnwwfHx8fDE3NzA2OTEzODZ8MA&ixlib=rb-4.1.0&q=85",
        is_default=True
    )
    wife_member = HouseholdMember(
        household_id=household_id,
        name="Wife",
        color="#EC4899",
        avatar_url="https://images.unsplash.com/photo-1590905775253-a4f0f3c426ff?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDQ2MzR8MHwxfHNlYXJjaHwxfHxwb3J0cmFpdCUyMHNtaWxpbmclMjBtYW4lMjB3b21hbiUyMHByb2Zlc3Npb25hbCUyMHByb2ZpbGUlMjBwaWN0dXJlfGVufDB8fHx8MTc3MDY5MTM2MXww&ixlib=rb-4.1.0&q=85"
    )
    await db.household_members.insert_many([me_member.model_dump(), wife_member.model_dump()])
    
    # Create default data
    await create_default_data(household_id, me_member.id, wife_member.id)
    
    # Generate token
    token = create_token(user_id, household_id)
    
    return {
        "token": token,
        "user": {
            "id": user_id,
            "email": user_data.email,
            "name": user_data.name,
            "household_id": household_id,
            "currency": "CAD",
            "timezone": "America/Toronto"
        }
    }

@api_router.post("/auth/login")
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if user["password_hash"] != hash_password(credentials.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_token(user["id"], user["household_id"])
    
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "household_id": user["household_id"],
            "currency": user.get("currency", "CAD"),
            "timezone": user.get("timezone", "America/Toronto")
        }
    }

@api_router.get("/auth/me")
async def get_me(user: dict = Depends(get_current_user)):
    return {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "household_id": user["household_id"],
        "currency": user.get("currency", "CAD"),
        "timezone": user.get("timezone", "America/Toronto")
    }

@api_router.put("/auth/settings")
async def update_settings(settings: SettingsUpdate, user: dict = Depends(get_current_user)):
    update_data = {k: v for k, v in settings.model_dump().items() if v is not None}
    if update_data:
        await db.users.update_one({"id": user["id"]}, {"$set": update_data})
    
    updated_user = await db.users.find_one({"id": user["id"]}, {"_id": 0, "password_hash": 0})
    return updated_user

# ==================== HOUSEHOLD MEMBERS ====================

@api_router.get("/household-members")
async def get_household_members(user: dict = Depends(get_current_user)):
    members = await db.household_members.find(
        {"household_id": user["household_id"], "is_active": True},
        {"_id": 0}
    ).to_list(100)
    return members

@api_router.post("/household-members")
async def create_household_member(member_data: HouseholdMemberCreate, user: dict = Depends(get_current_user)):
    member = HouseholdMember(
        household_id=user["household_id"],
        **member_data.model_dump()
    )
    await db.household_members.insert_one(member.model_dump())
    return member.model_dump()

@api_router.put("/household-members/{member_id}")
async def update_household_member(member_id: str, member_data: HouseholdMemberCreate, user: dict = Depends(get_current_user)):
    result = await db.household_members.update_one(
        {"id": member_id, "household_id": user["household_id"]},
        {"$set": member_data.model_dump()}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Member not found")
    
    member = await db.household_members.find_one({"id": member_id}, {"_id": 0})
    return member

@api_router.delete("/household-members/{member_id}")
async def delete_household_member(member_id: str, user: dict = Depends(get_current_user)):
    result = await db.household_members.update_one(
        {"id": member_id, "household_id": user["household_id"]},
        {"$set": {"is_active": False}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Member not found")
    return {"success": True}

# ==================== CATEGORIES ====================

@api_router.get("/categories")
async def get_categories(user: dict = Depends(get_current_user)):
    categories = await db.categories.find(
        {"household_id": user["household_id"], "is_active": True},
        {"_id": 0}
    ).sort("sort_order", 1).to_list(500)
    return categories

@api_router.post("/categories")
async def create_category(cat_data: CategoryCreate, user: dict = Depends(get_current_user)):
    category = Category(
        household_id=user["household_id"],
        **cat_data.model_dump()
    )
    await db.categories.insert_one(category.model_dump())
    return category.model_dump()

@api_router.put("/categories/{category_id}")
async def update_category(category_id: str, cat_data: CategoryCreate, user: dict = Depends(get_current_user)):
    result = await db.categories.update_one(
        {"id": category_id, "household_id": user["household_id"]},
        {"$set": cat_data.model_dump()}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Category not found")
    
    category = await db.categories.find_one({"id": category_id}, {"_id": 0})
    return category

@api_router.delete("/categories/{category_id}")
async def delete_category(category_id: str, user: dict = Depends(get_current_user)):
    result = await db.categories.update_one(
        {"id": category_id, "household_id": user["household_id"]},
        {"$set": {"is_active": False}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"success": True}

# ==================== SUBCATEGORIES ====================

@api_router.get("/subcategories")
async def get_subcategories(category_id: Optional[str] = None, user: dict = Depends(get_current_user)):
    query = {"household_id": user["household_id"], "is_active": True}
    if category_id:
        query["category_id"] = category_id
    
    subcategories = await db.subcategories.find(query, {"_id": 0}).sort("sort_order", 1).to_list(500)
    return subcategories

@api_router.post("/subcategories")
async def create_subcategory(subcat_data: SubcategoryCreate, user: dict = Depends(get_current_user)):
    subcategory = Subcategory(
        household_id=user["household_id"],
        **subcat_data.model_dump()
    )
    await db.subcategories.insert_one(subcategory.model_dump())
    return subcategory.model_dump()

@api_router.put("/subcategories/{subcategory_id}")
async def update_subcategory(subcategory_id: str, subcat_data: SubcategoryCreate, user: dict = Depends(get_current_user)):
    result = await db.subcategories.update_one(
        {"id": subcategory_id, "household_id": user["household_id"]},
        {"$set": subcat_data.model_dump()}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Subcategory not found")
    
    subcategory = await db.subcategories.find_one({"id": subcategory_id}, {"_id": 0})
    return subcategory

@api_router.delete("/subcategories/{subcategory_id}")
async def delete_subcategory(subcategory_id: str, user: dict = Depends(get_current_user)):
    result = await db.subcategories.update_one(
        {"id": subcategory_id, "household_id": user["household_id"]},
        {"$set": {"is_active": False}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Subcategory not found")
    return {"success": True}

# ==================== MERCHANTS ====================

@api_router.get("/merchants")
async def get_merchants(user: dict = Depends(get_current_user)):
    merchants = await db.merchants.find(
        {"household_id": user["household_id"]},
        {"_id": 0}
    ).to_list(500)
    return merchants

@api_router.post("/merchants")
async def create_merchant(merchant_data: MerchantCreate, user: dict = Depends(get_current_user)):
    merchant = Merchant(
        household_id=user["household_id"],
        **merchant_data.model_dump()
    )
    await db.merchants.insert_one(merchant.model_dump())
    return merchant.model_dump()

@api_router.put("/merchants/{merchant_id}")
async def update_merchant(merchant_id: str, merchant_data: MerchantCreate, user: dict = Depends(get_current_user)):
    result = await db.merchants.update_one(
        {"id": merchant_id, "household_id": user["household_id"]},
        {"$set": merchant_data.model_dump()}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Merchant not found")
    
    merchant = await db.merchants.find_one({"id": merchant_id}, {"_id": 0})
    return merchant

@api_router.delete("/merchants/{merchant_id}")
async def delete_merchant(merchant_id: str, user: dict = Depends(get_current_user)):
    result = await db.merchants.delete_one(
        {"id": merchant_id, "household_id": user["household_id"]}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Merchant not found")
    return {"success": True}

# ==================== ACCOUNTS ====================

@api_router.get("/accounts")
async def get_accounts(user: dict = Depends(get_current_user)):
    accounts = await db.accounts.find(
        {"household_id": user["household_id"], "is_active": True},
        {"_id": 0}
    ).to_list(100)
    
    # Calculate current balance for each account
    for account in accounts:
        transactions = await db.transactions.find(
            {"household_id": user["household_id"], "account_id": account["id"]}
        ).to_list(10000)
        total = sum(t["amount"] for t in transactions)
        account["current_balance"] = account["opening_balance"] + total
    
    return accounts

@api_router.post("/accounts")
async def create_account(account_data: AccountCreate, user: dict = Depends(get_current_user)):
    account = Account(
        household_id=user["household_id"],
        **account_data.model_dump()
    )
    await db.accounts.insert_one(account.model_dump())
    return account.model_dump()

@api_router.put("/accounts/{account_id}")
async def update_account(account_id: str, account_data: AccountCreate, user: dict = Depends(get_current_user)):
    result = await db.accounts.update_one(
        {"id": account_id, "household_id": user["household_id"]},
        {"$set": account_data.model_dump()}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Account not found")
    
    account = await db.accounts.find_one({"id": account_id}, {"_id": 0})
    return account

@api_router.delete("/accounts/{account_id}")
async def delete_account(account_id: str, user: dict = Depends(get_current_user)):
    result = await db.accounts.update_one(
        {"id": account_id, "household_id": user["household_id"]},
        {"$set": {"is_active": False}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"success": True}

# ==================== TRANSACTIONS ====================

@api_router.get("/transactions")
async def get_transactions(
    month: Optional[str] = None,
    member_id: Optional[str] = None,
    category_id: Optional[str] = None,
    subcategory_id: Optional[str] = None,
    account_id: Optional[str] = None,
    search: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    query = {"household_id": user["household_id"]}
    
    if month:
        query["date"] = {"$regex": f"^{month}"}
    elif start_date and end_date:
        query["date"] = {"$gte": start_date, "$lte": end_date}
    elif start_date:
        query["date"] = {"$gte": start_date}
    elif end_date:
        query["date"] = {"$lte": end_date}
    
    if member_id:
        query["member_id"] = member_id
    if category_id:
        query["category_id"] = category_id
    if subcategory_id:
        query["subcategory_id"] = subcategory_id
    if account_id:
        query["account_id"] = account_id
    if search:
        query["$or"] = [
            {"merchant_name": {"$regex": search, "$options": "i"}},
            {"notes": {"$regex": search, "$options": "i"}}
        ]
    
    transactions = await db.transactions.find(query, {"_id": 0}).sort("date", -1).to_list(10000)
    return transactions

@api_router.post("/transactions")
async def create_transaction(tx_data: TransactionCreate, user: dict = Depends(get_current_user)):
    # Apply rules
    if tx_data.merchant_name:
        rules = await db.rules.find(
            {"household_id": user["household_id"], "active": True},
            {"_id": 0}
        ).to_list(100)
        
        for rule in rules:
            if rule["merchant_contains"].lower() in tx_data.merchant_name.lower():
                if rule.get("set_category_id") and not tx_data.category_id:
                    tx_data.category_id = rule["set_category_id"]
                if rule.get("set_member_id") and not tx_data.member_id:
                    tx_data.member_id = rule["set_member_id"]
                break
    
    # Auto-create merchant if new
    if tx_data.merchant_name:
        existing = await db.merchants.find_one({
            "household_id": user["household_id"],
            "name": {"$regex": f"^{tx_data.merchant_name}$", "$options": "i"}
        })
        if not existing:
            merchant = Merchant(
                household_id=user["household_id"],
                name=tx_data.merchant_name,
                default_category_id=tx_data.category_id
            )
            await db.merchants.insert_one(merchant.model_dump())
            tx_data.merchant_id = merchant.id
        else:
            tx_data.merchant_id = existing["id"]
    
    transaction = Transaction(
        household_id=user["household_id"],
        **tx_data.model_dump()
    )
    await db.transactions.insert_one(transaction.model_dump())
    return transaction.model_dump()

@api_router.put("/transactions/{transaction_id}")
async def update_transaction(transaction_id: str, tx_data: TransactionUpdate, user: dict = Depends(get_current_user)):
    update_data = {k: v for k, v in tx_data.model_dump().items() if v is not None}
    
    if update_data:
        result = await db.transactions.update_one(
            {"id": transaction_id, "household_id": user["household_id"]},
            {"$set": update_data}
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Transaction not found")
    
    transaction = await db.transactions.find_one({"id": transaction_id}, {"_id": 0})
    return transaction

@api_router.delete("/transactions/{transaction_id}")
async def delete_transaction(transaction_id: str, user: dict = Depends(get_current_user)):
    result = await db.transactions.delete_one(
        {"id": transaction_id, "household_id": user["household_id"]}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {"success": True}

@api_router.put("/transactions/bulk/update")
async def bulk_update_transactions(
    transaction_ids: List[str],
    category_id: Optional[str] = None,
    member_id: Optional[str] = None,
    tags: Optional[List[str]] = None,
    user: dict = Depends(get_current_user)
):
    update_data = {}
    if category_id:
        update_data["category_id"] = category_id
    if member_id:
        update_data["member_id"] = member_id
    if tags is not None:
        update_data["tags"] = tags
    
    if update_data:
        result = await db.transactions.update_many(
            {"id": {"$in": transaction_ids}, "household_id": user["household_id"]},
            {"$set": update_data}
        )
        return {"updated": result.modified_count}
    
    return {"updated": 0}

# ==================== BUDGETS ====================

@api_router.get("/budgets")
async def get_budgets(month: Optional[str] = None, user: dict = Depends(get_current_user)):
    query = {"household_id": user["household_id"]}
    if month:
        query["month"] = month
    
    budgets = await db.budgets.find(query, {"_id": 0}).to_list(500)
    return budgets

@api_router.post("/budgets")
async def create_budget(budget_data: BudgetCreate, user: dict = Depends(get_current_user)):
    # Check if budget exists for this month/category
    existing = await db.budgets.find_one({
        "household_id": user["household_id"],
        "month": budget_data.month,
        "category_id": budget_data.category_id
    })
    
    if existing:
        # Update existing
        await db.budgets.update_one(
            {"id": existing["id"]},
            {"$set": {"amount": budget_data.amount, "rollover": budget_data.rollover}}
        )
        updated = await db.budgets.find_one({"id": existing["id"]}, {"_id": 0})
        return updated
    
    budget = Budget(
        household_id=user["household_id"],
        **budget_data.model_dump()
    )
    await db.budgets.insert_one(budget.model_dump())
    return budget.model_dump()

@api_router.put("/budgets/{budget_id}")
async def update_budget(budget_id: str, budget_data: BudgetCreate, user: dict = Depends(get_current_user)):
    result = await db.budgets.update_one(
        {"id": budget_id, "household_id": user["household_id"]},
        {"$set": budget_data.model_dump()}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Budget not found")
    
    budget = await db.budgets.find_one({"id": budget_id}, {"_id": 0})
    return budget

@api_router.delete("/budgets/{budget_id}")
async def delete_budget(budget_id: str, user: dict = Depends(get_current_user)):
    result = await db.budgets.delete_one(
        {"id": budget_id, "household_id": user["household_id"]}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Budget not found")
    return {"success": True}

# ==================== RECURRING RULES ====================

@api_router.get("/recurring")
async def get_recurring_rules(user: dict = Depends(get_current_user)):
    rules = await db.recurring_rules.find(
        {"household_id": user["household_id"], "active": True},
        {"_id": 0}
    ).to_list(500)
    return rules

@api_router.post("/recurring")
async def create_recurring_rule(rule_data: RecurringRuleCreate, user: dict = Depends(get_current_user)):
    rule = RecurringRule(
        household_id=user["household_id"],
        **rule_data.model_dump()
    )
    await db.recurring_rules.insert_one(rule.model_dump())
    return rule.model_dump()

@api_router.put("/recurring/{rule_id}")
async def update_recurring_rule(rule_id: str, rule_data: RecurringRuleCreate, user: dict = Depends(get_current_user)):
    result = await db.recurring_rules.update_one(
        {"id": rule_id, "household_id": user["household_id"]},
        {"$set": rule_data.model_dump()}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Recurring rule not found")
    
    rule = await db.recurring_rules.find_one({"id": rule_id}, {"_id": 0})
    return rule

@api_router.delete("/recurring/{rule_id}")
async def delete_recurring_rule(rule_id: str, user: dict = Depends(get_current_user)):
    result = await db.recurring_rules.update_one(
        {"id": rule_id, "household_id": user["household_id"]},
        {"$set": {"active": False}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Recurring rule not found")
    return {"success": True}

@api_router.post("/recurring/{rule_id}/post")
async def post_recurring_transaction(rule_id: str, user: dict = Depends(get_current_user)):
    """Manually post a recurring transaction"""
    rule = await db.recurring_rules.find_one(
        {"id": rule_id, "household_id": user["household_id"]},
        {"_id": 0}
    )
    if not rule:
        raise HTTPException(status_code=404, detail="Recurring rule not found")
    
    # Create transaction
    amount = rule["amount"] if rule["type"] == "income" else -abs(rule["amount"])
    transaction = Transaction(
        household_id=user["household_id"],
        date=rule["next_date"],
        amount=amount,
        type=rule["type"],
        merchant_name=rule["name"],
        category_id=rule.get("category_id"),
        account_id=rule.get("account_id"),
        member_id=rule.get("member_id"),
        notes=rule.get("notes"),
        is_recurring_instance=True
    )
    await db.transactions.insert_one(transaction.model_dump())
    
    # Update next date
    from dateutil.relativedelta import relativedelta
    from datetime import datetime
    
    current_date = datetime.strptime(rule["next_date"], "%Y-%m-%d")
    if rule["frequency"] == "weekly":
        next_date = current_date + timedelta(weeks=1)
    elif rule["frequency"] == "biweekly":
        next_date = current_date + timedelta(weeks=2)
    elif rule["frequency"] == "monthly":
        next_date = current_date + relativedelta(months=1)
    elif rule["frequency"] == "yearly":
        next_date = current_date + relativedelta(years=1)
    else:
        next_date = current_date + relativedelta(months=1)
    
    await db.recurring_rules.update_one(
        {"id": rule_id},
        {"$set": {"next_date": next_date.strftime("%Y-%m-%d")}}
    )
    
    return transaction.model_dump()

# ==================== GOALS ====================

@api_router.get("/goals")
async def get_goals(user: dict = Depends(get_current_user)):
    goals = await db.goals.find(
        {"household_id": user["household_id"], "active": True},
        {"_id": 0}
    ).to_list(100)
    return goals

@api_router.post("/goals")
async def create_goal(goal_data: GoalCreate, user: dict = Depends(get_current_user)):
    goal = Goal(
        household_id=user["household_id"],
        **goal_data.model_dump()
    )
    await db.goals.insert_one(goal.model_dump())
    return goal.model_dump()

@api_router.put("/goals/{goal_id}")
async def update_goal(goal_id: str, goal_data: GoalCreate, user: dict = Depends(get_current_user)):
    result = await db.goals.update_one(
        {"id": goal_id, "household_id": user["household_id"]},
        {"$set": goal_data.model_dump()}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    goal = await db.goals.find_one({"id": goal_id}, {"_id": 0})
    return goal

@api_router.delete("/goals/{goal_id}")
async def delete_goal(goal_id: str, user: dict = Depends(get_current_user)):
    result = await db.goals.update_one(
        {"id": goal_id, "household_id": user["household_id"]},
        {"$set": {"active": False}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Goal not found")
    return {"success": True}

@api_router.post("/goals/{goal_id}/contribute")
async def contribute_to_goal(goal_id: str, amount: float, user: dict = Depends(get_current_user)):
    """Add contribution to a goal"""
    goal = await db.goals.find_one(
        {"id": goal_id, "household_id": user["household_id"]},
        {"_id": 0}
    )
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    new_amount = goal["current_amount"] + amount
    await db.goals.update_one(
        {"id": goal_id},
        {"$set": {"current_amount": new_amount}}
    )
    
    updated = await db.goals.find_one({"id": goal_id}, {"_id": 0})
    return updated

# ==================== TAGS ====================

@api_router.get("/tags")
async def get_tags(user: dict = Depends(get_current_user)):
    tags = await db.tags.find(
        {"household_id": user["household_id"]},
        {"_id": 0}
    ).to_list(500)
    return tags

@api_router.post("/tags")
async def create_tag(tag_data: TagCreate, user: dict = Depends(get_current_user)):
    tag = Tag(
        household_id=user["household_id"],
        **tag_data.model_dump()
    )
    await db.tags.insert_one(tag.model_dump())
    return tag.model_dump()

@api_router.delete("/tags/{tag_id}")
async def delete_tag(tag_id: str, user: dict = Depends(get_current_user)):
    result = await db.tags.delete_one(
        {"id": tag_id, "household_id": user["household_id"]}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Tag not found")
    return {"success": True}

# ==================== RULES ====================

@api_router.get("/rules")
async def get_rules(user: dict = Depends(get_current_user)):
    rules = await db.rules.find(
        {"household_id": user["household_id"], "active": True},
        {"_id": 0}
    ).to_list(500)
    return rules

@api_router.post("/rules")
async def create_rule(rule_data: RuleCreate, user: dict = Depends(get_current_user)):
    rule = Rule(
        household_id=user["household_id"],
        **rule_data.model_dump()
    )
    await db.rules.insert_one(rule.model_dump())
    return rule.model_dump()

@api_router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str, user: dict = Depends(get_current_user)):
    result = await db.rules.update_one(
        {"id": rule_id, "household_id": user["household_id"]},
        {"$set": {"active": False}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"success": True}

# ==================== DASHBOARD / REPORTS ====================

@api_router.get("/dashboard/summary")
async def get_dashboard_summary(month: str, user: dict = Depends(get_current_user)):
    """Get dashboard summary for a specific month"""
    from dateutil.relativedelta import relativedelta
    
    household_id = user["household_id"]
    
    # Get transactions for the month
    transactions = await db.transactions.find(
        {"household_id": household_id, "date": {"$regex": f"^{month}"}},
        {"_id": 0}
    ).to_list(10000)
    
    income = sum(t["amount"] for t in transactions if t["amount"] > 0)
    expenses = sum(t["amount"] for t in transactions if t["amount"] < 0)
    
    # Get previous month data for comparison
    year, mon = map(int, month.split("-"))
    current_month_start = datetime(year, mon, 1)
    prev_month_start = current_month_start - relativedelta(months=1)
    prev_month = prev_month_start.strftime("%Y-%m")
    
    prev_transactions = await db.transactions.find(
        {"household_id": household_id, "date": {"$regex": f"^{prev_month}"}},
        {"_id": 0}
    ).to_list(10000)
    
    prev_income = sum(t["amount"] for t in prev_transactions if t["amount"] > 0)
    prev_expenses = sum(t["amount"] for t in prev_transactions if t["amount"] < 0)
    
    # Get budgets for the month
    budgets = await db.budgets.find(
        {"household_id": household_id, "month": month},
        {"_id": 0}
    ).to_list(500)
    
    total_budget = sum(b["amount"] for b in budgets)
    
    return {
        "income": income,
        "expenses": abs(expenses),
        "net": income + expenses,
        "budget": total_budget,
        "to_budget": total_budget - abs(expenses),
        "prev_income": prev_income,
        "prev_expenses": abs(prev_expenses),
        "prev_net": prev_income + prev_expenses,
        "income_change": income - prev_income,
        "expenses_change": abs(expenses) - abs(prev_expenses)
    }

@api_router.get("/dashboard/category-spending")
async def get_category_spending(month: str, user: dict = Depends(get_current_user)):
    """Get spending breakdown by category for the month"""
    household_id = user["household_id"]
    
    # Get expense transactions for the month
    transactions = await db.transactions.find(
        {"household_id": household_id, "date": {"$regex": f"^{month}"}, "amount": {"$lt": 0}},
        {"_id": 0}
    ).to_list(10000)
    
    # Get all categories with colors
    categories = await db.categories.find(
        {"household_id": household_id, "is_active": True},
        {"_id": 0}
    ).to_list(500)
    
    cat_map = {c["id"]: c for c in categories}
    
    # Group spending by category
    by_category = {}
    for tx in transactions:
        cat_id = tx.get("category_id")
        if cat_id and cat_id in cat_map:
            cat = cat_map[cat_id]
            cat_name = cat["category_name"]
            if cat_name not in by_category:
                by_category[cat_name] = {
                    "name": cat_name,
                    "amount": 0,
                    "color": cat.get("color", "#64748B"),
                    "group": cat.get("group_name", "Other"),
                    "category_id": cat_id
                }
            by_category[cat_name]["amount"] += abs(tx["amount"])
    
    # Sort by amount descending
    result = sorted(by_category.values(), key=lambda x: -x["amount"])
    
    # Calculate total and percentages
    total = sum(item["amount"] for item in result)
    for item in result:
        item["percentage"] = round((item["amount"] / total * 100) if total > 0 else 0, 1)
    
    return {
        "categories": result,
        "total": total
    }

@api_router.get("/dashboard/spending-chart")
async def get_spending_chart(month: str, user: dict = Depends(get_current_user)):
    """Get cumulative spending data for current and previous month"""
    from datetime import datetime
    from dateutil.relativedelta import relativedelta
    
    household_id = user["household_id"]
    
    # Parse month
    year, mon = map(int, month.split("-"))
    current_month_start = datetime(year, mon, 1)
    prev_month_start = current_month_start - relativedelta(months=1)
    prev_month = prev_month_start.strftime("%Y-%m")
    
    # Get transactions for both months
    current_txs = await db.transactions.find(
        {"household_id": household_id, "date": {"$regex": f"^{month}"}, "amount": {"$lt": 0}},
        {"_id": 0}
    ).to_list(10000)
    
    prev_txs = await db.transactions.find(
        {"household_id": household_id, "date": {"$regex": f"^{prev_month}"}, "amount": {"$lt": 0}},
        {"_id": 0}
    ).to_list(10000)
    
    # Build cumulative data by day
    def build_cumulative(txs):
        by_day = {}
        for tx in txs:
            day = int(tx["date"].split("-")[2])
            by_day[day] = by_day.get(day, 0) + abs(tx["amount"])
        
        cumulative = []
        running = 0
        for day in range(1, 32):
            running += by_day.get(day, 0)
            cumulative.append({"day": day, "amount": running})
        return cumulative
    
    return {
        "current": build_cumulative(current_txs),
        "previous": build_cumulative(prev_txs),
        "current_month": month,
        "previous_month": prev_month
    }

@api_router.get("/reports/summary")
async def get_reports_summary(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    member_id: Optional[str] = None,
    category_id: Optional[str] = None,
    account_id: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get reports summary with filters"""
    household_id = user["household_id"]
    
    query = {"household_id": household_id}
    
    if start_date and end_date:
        query["date"] = {"$gte": start_date, "$lte": end_date}
    elif start_date:
        query["date"] = {"$gte": start_date}
    elif end_date:
        query["date"] = {"$lte": end_date}
    
    if member_id:
        query["member_id"] = member_id
    if category_id:
        query["category_id"] = category_id
    if account_id:
        query["account_id"] = account_id
    
    transactions = await db.transactions.find(query, {"_id": 0}).to_list(10000)
    
    expenses = [t for t in transactions if t["amount"] < 0]
    income = [t for t in transactions if t["amount"] > 0]
    
    total_spent = sum(abs(t["amount"]) for t in expenses)
    total_income = sum(t["amount"] for t in income)
    
    # By category
    by_category = {}
    categories = await db.categories.find({"household_id": household_id}, {"_id": 0}).to_list(500)
    cat_map = {c["id"]: c for c in categories}
    
    for tx in expenses:
        cat_id = tx.get("category_id")
        if cat_id and cat_id in cat_map:
            cat = cat_map[cat_id]
            key = cat["category_name"]
            by_category[key] = by_category.get(key, 0) + abs(tx["amount"])
    
    # By member
    members = await db.household_members.find({"household_id": household_id}, {"_id": 0}).to_list(100)
    member_map = {m["id"]: m for m in members}
    
    by_member = {}
    for tx in expenses:
        mem_id = tx.get("member_id")
        if mem_id and mem_id in member_map:
            name = member_map[mem_id]["name"]
            by_member[name] = by_member.get(name, 0) + abs(tx["amount"])
    
    # Budget usage
    budgets = await db.budgets.find({"household_id": household_id}, {"_id": 0}).to_list(500)
    total_budget = sum(b["amount"] for b in budgets)
    budget_usage = (total_spent / total_budget * 100) if total_budget > 0 else 0
    
    return {
        "total_spent": total_spent,
        "total_income": total_income,
        "transaction_count": len(expenses),
        "avg_transaction": total_spent / len(expenses) if expenses else 0,
        "budget_usage": round(budget_usage, 1),
        "by_category": [{"name": k, "value": v} for k, v in sorted(by_category.items(), key=lambda x: -x[1])],
        "by_member": [{"name": k, "value": v, "color": member_map.get(next((m["id"] for m in members if m["name"] == k), None), {}).get("color", "#64748B")} for k, v in by_member.items()]
    }

# ==================== CSV EXPORT ====================

@api_router.get("/export/transactions")
async def export_transactions(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    member_id: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Export transactions as CSV"""
    household_id = user["household_id"]
    
    query = {"household_id": household_id}
    if start_date and end_date:
        query["date"] = {"$gte": start_date, "$lte": end_date}
    if member_id:
        query["member_id"] = member_id
    
    transactions = await db.transactions.find(query, {"_id": 0}).sort("date", -1).to_list(10000)
    
    # Get lookups
    categories = await db.categories.find({"household_id": household_id}, {"_id": 0}).to_list(500)
    cat_map = {c["id"]: c["category_name"] for c in categories}
    
    members = await db.household_members.find({"household_id": household_id}, {"_id": 0}).to_list(100)
    member_map = {m["id"]: m["name"] for m in members}
    
    accounts = await db.accounts.find({"household_id": household_id}, {"_id": 0}).to_list(100)
    account_map = {a["id"]: a["name"] for a in accounts}
    
    # Build CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Type", "Amount", "Merchant", "Category", "Account", "Member", "Notes", "Tags"])
    
    for tx in transactions:
        writer.writerow([
            tx["date"],
            tx["type"],
            tx["amount"],
            tx.get("merchant_name", ""),
            cat_map.get(tx.get("category_id"), ""),
            account_map.get(tx.get("account_id"), ""),
            member_map.get(tx.get("member_id"), ""),
            tx.get("notes", ""),
            ",".join(tx.get("tags", []))
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=transactions.csv"}
    )

# ==================== SETUP ====================

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
