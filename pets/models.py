from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.utils import timezone
from django.db.models.signals import post_migrate
from django.db import OperationalError
from django.dispatch import receiver
from django.db.models import Sum, Count, F, ExpressionWrapper, DecimalField, Subquery, OuterRef
from django.conf import settings


class ExchangeRate(models.Model):
    """Модель для хранения исторических курсов валют"""
    CURRENCIES = [
        ('RUB', 'Рубли (₽)'),
        ('USD', 'Доллары ($)'),
        ('EUR', 'Евро (€)'),
    ]
    
    currency = models.CharField(max_length=3, choices=CURRENCIES, verbose_name='Валюта')
    rate = models.DecimalField(max_digits=10, decimal_places=4, verbose_name='Курс к рублю')
    date = models.DateField(auto_now_add=True, verbose_name='Дата курса')
    is_active = models.BooleanField(default=True, verbose_name='Актуальный курс')
    
    class Meta:
        verbose_name = 'Курс валюты'
        verbose_name_plural = 'Курсы валют'
        ordering = ['-date', 'currency']
        indexes = [
            models.Index(fields=['currency', '-date']),
            models.Index(fields=['is_active']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['currency', 'date'],
                name='unique_currency_rate_per_day'
            ),
        ]
    
    def __str__(self):
        return f"{self.get_currency_display()}: {self.rate} ({self.date})"
    
    @classmethod
    def get_latest_rate(cls, currency):
        """Получить последний актуальный курс валюты"""
        try:
            return cls.objects.filter(
                currency=currency, 
                is_active=True
            ).latest('date').rate
        except cls.DoesNotExist:
            # Возвращаем курс по умолчанию из настроек
            return Decimal(settings.DEFAULT_EXCHANGE_RATES.get(currency, '1.0'))
    
    @classmethod
    def get_rate_on_date(cls, currency, date):
        """Получить курс валюты на конкретную дату"""
        try:
            return cls.objects.filter(
                currency=currency,
                date__lte=date
            ).latest('date').rate
        except cls.DoesNotExist:
            return Decimal('1.0')


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
        """Общая сумма расходов на питомца в рублях (оптимизированная версия)"""
        result = self.expenses.with_rub_amount().aggregate(
            total=Sum('rub_amount')
        )
        return result['total'] or Decimal('0')
    
    @property
    def total_expenses_cached(self):
        """Кэшированная версия общей суммы расходов"""
        if not hasattr(self, '_total_expenses_cache'):
            self._total_expenses_cache = self.total_expenses()
        return self._total_expenses_cache
    
    def expenses_by_currency(self):
        """Возвращает расходы сгруппированные по валюте (оптимизированная версия)"""
        from django.db.models import Count as CountAgg
        
        expenses = self.expenses.values('currency').annotate(
            count=CountAgg('id'),
            total_amount=Sum('amount'),
            total_in_rub=Sum(
                ExpressionWrapper(
                    F('amount') * Subquery(
                        ExchangeRate.objects.filter(
                            currency=OuterRef('currency'),
                            date__lte=OuterRef('date')
                        ).order_by('-date').values('rate')[:1]
                    ),
                    output_field=DecimalField(max_digits=12, decimal_places=2)
                )
            )
        ).order_by('currency')
        
        result = {}
        for item in expenses:
            # Получаем символ валюты для отображения
            expense_sample = self.expenses.filter(currency=item['currency']).first()
            symbol = expense_sample.get_currency_symbol() if expense_sample else ''
            
            result[item['currency']] = {
                'count': item['count'],
                'total': item['total_amount'] or Decimal('0'),
                'total_in_rub': item['total_in_rub'] or Decimal('0'),
                'symbol': symbol
            }
        
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
        
        total_rub = sum(data['total_in_rub'] for data in by_currency.values())
        return " + ".join(result) + f" ≈ {total_rub:.2f} ₽"
    
    def expenses_count(self):
        """Количество расходов питомца"""
        return self.expenses.count()
    
    def last_expense_date(self):
        """Дата последнего расхода"""
        last_expense = self.expenses.order_by('-date').first()
        return last_expense.date if last_expense else None
    
    def average_expense(self):
        """Средний расход на питомца"""
        total = self.total_expenses()
        count = self.expenses_count()
        return total / count if count > 0 else Decimal('0')


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
    
    def expenses_count(self):
        """Количество расходов в категории"""
        return self.expense_set.count()


class ExpenseQuerySet(models.QuerySet):
    """Кастомный QuerySet для оптимизации запросов по расходам"""
    
    def with_rub_amount(self):
        """Аннотирует QuerySet полем rub_amount (сумма в рублях)"""
        return self.annotate(
            rub_amount=ExpressionWrapper(
                F('amount') * Subquery(
                    ExchangeRate.objects.filter(
                        currency=OuterRef('currency'),
                        date__lte=OuterRef('date')
                    ).order_by('-date').values('rate')[:1]
                ),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            )
        )
    
    def total_in_rub(self):
        """Возвращает общую сумму в рублях"""
        result = self.with_rub_amount().aggregate(
            total=Sum('rub_amount')
        )
        return result['total'] or Decimal('0')
    
    def statistics_by_currency(self):
        """Статистика по валютам"""
        from django.db.models import Count as CountAgg
        
        return self.values('currency').annotate(
            count=CountAgg('id'),
            total_amount=Sum('amount'),
            total_in_rub=Sum(
                ExpressionWrapper(
                    F('amount') * Subquery(
                        ExchangeRate.objects.filter(
                            currency=OuterRef('currency'),
                            date__lte=OuterRef('date')
                        ).order_by('-date').values('rate')[:1]
                    ),
                    output_field=DecimalField(max_digits=12, decimal_places=2)
                )
            )
        ).order_by('currency')


class Expense(models.Model):
    CURRENCIES = [
        ('RUB', 'Рубли (₽)'),
        ('USD', 'Доллары ($)'),
        ('EUR', 'Евро (€)'),
    ]
    
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
    
    objects = ExpenseQuerySet.as_manager()
    
    class Meta:
        verbose_name = 'Расход'
        verbose_name_plural = 'Расходы'
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['currency']),
            models.Index(fields=['pet', 'date']),
        ]
    
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
        """Конвертирует сумму в рубли по курсу на дату расхода"""
        rate = ExchangeRate.get_rate_on_date(self.currency, self.date)
        return self.amount * rate
    
    def get_amount_display(self):
        """Возвращает отформатированную сумму с валютой"""
        return f"{self.amount} {self.get_currency_symbol()}"
    
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
        
        # Проверяем, есть ли актуальный курс для этой даты
        try:
            ExchangeRate.objects.get_or_create(
                currency=self.currency,
                date=self.date,
                defaults={
                    'rate': ExchangeRate.get_latest_rate(self.currency),
                    'is_active': self.date == timezone.now().date()
                }
            )
        except Exception as e:
            # Логируем ошибку, но не прерываем сохранение расхода
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Не удалось создать/получить курс валюты: {e}")
        
        super().save(*args, **kwargs)
        
        # Сбрасываем кэш у связанного питомца
        if hasattr(self.pet, '_total_expenses_cache'):
            delattr(self.pet, '_total_expenses_cache')


@receiver(post_migrate)
def create_default_data(sender, **kwargs):
    """Создает данные по умолчанию после миграций"""
    # Проверяем, что это наше приложение
    app_config = kwargs.get('app_config')
    if app_config and app_config.name == 'pets':
        from django.db import transaction
        from django.db.utils import ProgrammingError
        
        try:
            with transaction.atomic():
                # Создаем категории по умолчанию
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
                    
                    print(" Созданы категории расходов по умолчанию")
                
                # Создаем начальные курсы валют
                if not ExchangeRate.objects.exists():
                    import datetime
                    today = datetime.date.today()
                    
                    default_rates = [
                        {'currency': 'RUB', 'rate': Decimal('1.0'), 'is_active': True},
                        {'currency': 'USD', 'rate': Decimal(settings.DEFAULT_EXCHANGE_RATES.get('USD', '77.0')), 'is_active': True},
                        {'currency': 'EUR', 'rate': Decimal(settings.DEFAULT_EXCHANGE_RATES.get('EUR', '90.4')), 'is_active': True},
                    ]
                    
                    for rate_data in default_rates:
                        ExchangeRate.objects.create(
                            currency=rate_data['currency'],
                            rate=rate_data['rate'],
                            date=today,
                            is_active=rate_data['is_active']
                        )
                    
                    print(" Созданы начальные курсы валют")
        except (ProgrammingError, OperationalError, ImportError) as e:
            # Игнорируем ошибки при инициализации
            pass