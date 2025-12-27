from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal

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