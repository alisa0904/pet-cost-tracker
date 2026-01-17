from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def to_rub(expense):
    """Конвертирует расход в рубли"""
    return expense.amount_in_rub

@register.filter
def currency_symbol(currency_code):
    """Возвращает символ валюты"""
    symbols = {'RUB': '₽', 'USD': '$', 'EUR': '€'}
    return symbols.get(currency_code, currency_code)

@register.filter
def format_currency(amount, currency_code):
    """Форматирует сумму с валютой"""
    symbols = {'RUB': '₽', 'USD': '$', 'EUR': '€'}
    symbol = symbols.get(currency_code, currency_code)
    
    if currency_code == 'RUB':
        return f"{amount} {symbol}"
    else:
        return f"{symbol}{amount}"

@register.simple_tag
def convert_and_format(amount, from_currency, to_currency='RUB'):
    """Конвертирует и форматирует сумму"""
    # Простая реализация конвертации
    rates = {'RUB': 1.0, 'USD': 90.0, 'EUR': 100.0}
    
    if from_currency == to_currency:
        converted = amount
    else:
        # Конвертируем через рубли
        amount_in_rub = amount * Decimal(str(rates.get(from_currency, 1.0)))
        if to_currency == 'RUB':
            converted = amount_in_rub
        else:
            converted = amount_in_rub / Decimal(str(rates.get(to_currency, 1.0)))
    
    symbols = {'RUB': '₽', 'USD': '$', 'EUR': '€'}
    symbol = symbols.get(to_currency, to_currency)
    
    if to_currency == 'RUB':
        return f"{converted:.2f} {symbol}"
    else:
        return f"{symbol}{converted:.2f}"