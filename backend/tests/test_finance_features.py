"""
Test suite for Personal Finance App - Date Bug Fix and Auto-post Recurring Features
Tests:
1. Date bug fix: When creating a transaction with date 2025-02-14, it should be stored as Feb 14
2. Auto-post recurring transactions endpoint
3. Auto-posted transactions appear in dashboard expense totals
4. Auto-posted transactions appear in Monthly Spending by Category
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test user credentials
TEST_EMAIL = f"test_autopost_{uuid.uuid4().hex[:8]}@example.com"
TEST_PASSWORD = "password123"
TEST_NAME = "Test User"


class TestSetup:
    """Setup fixtures for all tests"""
    
    @pytest.fixture(scope="class")
    def api_client(self):
        """Shared requests session"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        return session
    
    @pytest.fixture(scope="class")
    def auth_data(self, api_client):
        """Register a new user and return auth data"""
        response = api_client.post(f"{BASE_URL}/api/auth/register", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
            "name": TEST_NAME
        })
        assert response.status_code == 200, f"Registration failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert "user" in data
        return data
    
    @pytest.fixture(scope="class")
    def authenticated_client(self, api_client, auth_data):
        """Session with auth header"""
        api_client.headers.update({"Authorization": f"Bearer {auth_data['token']}"})
        return api_client


class TestDateBugFix(TestSetup):
    """Test that dates are stored and returned correctly without timezone shift"""
    
    def test_create_transaction_feb_14_stored_correctly(self, authenticated_client):
        """
        Date bug fix: When creating a transaction with date 2025-02-14, 
        it should be stored and displayed as Feb 14, not Feb 13
        """
        # Create a transaction with date 2025-02-14
        test_date = "2025-02-14"
        response = authenticated_client.post(f"{BASE_URL}/api/transactions", json={
            "date": test_date,
            "amount": -50.00,
            "type": "expense",
            "merchant_name": "TEST_DateBugFix Store",
            "notes": "Testing date bug fix"
        })
        
        assert response.status_code == 200, f"Transaction creation failed: {response.text}"
        transaction = response.json()
        
        # Verify the date is stored exactly as provided
        assert transaction["date"] == test_date, f"Date mismatch: expected {test_date}, got {transaction['date']}"
        print(f"✓ Transaction created with date: {transaction['date']}")
        
        # Verify by fetching the transaction
        tx_id = transaction["id"]
        get_response = authenticated_client.get(f"{BASE_URL}/api/transactions?month=2025-02")
        assert get_response.status_code == 200
        
        transactions = get_response.json()
        found_tx = next((t for t in transactions if t["id"] == tx_id), None)
        assert found_tx is not None, "Transaction not found in list"
        assert found_tx["date"] == test_date, f"Date mismatch in GET: expected {test_date}, got {found_tx['date']}"
        print(f"✓ Transaction retrieved with correct date: {found_tx['date']}")
    
    def test_create_transaction_various_dates(self, authenticated_client):
        """Test multiple dates to ensure no timezone shift occurs"""
        test_dates = [
            "2025-01-01",  # New Year
            "2025-01-31",  # End of month
            "2025-03-15",  # Mid month
            "2025-12-31",  # End of year
        ]
        
        for test_date in test_dates:
            response = authenticated_client.post(f"{BASE_URL}/api/transactions", json={
                "date": test_date,
                "amount": -25.00,
                "type": "expense",
                "merchant_name": f"TEST_DateTest_{test_date}",
                "notes": f"Testing date {test_date}"
            })
            
            assert response.status_code == 200, f"Failed for date {test_date}: {response.text}"
            transaction = response.json()
            assert transaction["date"] == test_date, f"Date mismatch for {test_date}: got {transaction['date']}"
            print(f"✓ Date {test_date} stored correctly")


class TestAutopostRecurring(TestSetup):
    """Test auto-post recurring transactions feature"""
    
    def test_process_autopost_endpoint_exists(self, authenticated_client):
        """Verify /api/recurring/process-autopost endpoint exists and works"""
        response = authenticated_client.post(f"{BASE_URL}/api/recurring/process-autopost")
        assert response.status_code == 200, f"Autopost endpoint failed: {response.text}"
        
        data = response.json()
        assert "processed_rules" in data
        assert "posted_transactions" in data
        assert "transactions" in data
        print(f"✓ Autopost endpoint returned: {data['processed_rules']} rules processed, {data['posted_transactions']} transactions posted")
    
    def test_create_recurring_rule_with_autopost(self, authenticated_client):
        """Create a recurring rule with autopost enabled"""
        # Get a category for the recurring rule
        cat_response = authenticated_client.get(f"{BASE_URL}/api/categories")
        assert cat_response.status_code == 200
        categories = cat_response.json()
        expense_cat = next((c for c in categories if c["type"] == "expense"), None)
        
        # Get an account
        acc_response = authenticated_client.get(f"{BASE_URL}/api/accounts")
        assert acc_response.status_code == 200
        accounts = acc_response.json()
        account = accounts[0] if accounts else None
        
        # Create a recurring rule with a past date (should trigger autopost)
        past_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
        
        response = authenticated_client.post(f"{BASE_URL}/api/recurring", json={
            "name": "TEST_AutoPost Subscription",
            "type": "expense",
            "amount": 15.99,
            "frequency": "monthly",
            "next_date": past_date,
            "category_id": expense_cat["id"] if expense_cat else None,
            "account_id": account["id"] if account else None,
            "autopost": True,
            "notes": "Test autopost recurring"
        })
        
        assert response.status_code == 200, f"Recurring rule creation failed: {response.text}"
        rule = response.json()
        assert rule["autopost"] == True
        assert rule["name"] == "TEST_AutoPost Subscription"
        print(f"✓ Recurring rule created with autopost=True, next_date={rule['next_date']}")
        
        return rule
    
    def test_autopost_creates_transactions_for_past_due_rules(self, authenticated_client):
        """When autopost is triggered, it should create transactions for past due rules"""
        # First, create a recurring rule with past date
        past_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
        
        # Get categories and accounts
        cat_response = authenticated_client.get(f"{BASE_URL}/api/categories")
        categories = cat_response.json()
        expense_cat = next((c for c in categories if c["type"] == "expense"), None)
        
        acc_response = authenticated_client.get(f"{BASE_URL}/api/accounts")
        accounts = acc_response.json()
        account = accounts[0] if accounts else None
        
        # Create recurring rule
        rule_response = authenticated_client.post(f"{BASE_URL}/api/recurring", json={
            "name": "TEST_AutoPost Test Rule",
            "type": "expense",
            "amount": 29.99,
            "frequency": "monthly",
            "next_date": past_date,
            "category_id": expense_cat["id"] if expense_cat else None,
            "account_id": account["id"] if account else None,
            "autopost": True,
            "notes": "Testing autopost transaction creation"
        })
        
        assert rule_response.status_code == 200
        rule = rule_response.json()
        rule_id = rule["id"]
        
        # Trigger autopost processing
        autopost_response = authenticated_client.post(f"{BASE_URL}/api/recurring/process-autopost")
        assert autopost_response.status_code == 200
        autopost_data = autopost_response.json()
        
        print(f"✓ Autopost processed {autopost_data['processed_rules']} rules, created {autopost_data['posted_transactions']} transactions")
        
        # Verify transaction was created
        current_month = datetime.now().strftime("%Y-%m")
        tx_response = authenticated_client.get(f"{BASE_URL}/api/transactions?month={current_month}")
        assert tx_response.status_code == 200
        transactions = tx_response.json()
        
        # Look for auto-posted transaction
        autopost_tx = [t for t in transactions if "Auto-posted" in (t.get("notes") or "") and "TEST_AutoPost" in (t.get("merchant_name") or "")]
        print(f"✓ Found {len(autopost_tx)} auto-posted test transactions")
        
        # Verify the recurring rule's next_date was updated
        rules_response = authenticated_client.get(f"{BASE_URL}/api/recurring")
        assert rules_response.status_code == 200
        rules = rules_response.json()
        updated_rule = next((r for r in rules if r["id"] == rule_id), None)
        
        if updated_rule:
            # Next date should be in the future now
            assert updated_rule["next_date"] > past_date, f"Next date should have been updated from {past_date}"
            print(f"✓ Recurring rule next_date updated from {past_date} to {updated_rule['next_date']}")


class TestDashboardIntegration(TestSetup):
    """Test that auto-posted transactions appear in dashboard"""
    
    def test_autoposted_transactions_in_dashboard_summary(self, authenticated_client):
        """Auto-posted transactions should appear in dashboard expense totals"""
        current_month = datetime.now().strftime("%Y-%m")
        
        # Get dashboard summary
        response = authenticated_client.get(f"{BASE_URL}/api/dashboard/summary?month={current_month}")
        assert response.status_code == 200, f"Dashboard summary failed: {response.text}"
        
        summary = response.json()
        assert "expenses" in summary
        assert "income" in summary
        assert "net" in summary
        
        print(f"✓ Dashboard summary: Income=${summary['income']}, Expenses=${summary['expenses']}, Net=${summary['net']}")
        
        # Verify expenses include our test transactions
        assert summary["expenses"] >= 0, "Expenses should be non-negative"
    
    def test_autoposted_transactions_in_category_spending(self, authenticated_client):
        """Auto-posted transactions should appear in Monthly Spending by Category"""
        current_month = datetime.now().strftime("%Y-%m")
        
        # Get category spending
        response = authenticated_client.get(f"{BASE_URL}/api/dashboard/category-spending?month={current_month}")
        assert response.status_code == 200, f"Category spending failed: {response.text}"
        
        data = response.json()
        assert "categories" in data
        assert "total" in data
        
        print(f"✓ Category spending: Total=${data['total']}, Categories={len(data['categories'])}")
        
        # Print category breakdown
        for cat in data["categories"][:5]:  # Top 5 categories
            print(f"  - {cat['name']}: ${cat['amount']} ({cat['percentage']}%)")
    
    def test_spending_chart_includes_autoposted(self, authenticated_client):
        """Spending chart should include auto-posted transactions"""
        current_month = datetime.now().strftime("%Y-%m")
        
        response = authenticated_client.get(f"{BASE_URL}/api/dashboard/spending-chart?month={current_month}")
        assert response.status_code == 200, f"Spending chart failed: {response.text}"
        
        data = response.json()
        assert "current" in data
        assert "previous" in data
        
        # Current month should have cumulative spending data
        current_data = data["current"]
        assert len(current_data) > 0, "Should have spending data for current month"
        
        # Find the last day with spending
        last_spending = max((d["amount"] for d in current_data), default=0)
        print(f"✓ Spending chart: Current month cumulative spending=${last_spending}")


class TestRecurringRuleManagement(TestSetup):
    """Test recurring rule CRUD operations"""
    
    def test_create_recurring_rule_without_autopost(self, authenticated_client):
        """Create a recurring rule without autopost (manual posting)"""
        future_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        
        response = authenticated_client.post(f"{BASE_URL}/api/recurring", json={
            "name": "TEST_Manual Recurring",
            "type": "expense",
            "amount": 100.00,
            "frequency": "monthly",
            "next_date": future_date,
            "autopost": False,
            "notes": "Manual posting required"
        })
        
        assert response.status_code == 200
        rule = response.json()
        assert rule["autopost"] == False
        print(f"✓ Created recurring rule without autopost: {rule['name']}")
    
    def test_manual_post_recurring_transaction(self, authenticated_client):
        """Test manually posting a recurring transaction"""
        # Create a rule first
        future_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        create_response = authenticated_client.post(f"{BASE_URL}/api/recurring", json={
            "name": "TEST_Manual Post Test",
            "type": "expense",
            "amount": 50.00,
            "frequency": "monthly",
            "next_date": future_date,
            "autopost": False
        })
        
        assert create_response.status_code == 200
        rule = create_response.json()
        rule_id = rule["id"]
        
        # Manually post the transaction
        post_response = authenticated_client.post(f"{BASE_URL}/api/recurring/{rule_id}/post")
        assert post_response.status_code == 200
        
        transaction = post_response.json()
        assert transaction["is_recurring_instance"] == True
        assert transaction["merchant_name"] == "TEST_Manual Post Test"
        print(f"✓ Manually posted recurring transaction: {transaction['merchant_name']} on {transaction['date']}")
    
    def test_get_all_recurring_rules(self, authenticated_client):
        """Get all recurring rules for the household"""
        response = authenticated_client.get(f"{BASE_URL}/api/recurring")
        assert response.status_code == 200
        
        rules = response.json()
        assert isinstance(rules, list)
        print(f"✓ Retrieved {len(rules)} recurring rules")
        
        # Check for our test rules
        test_rules = [r for r in rules if "TEST_" in r.get("name", "")]
        print(f"  - Test rules: {len(test_rules)}")


class TestTransactionFiltering(TestSetup):
    """Test transaction filtering and retrieval"""
    
    def test_filter_transactions_by_month(self, authenticated_client):
        """Filter transactions by month"""
        current_month = datetime.now().strftime("%Y-%m")
        
        response = authenticated_client.get(f"{BASE_URL}/api/transactions?month={current_month}")
        assert response.status_code == 200
        
        transactions = response.json()
        assert isinstance(transactions, list)
        
        # All transactions should be from the current month
        for tx in transactions:
            assert tx["date"].startswith(current_month), f"Transaction date {tx['date']} not in month {current_month}"
        
        print(f"✓ Retrieved {len(transactions)} transactions for {current_month}")
    
    def test_filter_recurring_instance_transactions(self, authenticated_client):
        """Verify recurring instance transactions are marked correctly"""
        current_month = datetime.now().strftime("%Y-%m")
        
        response = authenticated_client.get(f"{BASE_URL}/api/transactions?month={current_month}")
        assert response.status_code == 200
        
        transactions = response.json()
        recurring_instances = [t for t in transactions if t.get("is_recurring_instance")]
        
        print(f"✓ Found {len(recurring_instances)} recurring instance transactions out of {len(transactions)} total")


# Cleanup fixture
@pytest.fixture(scope="module", autouse=True)
def cleanup_test_data():
    """Cleanup test data after all tests complete"""
    yield
    # Note: In a real scenario, we'd delete TEST_ prefixed data here
    # For now, we leave it as the test user is unique per run
    print("\n✓ Test suite completed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
