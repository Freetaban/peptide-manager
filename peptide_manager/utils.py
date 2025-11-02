"""
Utility functions e helpers.
"""

from datetime import datetime, timedelta
from typing import Optional


def format_date(date_str: Optional[str], format: str = '%d/%m/%Y') -> str:
    """Formatta una data per display."""
    if not date_str:
        return 'N/A'
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        return date_obj.strftime(format)
    except:
        return date_str


def days_until_expiry(expiry_date: str) -> int:
    """Calcola giorni rimanenti fino a scadenza."""
    try:
        expiry = datetime.strptime(expiry_date, '%Y-%m-%d')
        delta = expiry - datetime.now()
        return delta.days
    except:
        return -1


def format_currency(amount: float, currency: str = 'EUR') -> str:
    """Formatta un importo con valuta."""
    symbols = {'EUR': '€', 'USD': '$', 'GBP': '£'}
    symbol = symbols.get(currency, currency)
    return f"{amount:.2f} {symbol}"


def validate_email(email: str) -> bool:
    """Validazione semplice email."""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None
