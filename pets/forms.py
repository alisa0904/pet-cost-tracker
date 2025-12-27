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
            'date': DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
            'pet': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'currency': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Добавляем CSS классы ко всем полям
        for field_name, field in self.fields.items():
            if field_name not in ['pet', 'category', 'currency']:
                field.widget.attrs['class'] = 'form-control'
        
        # Фильтруем питомцев по владельцу
        if user:
            self.fields['pet'].queryset = Pet.objects.filter(owner=user)