from django import forms
from django.forms import DateInput
from .models import Pet, Expense, ExpenseCategory

class PetForm(forms.ModelForm):
    class Meta:
        model = Pet
        fields = ['name', 'species', 'breed', 'birth_date']
        widgets = {
            'birth_date': DateInput(attrs={'type': 'date'}),
            'species': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Добавляем CSS классы ко всем полям
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['pet', 'category', 'amount', 'currency', 'date', 'description', 'receipt']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': '0.01',
                'min': '0.01'
            }),
            'pet': forms.Select(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'currency': forms.Select(attrs={'class': 'form-control form-select'}),  # ВАЖНО!
            'receipt': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'pet': 'Питомец',
            'category': 'Категория',
            'amount': 'Сумма',
            'currency': 'Валюта',
            'date': 'Дата',
            'description': 'Описание',
            'receipt': 'Чек (фото)',
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            # Фильтруем питомцев только текущего пользователя
            self.fields['pet'].queryset = Pet.objects.filter(owner=user)
            
            # Добавляем placeholder для валюты
            self.fields['currency'].widget.attrs.update({'class': 'form-select'})