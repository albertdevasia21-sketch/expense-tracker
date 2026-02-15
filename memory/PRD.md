# Expense Tracker - Product Requirements Document

## Overview
A Monarch-style personal finance web app for household expense tracking with support for multiple members (Me/Wife).

## Original Problem Statement
Build a clean, modern personal finance web app with:
- Dashboard-first, left sidebar navigation, card-based UI
- Household finance tracker with manual income/expenses
- Assignment to household members (Me or Wife)
- Budget by category groups, recurring bills, goals tracking
- Reports with charts and CSV export

## User Choices
- **App Name**: Expense Tracker
- **Charts**: Recharts
- **Theme**: Light mode with blue accent + Dark mode toggle
- **Auth**: JWT-based custom authentication
- **Currency**: CAD (changeable in settings)
- **Demo Data**: Minimal deletable seed data

## Technical Architecture

### Backend (FastAPI + MongoDB)
- `/app/backend/server.py` - Main API with all endpoints
- JWT authentication with 24-hour token expiration
- MongoDB collections: users, household_members, categories, merchants, accounts, transactions, budgets, recurring_rules, goals, tags, rules

### Frontend (React + Tailwind + Shadcn UI)
- `/app/frontend/src/App.js` - Main app with routing
- `/app/frontend/src/contexts/` - AuthContext, ThemeContext, DataContext
- `/app/frontend/src/pages/` - All page components
- `/app/frontend/src/components/` - Reusable components

### Key Features Implemented
1. ✅ **Dashboard** - Summary cards, spending chart, recent transactions, goals preview
2. ✅ **Transactions** - Full list with filters (member/category/account), search, add/edit drawer
3. ✅ **Budget** - Fixed/Flexible expense tracking with progress bars
4. ✅ **Cash Flow** - Income vs expenses analysis with charts
5. ✅ **Reports** - KPI cards, pie charts, line charts, CSV export
6. ✅ **Recurring** - Income/expense rules with auto-post functionality
7. ✅ **Goals** - Progress tracking with contributions
8. ✅ **Accounts** - Manual account management with balance tracking
9. ✅ **Settings** - Profile, Household, Categories, Merchants, Tags, Data management
10. ✅ **Dark Mode** - Toggle between light and dark themes

### Data Model
- **Users**: id, email, password_hash, name, household_id, currency, timezone
- **Household Members**: id, household_id, name, color, avatar_url, is_default
- **Categories**: id, household_id, group_name, category_name, type, is_fixed
- **Transactions**: id, household_id, date, amount, type, merchant_name, category_id, account_id, member_id
- **Budgets**: id, household_id, month, category_id, amount, rollover
- **Recurring Rules**: id, household_id, name, type, amount, frequency, next_date, autopost
- **Goals**: id, household_id, name, target_amount, current_amount, target_date, color

## Implementation Date
- **Created**: February 10, 2026
- **Last Updated**: February 15, 2026

## What's Been Implemented
- Full authentication flow (register/login/logout)
- Demo data auto-creation on registration
- All 9 navigation pages fully functional
- Transaction drawer with type selector (Expense/Income/Transfer)
- Member badges (Me/Wife) visible throughout the app
- Month selector with prev/next navigation
- CSV export for transactions
- Dark mode toggle
- Responsive sidebar with mobile menu
- **Subcategories**: Categories can have subcategories for finer expense tracking
- **Enhanced Dashboard**: Monthly Spending by Category section with colored bars
- **Enhanced Reports**: Subcategory filter, category summary table with colors
- **Date Bug Fix (Feb 15, 2026)**: Fixed timezone issue where dates were displayed one day earlier
- **Auto-post Recurring (Feb 15, 2026)**: Recurring rules with autopost=true automatically create transactions on app load

## Prioritized Backlog

### P0 (Core - Completed)
- ✅ User registration and login
- ✅ Dashboard with summary cards
- ✅ Transaction CRUD
- ✅ Budget tracking
- ✅ Household member support

### P1 (Important - Completed)
- ✅ Reports with charts
- ✅ Recurring transactions
- ✅ Goals with contributions
- ✅ CSV export
- ✅ Dark mode

### P2 (Nice to Have - Future)
- [ ] Bank account sync integration
- [ ] Receipt/attachment upload
- [ ] Split transactions
- [ ] Transaction rules automation
- [ ] Email notifications
- [ ] Mobile app (React Native)

## Next Tasks
1. Add bank sync integration (Plaid)
2. Implement receipt image upload
3. Add split transaction functionality
4. Create email notification system
5. Build mobile app version
