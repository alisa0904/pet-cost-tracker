from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from datetime import timedelta
from .models import Pet, Expense, ExpenseCategory
from .forms import PetForm, ExpenseForm

@login_required
def home(request):
    """Главная страница с общей статистикой"""
    pets = Pet.objects.filter(owner=request.user)
    expenses = Expense.objects.filter(pet__owner=request.user)
    
    # Общая статистика
    total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or 0
    
    # Расходы за последние 30 дней
    last_month = timezone.now().date() - timedelta(days=30)
    monthly_expenses = expenses.filter(
        date__gte=last_month
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Последние расходы
    recent_expenses = expenses.order_by('-date')[:5]
    
    # Статистика по категориям
    category_stats = expenses.values(
        'category__name', 'category__color'
    ).annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')[:5]
    
    context = {
        'pets': pets,
        'total_expenses': total_expenses,
        'monthly_expenses': monthly_expenses,
        'recent_expenses': recent_expenses,
        'category_stats': category_stats,
        'pet_count': pets.count(),
        'expense_count': expenses.count(),
    }
    return render(request, 'pets/home.html', context)

@login_required
def pet_list(request):
    """Список всех питомцев пользователя"""
    pets = Pet.objects.filter(owner=request.user).annotate(
        total_spent=Sum('expenses__amount'),
        expense_count=Count('expenses')
    )
    
    context = {
        'pets': pets,
    }
    return render(request, 'pets/pet_list.html', context)

@login_required
def pet_detail(request, pk):
    """Детальная информация о питомце"""
    pet = get_object_or_404(Pet, pk=pk, owner=request.user)
    expenses = pet.expenses.all().order_by('-date')
    
    # Статистика по категориям
    category_stats = expenses.values(
        'category__name', 'category__color'
    ).annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')
    
    # Расходы по месяцам
    monthly_stats = expenses.extra(
        select={'month': "strftime('%%Y-%%m', date)"}
    ).values('month').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-month')[:6]
    
    context = {
        'pet': pet,
        'expenses': expenses[:10],  # Последние 10 расходов
        'category_stats': category_stats,
        'monthly_stats': monthly_stats,
        'total_spent': expenses.aggregate(total=Sum('amount'))['total'] or 0,
        'avg_expense': expenses.aggregate(avg=Avg('amount'))['avg'] or 0,
        'expense_count': expenses.count(),
    }
    return render(request, 'pets/pet_detail.html', context)

@login_required
def pet_add(request):
    """Добавление нового питомца"""
    if request.method == 'POST':
        form = PetForm(request.POST)
        if form.is_valid():
            pet = form.save(commit=False)
            pet.owner = request.user
            pet.save()
            messages.success(request, f'Питомец "{pet.name}" успешно добавлен!')
            return redirect('pets:pet_list')
    else:
        form = PetForm()
    
    context = {
        'form': form,
        'title': 'Добавить питомца',
    }
    return render(request, 'pets/form.html', context)

@login_required
def expense_list(request):
    """Список всех расходов"""
    expenses = Expense.objects.filter(pet__owner=request.user).order_by('-date')
    
    # Фильтрация
    pet_id = request.GET.get('pet')
    category_id = request.GET.get('category')
    month = request.GET.get('month')
    
    if pet_id:
        expenses = expenses.filter(pet_id=pet_id)
    if category_id:
        expenses = expenses.filter(category_id=category_id)
    if month:
        year, month_num = month.split('-')
        expenses = expenses.filter(date__year=year, date__month=month_num)
    
    # Общая сумма отфильтрованных расходов
    total_amount = expenses.aggregate(total=Sum('amount'))['total'] or 0
    
    context = {
        'expenses': expenses,
        'total_amount': total_amount,
        'pets': Pet.objects.filter(owner=request.user),
        'categories': ExpenseCategory.objects.all(),
        'selected_pet': pet_id,
        'selected_category': category_id,
        'selected_month': month,
    }
    return render(request, 'pets/expense_list.html', context)

@login_required
def expense_add(request):
    """Добавление нового расхода"""
    if request.method == 'POST':
        form = ExpenseForm(request.user, request.POST, request.FILES)
        if form.is_valid():
            expense = form.save()
            messages.success(request, 
                f'Расход на сумму {expense.amount}₽ успешно добавлен для {expense.pet.name}!')
            return redirect('pets:expense_list')
    else:
        form = ExpenseForm(user=request.user)
    
    context = {
        'form': form,
        'title': 'Добавить расход',
    }
    return render(request, 'pets/form.html', context)

@login_required
def analytics(request):
    """Страница аналитики"""
    pets = Pet.objects.filter(owner=request.user)
    expenses = Expense.objects.filter(pet__owner=request.user)
    
    if not expenses.exists():
        return render(request, 'pets/analytics.html', {
            'pets': pets,
            'no_data': True
        })
    
    # Общая статистика
    total_stats = expenses.aggregate(
        total=Sum('amount'),
        avg=Avg('amount'),
        count=Count('id')
    )
    
    # По категориям
    by_category = expenses.values(
        'category__name', 'category__color'
    ).annotate(
        total=Sum('amount'),
        count=Count('id'),
        avg=Avg('amount')
    ).order_by('-total')
    
    # По питомцам
    by_pet = expenses.values(
        'pet__name'
    ).annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')
    
    # По месяцам
    monthly_stats = expenses.extra(
        select={'month': "strftime('%%Y-%%m', date)"}
    ).values('month').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('month')
    
    context = {
        'pets': pets,
        'total_stats': total_stats,
        'by_category': by_category,
        'by_pet': by_pet,
        'monthly_stats': monthly_stats,
        'expense_count': expenses.count(),
        'pet_count': pets.count(),
    }
    return render(request, 'pets/analytics.html', context)