from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.utils import timezone
from django.db.models.signals import post_migrate
from django.db import OperationalError
from django.dispatch import receiver

class Pet(models.Model):
    PET_TYPES = [
        ('cat', 'Кошка'),
        ('dog', 'Собака'),
        ('bird', 'Птица'),
        ('rodent', 'Грызун'),
        ('fish', 'Рыбка'),
        ('reptile', 'Рептилия'),
        ('other', 'Другое'),
    ]
    
    name = models.CharField(max_length=100, verbose_name='Кличка')
    species = models.CharField(max_length=50, choices=PET_TYPES, verbose_name='Вид')
    breed = models.CharField(max_length=100, blank=True, verbose_name='Порода')
    birth_date = models.DateField(null=True, blank=True, verbose_name='Дата рождения')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Владелец')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата добавления')
    
    class Meta:
        verbose_name = 'Питомец'
        verbose_name_plural = 'Питомцы'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.get_species_display()})"
    
    def get_age(self):
        """Возвращает возраст питомца в годах"""
        if self.birth_date:
            from datetime import date
            today = date.today()
            return today.year - self.birth_date.year - (
                (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
            )
        return None
    
    def total_expenses(self):
        """Общая сумма расходов на питомца в рублях"""
        total = Decimal('0')
        for expense in self.expenses.all():
            total += expense.amount_in_rub
        return total
    
    def expenses_by_currency(self):
        """Возвращает расходы сгруппированные по валюте"""
        expenses = self.expenses.all()
        result = {}
        
        for expense in expenses:
            currency = expense.currency
            if currency not in result:
                result[currency] = {
                    'count': 0,
                    'total': Decimal('0'),
                    'total_in_rub': Decimal('0'),
                    'symbol': expense.get_currency_symbol()
                }
            
            result[currency]['count'] += 1
            result[currency]['total'] += expense.amount
            result[currency]['total_in_rub'] += expense.amount_in_rub
        
        return result
    
    def get_expenses_display(self):
        """Возвращает отформатированную строку расходов"""
        by_currency = self.expenses_by_currency()
        if not by_currency:
            return "0 ₽"
        
        result = []
        for currency, data in by_currency.items():
            if currency == 'RUB':
                result.append(f"{data['total']} ₽")
            else:
                result.append(f"{data['total']}{data['symbol']}")
        
        return " + ".join(result) + f" ≈ {self.total_expenses():.2f} ₽"


class ExpenseCategory(models.Model):
    name = models.CharField(max_length=100, verbose_name='Название категории')
    description = models.TextField(blank=True, verbose_name='Описание')
    color = models.CharField(max_length=7, default='#007bff', verbose_name='Цвет (HEX)')
    
    class Meta:
        verbose_name = 'Категория расходов'
        verbose_name_plural = 'Категории расходов'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Expense(models.Model):
    CURRENCIES = [
        ('RUB', 'Рубли (₽)'),
        ('USD', 'Доллары ($)'),
        ('EUR', 'Евро (€)'),
    ]
    
    # Курсы валют для конвертации 
    EXCHANGE_RATES = {
        'RUB': Decimal('1.0'),
        'USD': Decimal('77.0'),  # 1 USD = 90 RUB
        'EUR': Decimal('90.4'),  # 1 EUR = 100 RUB
    }
    
    pet = models.ForeignKey(
        Pet, 
        on_delete=models.CASCADE, 
        related_name='expenses', 
        verbose_name='Питомец'
    )
    category = models.ForeignKey(
        ExpenseCategory, 
        on_delete=models.CASCADE, 
        verbose_name='Категория'
    )
    amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Сумма'
    )
    currency = models.CharField(
        max_length=3, 
        choices=CURRENCIES, 
        default='RUB', 
        verbose_name='Валюта'
    )
    date = models.DateField(verbose_name='Дата расхода')
    description = models.TextField(blank=True, verbose_name='Описание')
    receipt = models.ImageField(
        upload_to='receipts/%Y/%m/%d/', 
        blank=True, 
        null=True, 
        verbose_name='Чек'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата добавления')
    
    class Meta:
        verbose_name = 'Расход'
        verbose_name_plural = 'Расходы'
        ordering = ['-date', '-created_at']
    
    def __str__(self):
        return f"{self.pet.name} - {self.category.name} - {self.amount} {self.currency}"
    
    def get_currency_symbol(self):
        """Возвращает символ валюты"""
        symbols = {
            'RUB': '₽',
            'USD': '$',
            'EUR': '€'
        }
        return symbols.get(self.currency, self.currency)
    
    @property
    def amount_in_rub(self):
        """Конвертирует сумму в рубли"""
        rate = self.EXCHANGE_RATES.get(self.currency, Decimal('1.0'))
        return self.amount * rate
    
    def get_amount_with_symbol(self):
        """Возвращает сумму с символом валюты"""
        return f"{self.amount}{self.get_currency_symbol()}"
    
    def get_amount_display(self):
        """Возвращает отформатированную сумму с валютой"""
        return f"{self.amount} {self.get_currency_display()}"
    
    def get_converted_display(self):
        """Возвращает сумму в рублях с пометкой"""
        if self.currency == 'RUB':
            return f"{self.amount} ₽"
        else:
            return f"{self.amount}{self.get_currency_symbol()} ≈ {self.amount_in_rub:.2f} ₽"
    
    def save(self, *args, **kwargs):
        # Автоматически устанавливаем сегодняшнюю дату если не указана
        if not self.date:
            self.date = timezone.now().date()
        super().save(*args, **kwargs)
    
    @classmethod
    def get_total_in_rub(cls, queryset=None):
        """Возвращает общую сумму расходов в рублях"""
        if queryset is None:
            queryset = cls.objects.all()
        
        total = Decimal('0')
        for expense in queryset:
            total += expense.amount_in_rub
        return total
    
    @classmethod
    def get_statistics_by_currency(cls, queryset=None):
        """Возвращает статистику по валютам"""
        if queryset is None:
            queryset = cls.objects.all()
        
        stats = {}
        for expense in queryset:
            currency = expense.currency
            if currency not in stats:
                stats[currency] = {
                    'count': 0,
                    'total_amount': Decimal('0'),
                    'total_in_rub': Decimal('0'),
                    'symbol': expense.get_currency_symbol(),
                    'name': expense.get_currency_display()
                }
            
            stats[currency]['count'] += 1
            stats[currency]['total_amount'] += expense.amount
            stats[currency]['total_in_rub'] += expense.amount_in_rub
        
        return stats

@receiver(post_migrate)
def create_default_categories(sender, **kwargs):
    """Создает категории по умолчанию после миграций"""
    if sender.name == 'pets':  # Проверяем, что это наше приложение
        from django.db import transaction
        from django.db.utils import ProgrammingError
        
        try:
            with transaction.atomic():
                # Проверяем, есть ли уже категории
                if not ExpenseCategory.objects.exists():
                    categories = [
                        {'name': 'Корм', 'color': '#FF6384', 'description': 'Еда и лакомства'},
                        {'name': 'Ветеринар', 'color': '#36A2EB', 'description': 'Ветеринарные услуги'},
                        {'name': 'Игрушки', 'color': '#FFCE56', 'description': 'Игрушки и развлечения'},
                        {'name': 'Аксессуары', 'color': '#4BC0C0', 'description': 'Ошейники, поводки, миски'},
                        {'name': 'Груминг', 'color': '#9966FF', 'description': 'Стрижка, мытье, уход'},
                        {'name': 'Страхование', 'color': '#FF9F40', 'description': 'Медицинское страхование'},
                        {'name': 'Лекарства', 'color': '#8AC926', 'description': 'Лекарства и витамины'},
                        {'name': 'Транспорт', 'color': '#1982C4', 'description': 'Перевозка питомца'},
                        {'name': 'Обучение', 'color': '#6A4C93', 'description': 'Дрессировка и курсы'},
                        {'name': 'Другое', 'color': '#C9CBCF', 'description': 'Прочие расходы'},
                    ]
                    
                    for cat_data in categories:
                        ExpenseCategory.objects.create(**cat_data)
                    
                    print("✅ Созданы категории расходов по умолчанию")
                else:
                    print(f"ℹ️  В базе уже есть {ExpenseCategory.objects.count()} категорий")
        except (ProgrammingError, OperationalError):
            # Таблица еще не создана, пропускаем
            pass