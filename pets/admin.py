from django.contrib import admin
from .models import Pet, ExpenseCategory, Expense

@admin.register(Pet)
class PetAdmin(admin.ModelAdmin):
    list_display = ['name', 'species', 'breed', 'birth_date']

@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ['name']

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['pet', 'category', 'amount', 'date']
    list_filter = ['category', 'date']
    search_fields = ['pet__name', 'description']