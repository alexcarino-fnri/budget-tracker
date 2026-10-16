# PisoFlow (Philippine Peso Personal Budget & Debt Tracker)

A production-quality, responsive personal finance web application built with **Python 3.12+**, **Django 5.x**, **Tailwind CSS**, **HTMX**, **Chart.js**, and **SQLite / PostgreSQL**.

Designed specifically for tracking incoming and outgoing cash flows, monthly category budgets with automated warning thresholds, multi-account liquidity (Cash, Bank, GCash, Maya, Credit Card), and debt payoff optimization (Snowball vs. Avalanche strategies).

---

## Features

1. **Authentication & Multi-Tenant Security**
   - User registration, login, logout, profile customization, and password reset.
   - Strict database and view-level user scoping: users can never access or modify another user's financial accounts, budgets, or debts.
2. **Accounts & Wallets (Where money lives)**
   - Account types: **Cash**, **Bank**, **E-wallet** (GCash, Maya), **Credit Card**, and **Other**.
   - Real-time dynamically computed balances from transaction history: `opening_balance + income - expense + transfers_in - transfers_out`.
   - Internal account-to-account transfers (excluded from income/expense totals).
3. **Transactions & Activity**
   - Income, Expense, and Transfer transactions with receipt image attachment support.
   - Live debounced search and filtering by date range, account, type, and category via **HTMX partial swaps**.
   - Quick-add form accessible on mobile in seconds.
   - Scheduled recurring transactions (daily, weekly, bi-weekly, monthly, yearly) managed by `python manage.py generate_recurring`.
4. **Budgets & Goals**
   - Monthly category spending targets with customizable alert levels (default warning at 80%, critical alert at 100%+).
   - Optional monthly rollover of unused budget surpluses.
   - User-customizable categories with Lucide icons and colors.
5. **Debt & Loan Tracker**
   - Dual-direction tracking:
     - **I Owe (Liabilities)**: Credit cards, bank loans, personal loans.
     - **Owed to Me (Receivables)**: Money lent to others.
   - Overdue badges and countdown indicators.
   - Record payments against debts with optional automatic creation of linked ledger transactions.
   - **Payoff Strategy Planner**: Side-by-side comparison between **Debt Snowball** (lowest balance first) and **Debt Avalanche** (highest interest rate first) with extra monthly payment simulations.
6. **Dashboard & Visual Analytics**
   - Monthly cash flow metrics: Total Income, Total Expenses, Net Cash Flow, Total Net Worth.
   - Interactive **Chart.js** visualizations:
     - Expenses by category (Doughnut chart)
     - 6-month cash flow trajectory (Bar chart)
     - Historical debt reduction (Line chart)
   - Upcoming bills & debt due dates in the next 7 and 30 days.
7. **Reports, Export & CSV Import**
   - Monthly and 12-month yearly financial summaries and savings rate.
   - One-click export of transactions and debts to **CSV** and **Excel (.xlsx via openpyxl)**.
   - **CSV Import with Preview & Validation Step**: Pre-checks columns, formats, and categories before committing to the database.
8. **PWA & Responsive UX**
   - Mobile-first layout with bottom navigation bar for handheld devices and desktop sidebar.
   - Dark mode toggle with persistent local storage.
   - Installable as a Progressive Web App (manifest + service worker).

---

## Tech Stack

- **Backend**: Python 3.12+, Django 5.x
- **Database**: SQLite for development (easily switchable to PostgreSQL via `DATABASE_URL`)
- **Frontend**: Django Templates + Tailwind CSS (via CDN) + HTMX + Alpine.js
- **Charts**: Chart.js 4.x
- **Icons**: Lucide Icons
- **Currency**: Philippine Peso (`₱` / `PHP`) stored in `DecimalField(max_digits=12, decimal_places=2)` — no floating point inaccuracy.

---

## Getting Started

### 1. Prerequisites
- Python 3.12 or higher

### 2. Clone and Setup Virtual Environment
```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Key configuration values in `.env`:
- `DEBUG`: Set to `True` for development, `False` for production.
- `SECRET_KEY`: Django secret key.
- `ALLOWED_HOSTS`: Comma-separated allowed hosts (default: `localhost,127.0.0.1`).
- `DEFAULT_CURRENCY`: Default currency code (default: `PHP`).
- `DATABASE_URL`: (Optional) PostgreSQL connection string (e.g., `postgresql://user:password@localhost:5432/budget_db`). Defaults to SQLite `db.sqlite3` if unset.

### 4. Run Database Migrations
```bash
python manage.py migrate
```

### 5. Seed Realistic Demo Data
Populate the database with realistic Filipino financial accounts (BPI, GCash, Maya, BDO), 60 days of transaction history, monthly budgets, and debt tracking:
```bash
python manage.py seed_demo
```
**Demo Login Credentials:**
- **Username:** `demo`
- **Password:** `DemoPass123!`

### 6. Start the Development Server
```bash
python manage.py runserver
```
Visit `http://127.0.0.1:8000` in your web browser.

---

## Running Automated Tests

Run the complete test suite across all apps:
```bash
python manage.py test
```
The test suite covers:
- User registration, authentication, and profile settings
- Account balance calculations across income, expenses, and internal transfers
- Strict multi-tenant permission isolation (user scoping)
- Budget progress calculations, 80% warnings, and 100%+ alerts
- Debt repayment logic, linked transactions, and Snowball vs Avalanche payoff simulations
- Reports, CSV/Excel export endpoints, and CSV validation preview import

---

## Recurring Transactions Command

To execute due recurring transactions (can be automated via Cron or Celery):
```bash
python manage.py generate_recurring
```

---

## Project Structure

```text
├── accounts/          # User authentication, registration, profiles & theme settings
├── wallets/           # Accounts (Cash, Bank, GCash, Maya, Cards) & balance services
├── transactions/      # Incomes, expenses, transfers, recurring & attachments
├── budgets/           # Monthly budgets, categories & spending thresholds
├── debts/             # Debt tracker (I owe / Owed to me) & payoff planner
├── reports/           # Monthly/yearly summaries, CSV/Excel export & CSV preview import
├── core/              # Base templates, dashboard, KPIs, PWA & demo seeder
├── templates/         # Clean, responsive HTML templates
├── static/            # CSS, PWA manifest, service worker & icons
└── config/            # Django project settings & root URLs
```

---

## Cloud Deployment Guides

Choose your preferred deployment platform:

- 🚀 **[Deploy on Render (Recommended for Fast 1-Click Setup)](DEPLOY_RENDER.md)**: Zero-server setup with automated PostgreSQL, automatic SSL/TLS, and 1-click Blueprint (`render.yaml`).
- 🏛️ **[Deploy on Oracle Cloud Infrastructure (OCI)](DEPLOY_ORACLE_CLOUD.md)**: Full production VPS deployment with Docker Compose, PostgreSQL 16, Nginx, and systemd on Always Free compute instances.
