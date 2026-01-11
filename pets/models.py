from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal
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
        """Общая сумма расходов на питомца"""
        total = self.expenses.aggregate(total=models.Sum('amount'))['total']
        return total if total else 0


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