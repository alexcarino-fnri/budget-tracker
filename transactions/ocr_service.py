import re
from datetime import datetime, date
from decimal import Decimal
from rapidfuzz import process, fuzz
from wallets.models import Account
from budgets.models import Category
from debts.models import Debt

def parse_receipt_text_to_data(raw_text: str, user):
    """
    Analyzes raw text extracted from a receipt image or document and intelligently matches:
    - Amount (total, grand total, balance, or largest transaction decimal)
    - Date (YYYY-MM-DD, MM/DD/YYYY, DD/MM/YYYY, or Month DD, YYYY)
    - Merchant / Description
    - Account / Wallet (GCash, Maya, BPI, BDO, Cash, or fuzzy match user's accounts)
    - Category (Food, Utilities, Transportation, Groceries, Shopping, etc.)
    - Debt detection: whether this receipt relates to an active debt or debt payment
    """
    text_clean = raw_text.replace('\r', '\n')
    lines = [line.strip() for line in text_clean.split('\n') if line.strip()]
    full_lower = text_clean.lower()

    # 1. Extract Candidate Amounts
    # Look for amounts formatted like PHP 1,250.00, ₱500.50, Total: 120.00, 50.00, etc.
    amount = None
    
    # Priority pattern: explicitly labeled Total / Amount / Net / Grand Total / Paid
    total_patterns = [
        r'(?:total\s*(?:amount|due|paid)?|grand\s*total|amount\s*paid|amount\s*due|net\s*amount|amount|paid|balance)[\s:₱$pPhpP=]*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)',
        r'(?:₱|php|pesos|usd|\$)\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)',
    ]

    for pat in total_patterns:
        matches = re.findall(pat, full_lower)
        if matches:
            for m in reversed(matches):  # totals often appear near the bottom
                try:
                    val = Decimal(m.replace(',', ''))
                    if val > Decimal('0.00'):
                        amount = val
                        break
                except Exception:
                    continue
        if amount:
            break

    # Fallback amount: largest plausible decimal number in the receipt
    if not amount:
        decimal_matches = re.findall(r'\b([0-9]{1,3}(?:,[0-9]{3})*\.[0-9]{2})\b', text_clean)
        candidates = []
        for dm in decimal_matches:
            try:
                v = Decimal(dm.replace(',', ''))
                # Filter out numbers that look like times (e.g. 12.30) if preceded by am/pm or small
                if v > Decimal('0.00'):
                    candidates.append(v)
            except Exception:
                continue
        if candidates:
            # Usually the total is the maximum or near the bottom
            amount = max(candidates)

    # 2. Extract Date
    receipt_date = None
    date_patterns = [
        # YYYY-MM-DD
        (r'\b(20[2-3][0-9])[-/.](0[1-9]|1[0-2])[-/.](0[1-9]|[12][0-9]|3[01])\b', '%Y-%m-%d'),
        # MM/DD/YYYY or MM-DD-YYYY
        (r'\b(0[1-9]|1[0-2])[-/.](0[1-9]|[12][0-9]|3[01])[-/.](20[2-3][0-9])\b', '%m-%d-%Y'),
        # DD/MM/YYYY
        (r'\b(0[1-9]|[12][0-9]|3[01])[-/.](0[1-9]|1[0-2])[-/.](20[2-3][0-9])\b', '%d-%m-%Y'),
        # Month DD, YYYY (e.g. Oct 12, 2026 or October 12, 2026)
        (r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+([0-9]{1,2}),?\s+(20[2-3][0-9])\b', None),
    ]

    for pat, fmt in date_patterns:
        m = re.search(pat, full_lower)
        if m:
            try:
                if fmt:
                    raw_str = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
                    dt = datetime.strptime(raw_str, fmt)
                    receipt_date = dt.date()
                else:
                    month_str = m.group(1)[:3]
                    day_str = m.group(2)
                    year_str = m.group(3)
                    dt = datetime.strptime(f"{month_str} {day_str} {year_str}", "%b %d %Y")
                    receipt_date = dt.date()
                break
            except Exception:
                continue

    if not receipt_date:
        receipt_date = date.today()

    # 3. Detect Account / Wallet
    user_accounts = list(Account.objects.filter(user=user, is_active=True))
    matched_account = None

    # Check common payment channel keywords
    wallet_keywords = {
        'gcash': ['gcash', 'g-cash', 'mynt', 'globe fintech'],
        'maya': ['maya', 'paymaya', 'pay maya', 'maya bank'],
        'bpi': ['bpi', 'bank of the philippine islands'],
        'bdo': ['bdo', 'bdo unibank', 'bdo network'],
        'metrobank': ['metrobank', 'metro bank'],
        'unionbank': ['unionbank', 'union bank', 'ubp'],
        'cash': ['cash', 'change', 'sukli', 'cash tender', 'bill payment cash'],
        'credit': ['credit card', 'visa', 'mastercard', 'master card', 'amex', 'jcb'],
    }

    # First match against user accounts directly
    for acc in user_accounts:
        acc_name_lower = acc.name.lower()
        if acc_name_lower in full_lower:
            matched_account = acc
            break

    # If not directly matched, check keyword mappings against user account types and names
    if not matched_account and user_accounts:
        for key, terms in wallet_keywords.items():
            if any(term in full_lower for term in terms):
                for acc in user_accounts:
                    if key in acc.name.lower() or (key == 'cash' and acc.account_type == 'CASH') or (key == 'credit' and acc.account_type == 'CREDIT_CARD'):
                        matched_account = acc
                        break
            if matched_account:
                break

    # Fallback account: user's default/first account
    if not matched_account and user_accounts:
        matched_account = user_accounts[0]

    # 4. Extract Merchant / Description
    # Usually top 1-3 lines contain store name (e.g. Jollibee, McDonald's, 7-Eleven, Meralco, Shopee)
    description = ""
    # Check known merchant/biller keywords
    merchant_patterns = [
        'jollibee', 'mcdonald', 'starbucks', '7-eleven', 'seven eleven', 'sm store',
        'meralco', 'maynilad', 'manila water', 'pldt', 'globe', 'smart', 'converge',
        'shopee', 'lazada', 'grab', 'foodpanda', 'watsons', 'mercury drug', 'puregold',
        'robinsons', 'shell', 'petron', 'caltex', 'cebu pacific', 'philippine airlines'
    ]
    for mp in merchant_patterns:
        if mp in full_lower:
            description = mp.title()
            break

    if not description and lines:
        # Take first reasonable line (not too short, not purely numbers)
        for line in lines[:5]:
            clean_l = re.sub(r'[^a-zA-Z0-9\s&]', '', line).strip()
            if len(clean_l) >= 3 and not clean_l.isdigit():
                description = clean_l[:60]
                break

    if not description:
        description = "Receipt Transaction"

    # 5. Detect Category
    user_categories = list(Category.objects.filter(user=user))
    system_categories = list(Category.objects.filter(user__isnull=True))
    all_categories = user_categories + system_categories
    matched_category = None

    category_keyword_map = {
        'Food & Dining': ['food', 'jollibee', 'mcdonald', 'restaurant', 'cafe', 'coffee', 'starbucks', 'meal', 'lunch', 'dinner', 'breakfast', 'dine', 'snack', 'bake', 'grill'],
        'Groceries': ['puregold', 'sm supermarket', 'robinsons supermarket', 'supermarket', 'grocery', 'waltermart', 'savemore', 'wet market'],
        'Utilities': ['meralco', 'maynilad', 'water', 'electric', 'bill', 'electricity', 'pldt', 'converge', 'internet', 'utility'],
        'Transportation': ['grab', 'gas', 'fuel', 'shell', 'petron', 'caltex', 'toll', 'parking', 'transport', 'taxi', 'fare'],
        'Health & Medical': ['mercury drug', 'watsons', 'pharmacy', 'clinic', 'hospital', 'medical', 'medicine', 'doctor'],
        'Shopping': ['shopee', 'lazada', 'sm store', 'department store', 'zara', 'uniqlo', 'clothing', 'retail'],
        'Entertainment': ['cinema', 'movie', 'netflix', 'spotify', 'games', 'steam'],
        'Debt & Loan Repayment': ['loan', 'debt', 'amortization', 'installment', 'credit card payment', 'lending', 'repayment', 'sss loan', 'pag-ibig', 'home credit'],
    }

    for cat_name, kw_list in category_keyword_map.items():
        if any(kw in full_lower for kw in kw_list):
            # Find category object in user or system categories
            for cat in all_categories:
                if cat.name.lower() == cat_name.lower() or cat_name.lower() in cat.name.lower():
                    matched_category = cat
                    break
        if matched_category:
            break

    # If still none, check category name directly in text
    if not matched_category and all_categories:
        for cat in all_categories:
            if cat.name.lower() in full_lower:
                matched_category = cat
                break

    # 6. Check if this receipt is for payment of DEBTS
    is_debt_payment = False
    matched_debt = None
    debt_confidence = 0
    debt_keywords = ['loan', 'debt', 'amortization', 'installment', 'statement balance', 'minimum due', 'repayment', 'credit card bill', 'card payment', 'lender', 'borrower', 'sss loan', 'pag-ibig loan', 'home credit']
    
    if any(dk in full_lower for dk in debt_keywords):
        is_debt_payment = True
        debt_confidence = 70

    # Match against user's active debts
    user_debts = list(Debt.objects.filter(user=user, status=Debt.STATUS_ACTIVE))
    if user_debts:
        for d in user_debts:
            title_lower = d.title.lower()
            creditor_lower = d.creditor_or_debtor.lower()
            
            # Direct match on debt title or creditor name
            if (len(title_lower) >= 3 and title_lower in full_lower) or (len(creditor_lower) >= 3 and creditor_lower in full_lower):
                matched_debt = d
                is_debt_payment = True
                debt_confidence = 95
                break

        # Fuzzy match if not directly found
        if not matched_debt:
            debt_names = [f"{d.title} {d.creditor_or_debtor}" for d in user_debts]
            best_match = process.extractOne(full_lower, debt_names, scorer=fuzz.partial_ratio)
            if best_match and best_match[1] >= 80:
                idx = debt_names.index(best_match[0])
                matched_debt = user_debts[idx]
                is_debt_payment = True
                debt_confidence = best_match[1]

    return {
        'amount': str(amount) if amount else '',
        'date': receipt_date.strftime('%Y-%m-%d') if receipt_date else date.today().strftime('%Y-%m-%d'),
        'description': description,
        'account_id': matched_account.id if matched_account else None,
        'account_name': matched_account.name if matched_account else '',
        'category_id': matched_category.id if matched_category else None,
        'category_name': matched_category.name if matched_category else '',
        'is_debt_payment': is_debt_payment,
        'debt_id': matched_debt.id if matched_debt else None,
        'debt_title': matched_debt.title if matched_debt else '',
        'debt_creditor': matched_debt.creditor_or_debtor if matched_debt else '',
        'debt_confidence': debt_confidence,
        'raw_text_preview': text_clean[:500] if text_clean else ''
    }
