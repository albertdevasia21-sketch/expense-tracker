#!/usr/bin/env python3
"""
Comprehensive backend API testing for Personal Finance Expense Tracker
Tests all endpoints with proper authentication and data validation
"""

import requests
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class ExpenseTrackerAPITester:
    def __init__(self, base_url: str = "https://finances-hub-5.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.user_data = None
        self.household_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        
        # Store created IDs for cleanup and reference
        self.created_ids = {
            'members': [],
            'categories': [],
            'merchants': [],
            'accounts': [],
            'transactions': [],
            'budgets': [],
            'recurring': [],
            'goals': [],
            'tags': [],
            'rules': []
        }

    def log_result(self, test_name: str, success: bool, details: str = "", response_data: Any = None):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {test_name}: PASSED")
        else:
            print(f"❌ {test_name}: FAILED - {details}")
        
        self.test_results.append({
            'test': test_name,
            'success': success,
            'details': details,
            'response_data': response_data
        })

    def make_request(self, method: str, endpoint: str, data: Dict = None, expected_status: int = 200) -> tuple[bool, Dict]:
        """Make API request with proper headers"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                return False, {'error': f'Unsupported method: {method}'}

            success = response.status_code == expected_status
            try:
                response_data = response.json()
            except:
                response_data = {'status_code': response.status_code, 'text': response.text}

            return success, response_data

        except Exception as e:
            return False, {'error': str(e)}

    def test_user_registration(self):
        """Test user registration with demo data creation"""
        print("\n🔍 Testing User Registration...")
        
        # Use timestamp to ensure unique email
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        test_email = f"test_user_{timestamp}@example.com"
        
        registration_data = {
            "email": test_email,
            "password": "testpass123",
            "name": "Test User"
        }
        
        success, response = self.make_request('POST', 'auth/register', registration_data, 200)
        
        if success and 'token' in response and 'user' in response:
            self.token = response['token']
            self.user_data = response['user']
            self.household_id = response['user']['household_id']
            self.log_result("User Registration", True, f"User created with ID: {self.user_data['id']}")
            return True
        else:
            self.log_result("User Registration", False, f"Registration failed: {response}")
            return False

    def test_user_login(self):
        """Test user login with demo credentials"""
        print("\n🔍 Testing User Login...")
        
        login_data = {
            "email": "demo@example.com",
            "password": "demo123"
        }
        
        success, response = self.make_request('POST', 'auth/login', login_data, 200)
        
        if success and 'token' in response:
            # Store demo user token for further tests
            demo_token = response['token']
            demo_user = response['user']
            self.log_result("User Login (Demo)", True, f"Demo user logged in: {demo_user['email']}")
            return True
        else:
            self.log_result("User Login (Demo)", False, f"Login failed: {response}")
            return False

    def test_auth_me(self):
        """Test getting current user info"""
        print("\n🔍 Testing Auth Me...")
        
        success, response = self.make_request('GET', 'auth/me', expected_status=200)
        
        if success and 'id' in response:
            self.log_result("Auth Me", True, f"User info retrieved: {response['email']}")
            return True
        else:
            self.log_result("Auth Me", False, f"Failed to get user info: {response}")
            return False

    def test_household_members(self):
        """Test household members CRUD operations"""
        print("\n🔍 Testing Household Members...")
        
        # Get existing members
        success, members = self.make_request('GET', 'household-members')
        if success:
            self.log_result("Get Household Members", True, f"Found {len(members)} members")
        else:
            self.log_result("Get Household Members", False, f"Failed: {members}")
            return False

        # Create new member
        new_member = {
            "name": "Test Member",
            "color": "#10B981",
            "is_default": False
        }
        
        success, response = self.make_request('POST', 'household-members', new_member, 200)
        if success and 'id' in response:
            member_id = response['id']
            self.created_ids['members'].append(member_id)
            self.log_result("Create Household Member", True, f"Member created: {member_id}")
            
            # Update member
            update_data = {"name": "Updated Test Member", "color": "#F59E0B"}
            success, response = self.make_request('PUT', f'household-members/{member_id}', update_data)
            if success:
                self.log_result("Update Household Member", True, f"Member updated: {member_id}")
            else:
                self.log_result("Update Household Member", False, f"Update failed: {response}")
            
            return True
        else:
            self.log_result("Create Household Member", False, f"Creation failed: {response}")
            return False

    def test_categories(self):
        """Test categories CRUD operations"""
        print("\n🔍 Testing Categories...")
        
        # Get existing categories
        success, categories = self.make_request('GET', 'categories')
        if success:
            self.log_result("Get Categories", True, f"Found {len(categories)} categories")
        else:
            self.log_result("Get Categories", False, f"Failed: {categories}")
            return False

        # Create new category
        new_category = {
            "group_name": "Test Group",
            "category_name": "Test Category",
            "type": "expense",
            "is_fixed": False
        }
        
        success, response = self.make_request('POST', 'categories', new_category, 200)
        if success and 'id' in response:
            category_id = response['id']
            self.created_ids['categories'].append(category_id)
            self.log_result("Create Category", True, f"Category created: {category_id}")
            return True
        else:
            self.log_result("Create Category", False, f"Creation failed: {response}")
            return False

    def test_accounts(self):
        """Test accounts CRUD operations"""
        print("\n🔍 Testing Accounts...")
        
        # Get existing accounts
        success, accounts = self.make_request('GET', 'accounts')
        if success:
            self.log_result("Get Accounts", True, f"Found {len(accounts)} accounts")
        else:
            self.log_result("Get Accounts", False, f"Failed: {accounts}")
            return False

        # Create new account
        new_account = {
            "name": "Test Account",
            "type": "checking",
            "opening_balance": 1000.0
        }
        
        success, response = self.make_request('POST', 'accounts', new_account, 200)
        if success and 'id' in response:
            account_id = response['id']
            self.created_ids['accounts'].append(account_id)
            self.log_result("Create Account", True, f"Account created: {account_id}")
            return True
        else:
            self.log_result("Create Account", False, f"Creation failed: {response}")
            return False

    def test_transactions(self):
        """Test transactions CRUD operations"""
        print("\n🔍 Testing Transactions...")
        
        # Get existing transactions
        success, transactions = self.make_request('GET', 'transactions')
        if success:
            self.log_result("Get Transactions", True, f"Found {len(transactions)} transactions")
        else:
            self.log_result("Get Transactions", False, f"Failed: {transactions}")
            return False

        # Create new transaction
        today = datetime.now().strftime("%Y-%m-%d")
        new_transaction = {
            "date": today,
            "amount": -50.0,
            "type": "expense",
            "merchant_name": "Test Merchant",
            "notes": "Test transaction"
        }
        
        success, response = self.make_request('POST', 'transactions', new_transaction, 200)
        if success and 'id' in response:
            transaction_id = response['id']
            self.created_ids['transactions'].append(transaction_id)
            self.log_result("Create Transaction", True, f"Transaction created: {transaction_id}")
            
            # Test transaction update
            update_data = {"amount": -75.0, "notes": "Updated test transaction"}
            success, response = self.make_request('PUT', f'transactions/{transaction_id}', update_data)
            if success:
                self.log_result("Update Transaction", True, f"Transaction updated: {transaction_id}")
            else:
                self.log_result("Update Transaction", False, f"Update failed: {response}")
            
            return True
        else:
            self.log_result("Create Transaction", False, f"Creation failed: {response}")
            return False

    def test_budgets(self):
        """Test budgets CRUD operations"""
        print("\n🔍 Testing Budgets...")
        
        current_month = datetime.now().strftime("%Y-%m")
        
        # Get existing budgets
        success, budgets = self.make_request('GET', f'budgets?month={current_month}')
        if success:
            self.log_result("Get Budgets", True, f"Found {len(budgets)} budgets")
        else:
            self.log_result("Get Budgets", False, f"Failed: {budgets}")
            return False

        # Get categories first to use in budget
        success, categories = self.make_request('GET', 'categories')
        if success and len(categories) > 0:
            category_id = categories[0]['id']
            
            # Create new budget
            new_budget = {
                "month": current_month,
                "category_id": category_id,
                "amount": 500.0,
                "rollover": False
            }
            
            success, response = self.make_request('POST', 'budgets', new_budget, 200)
            if success and 'id' in response:
                budget_id = response['id']
                self.created_ids['budgets'].append(budget_id)
                self.log_result("Create Budget", True, f"Budget created: {budget_id}")
                return True
            else:
                self.log_result("Create Budget", False, f"Creation failed: {response}")
                return False
        else:
            self.log_result("Create Budget", False, "No categories available for budget")
            return False

    def test_recurring_rules(self):
        """Test recurring rules CRUD operations"""
        print("\n🔍 Testing Recurring Rules...")
        
        # Get existing recurring rules
        success, rules = self.make_request('GET', 'recurring')
        if success:
            self.log_result("Get Recurring Rules", True, f"Found {len(rules)} rules")
        else:
            self.log_result("Get Recurring Rules", False, f"Failed: {rules}")
            return False

        # Create new recurring rule
        next_month = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        new_rule = {
            "name": "Test Recurring",
            "type": "expense",
            "amount": 100.0,
            "frequency": "monthly",
            "next_date": next_month,
            "autopost": False
        }
        
        success, response = self.make_request('POST', 'recurring', new_rule, 200)
        if success and 'id' in response:
            rule_id = response['id']
            self.created_ids['recurring'].append(rule_id)
            self.log_result("Create Recurring Rule", True, f"Rule created: {rule_id}")
            
            # Test posting recurring transaction
            success, response = self.make_request('POST', f'recurring/{rule_id}/post', expected_status=200)
            if success:
                self.log_result("Post Recurring Transaction", True, f"Transaction posted from rule: {rule_id}")
            else:
                self.log_result("Post Recurring Transaction", False, f"Post failed: {response}")
            
            return True
        else:
            self.log_result("Create Recurring Rule", False, f"Creation failed: {response}")
            return False

    def test_goals(self):
        """Test goals CRUD operations"""
        print("\n🔍 Testing Goals...")
        
        # Get existing goals
        success, goals = self.make_request('GET', 'goals')
        if success:
            self.log_result("Get Goals", True, f"Found {len(goals)} goals")
        else:
            self.log_result("Get Goals", False, f"Failed: {goals}")
            return False

        # Create new goal
        target_date = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
        new_goal = {
            "name": "Test Goal",
            "target_amount": 5000.0,
            "target_date": target_date,
            "current_amount": 0.0,
            "color": "#3B82F6"
        }
        
        success, response = self.make_request('POST', 'goals', new_goal, 200)
        if success and 'id' in response:
            goal_id = response['id']
            self.created_ids['goals'].append(goal_id)
            self.log_result("Create Goal", True, f"Goal created: {goal_id}")
            
            # Test goal contribution
            success, response = self.make_request('POST', f'goals/{goal_id}/contribute?amount=100', expected_status=200)
            if success:
                self.log_result("Goal Contribution", True, f"Contributed to goal: {goal_id}")
            else:
                self.log_result("Goal Contribution", False, f"Contribution failed: {response}")
            
            return True
        else:
            self.log_result("Create Goal", False, f"Creation failed: {response}")
            return False

    def test_dashboard_endpoints(self):
        """Test dashboard and reports endpoints"""
        print("\n🔍 Testing Dashboard & Reports...")
        
        current_month = datetime.now().strftime("%Y-%m")
        
        # Test dashboard summary
        success, summary = self.make_request('GET', f'dashboard/summary?month={current_month}')
        if success and 'income' in summary:
            self.log_result("Dashboard Summary", True, f"Summary: Income={summary.get('income', 0)}, Expenses={summary.get('expenses', 0)}")
        else:
            self.log_result("Dashboard Summary", False, f"Failed: {summary}")

        # Test spending chart
        success, chart_data = self.make_request('GET', f'dashboard/spending-chart?month={current_month}')
        if success and 'current' in chart_data:
            self.log_result("Spending Chart", True, f"Chart data retrieved with {len(chart_data['current'])} data points")
        else:
            self.log_result("Spending Chart", False, f"Failed: {chart_data}")

        # Test reports summary
        success, reports = self.make_request('GET', 'reports/summary')
        if success and 'total_spent' in reports:
            self.log_result("Reports Summary", True, f"Reports: Total spent={reports.get('total_spent', 0)}")
        else:
            self.log_result("Reports Summary", False, f"Failed: {reports}")

    def test_csv_export(self):
        """Test CSV export functionality"""
        print("\n🔍 Testing CSV Export...")
        
        try:
            url = f"{self.base_url}/api/export/transactions"
            headers = {'Authorization': f'Bearer {self.token}'}
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200 and 'text/csv' in response.headers.get('content-type', ''):
                self.log_result("CSV Export", True, f"CSV exported successfully, size: {len(response.content)} bytes")
                return True
            else:
                self.log_result("CSV Export", False, f"Export failed: {response.status_code}")
                return False
        except Exception as e:
            self.log_result("CSV Export", False, f"Export error: {str(e)}")
            return False

    def test_merchants_and_tags(self):
        """Test merchants and tags operations"""
        print("\n🔍 Testing Merchants & Tags...")
        
        # Test merchants
        success, merchants = self.make_request('GET', 'merchants')
        if success:
            self.log_result("Get Merchants", True, f"Found {len(merchants)} merchants")
        else:
            self.log_result("Get Merchants", False, f"Failed: {merchants}")

        # Test tags
        success, tags = self.make_request('GET', 'tags')
        if success:
            self.log_result("Get Tags", True, f"Found {len(tags)} tags")
        else:
            self.log_result("Get Tags", False, f"Failed: {tags}")

        # Create new tag
        new_tag = {
            "name": "Test Tag",
            "color": "#64748B"
        }
        
        success, response = self.make_request('POST', 'tags', new_tag, 200)
        if success and 'id' in response:
            tag_id = response['id']
            self.created_ids['tags'].append(tag_id)
            self.log_result("Create Tag", True, f"Tag created: {tag_id}")
        else:
            self.log_result("Create Tag", False, f"Creation failed: {response}")

    def run_all_tests(self):
        """Run comprehensive test suite"""
        print("🚀 Starting Expense Tracker API Tests...")
        print(f"📍 Testing against: {self.base_url}")
        
        # Authentication tests
        if not self.test_user_registration():
            print("❌ Registration failed, cannot continue with authenticated tests")
            return False
        
        self.test_user_login()
        self.test_auth_me()
        
        # Core functionality tests
        self.test_household_members()
        self.test_categories()
        self.test_accounts()
        self.test_transactions()
        self.test_budgets()
        self.test_recurring_rules()
        self.test_goals()
        self.test_merchants_and_tags()
        
        # Dashboard and reports
        self.test_dashboard_endpoints()
        self.test_csv_export()
        
        return True

    def print_summary(self):
        """Print test summary"""
        print(f"\n📊 Test Summary:")
        print(f"   Tests Run: {self.tests_run}")
        print(f"   Tests Passed: {self.tests_passed}")
        print(f"   Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"   Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if self.tests_passed < self.tests_run:
            print(f"\n❌ Failed Tests:")
            for result in self.test_results:
                if not result['success']:
                    print(f"   - {result['test']}: {result['details']}")
        
        return self.tests_passed == self.tests_run

def main():
    """Main test execution"""
    tester = ExpenseTrackerAPITester()
    
    try:
        success = tester.run_all_tests()
        tester.print_summary()
        
        # Save detailed results
        with open('/app/backend_test_results.json', 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'total_tests': tester.tests_run,
                'passed_tests': tester.tests_passed,
                'success_rate': tester.tests_passed/tester.tests_run if tester.tests_run > 0 else 0,
                'results': tester.test_results
            }, f, indent=2)
        
        return 0 if success else 1
        
    except Exception as e:
        print(f"💥 Test execution failed: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())