from django.contrib import admin
from django.utils.html import format_html
from .models import Pet, ExpenseCategory, Expense

@admin.register(Pet)
class PetAdmin(admin.ModelAdmin):
    list_display = ['name', 'species', 'breed', 'owner', 'birth_date']
    list_filter = ['species', 'owner']
    search_fields = ['name', 'breed']

@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'color_display', 'description']
    
    def color_display(self, obj):
        return format_html(
            '<span style="color: {};">⬤</span> {}',
            obj.color,
            obj.color
        )
    color_display.short_description = 'Цвет'

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['pet', 'category', 'amount', 'currency', 'date']
    list_filter = ['category', 'date', 'currency']
    search_fields = ['pet__name', 'description']
    date_hierarchy = 'date'