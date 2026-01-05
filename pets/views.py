from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from datetime import timedelta, datetime
from django.core.paginator import Paginator
from django.http import HttpResponse
import json

from .models import Pet, Expense, ExpenseCategory
from .forms import PetForm, ExpenseForm
from django.db.models import Min, Max

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
    
    # Расходы по питомцам
    pet_stats = pets.annotate(
        total_spent=Sum('expenses__amount'),
        expense_count=Count('expenses')
    ).order_by('-total_spent')[:3]
    
    # Расходы по месяцам (для графика)
    monthly_data = expenses.extra(
        select={'month': "strftime('%%Y-%%m', date)"}
    ).values('month').annotate(
        total=Sum('amount')
    ).order_by('month')[:6]
    
    context = {
        'pets': pets,
        'total_expenses': total_expenses,
        'monthly_expenses': monthly_expenses,
        'recent_expenses': recent_expenses,
        'category_stats': category_stats,
        'pet_stats': pet_stats,
        'monthly_data': list(monthly_data),
        'pet_count': pets.count(),
        'expense_count': expenses.count(),
    }
    return render(request, 'pets/home.html', context)

@login_required
def pet_list(request):
    """Список всех питомцев пользователя с суммарными расходами"""
    pets = Pet.objects.filter(owner=request.user).annotate(
        total_expenses=Sum('expenses__amount'),
        expense_count=Count('expenses')
    )
    
    # Сортировка
    sort_by = request.GET.get('sort', 'name')
    if sort_by == 'expenses':
        pets = pets.order_by('-total_expenses')
    elif sort_by == 'age':
        pets = pets.order_by('birth_date')
    else:
        pets = pets.order_by('name')
    
    # Поиск
    search_query = request.GET.get('search', '')
    if search_query:
        pets = pets.filter(
            Q(name__icontains=search_query) |
            Q(breed__icontains=search_query) |
            Q(species__icontains=search_query)
        )
    
    # Пагинация
    paginator = Paginator(pets, 9)  # 9 питомцев на странице
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'sort_by': sort_by,
        'search_query': search_query,
        'total_pets': pets.count(),
        'total_all_expenses': pets.aggregate(total=Sum('total_expenses'))['total'] or 0,
    }
    return render(request, 'pets/pet_list.html', context)

@login_required
def pet_detail(request, pk):
    """Детальная страница питомца со всеми расходами"""
    pet = get_object_or_404(Pet, pk=pk, owner=request.user)
    expenses = pet.expenses.all().order_by('-date')
    
    # Статистика
    total_spent = expenses.aggregate(total=Sum('amount'))['total'] or 0
    avg_expense = expenses.aggregate(avg=Avg('amount'))['avg'] or 0
    
    # Расходы по категориям
    by_category = expenses.values('category__name', 'category__color').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')
    
    # Расходы по месяцам
    monthly_expenses = expenses.extra(
        select={'month': "strftime('%%Y-%%m', date)"}
    ).values('month').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-month')
    
    # Последние расходы
    recent_expenses = expenses[:10]
    
    context = {
        'pet': pet,
        'expenses': recent_expenses,
        'total_spent': total_spent,
        'avg_expense': avg_expense,
        'by_category': by_category,
        'monthly_expenses': monthly_expenses[:12],  # Последние 12 месяцев
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
    """Список всех расходов с фильтрацией"""
    expenses = Expense.objects.filter(pet__owner=request.user).select_related('pet', 'category')
    
    # Фильтры
    pet_filter = request.GET.get('pet')
    category_filter = request.GET.get('category')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    search_query = request.GET.get('search', '')
    
    if pet_filter:
        expenses = expenses.filter(pet_id=pet_filter)
    if category_filter:
        expenses = expenses.filter(category_id=category_filter)
    if date_from:
        expenses = expenses.filter(date__gte=date_from)
    if date_to:
        expenses = expenses.filter(date__lte=date_to)
    if search_query:
        expenses = expenses.filter(
            Q(description__icontains=search_query) |
            Q(pet__name__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )
    
    # Сортировка
    sort_by = request.GET.get('sort', '-date')
    expenses = expenses.order_by(sort_by)
    
    # Пагинация
    paginator = Paginator(expenses, 15)  # 15 расходов на странице
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Статистика фильтрованных данных
    total_amount = expenses.aggregate(total=Sum('amount'))['total'] or 0
    avg_amount = expenses.aggregate(avg=Avg('amount'))['avg'] or 0
    
    context = {
        'page_obj': page_obj,
        'total_amount': total_amount,
        'avg_amount': avg_amount,
        'pets': Pet.objects.filter(owner=request.user),
        'categories': ExpenseCategory.objects.all(),
        'filters': {
            'pet': pet_filter,
            'category': category_filter,
            'date_from': date_from,
            'date_to': date_to,
            'sort': sort_by,
            'search': search_query,
        },
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
        
        # Если передан параметр pet в GET, установим его по умолчанию
        pet_id = request.GET.get('pet')
        if pet_id:
            try:
                pet = Pet.objects.get(id=pet_id, owner=request.user)
                form.initial['pet'] = pet
            except Pet.DoesNotExist:
                pass
    
    context = {
        'form': form,
        'title': 'Добавить расход',
    }
    return render(request, 'pets/form.html', context)

@login_required
def analytics(request):
    """Страница аналитики с графиками"""
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
        count=Count('id'),
        min=Min('amount'),
        max=Max('amount')
    )
    
    # Статистика по категориям
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
    
    # Подготовка данных для графика
    chart_data = {
        'labels': [item['category__name'] for item in by_category],
        'data': [float(item['total']) for item in by_category],
        'colors': [item['category__color'] for item in by_category],
    }
    
    # Статистика за текущий месяц
    current_month = datetime.now().strftime('%Y-%m')
    current_month_expenses = expenses.extra(
        where=[f"strftime('%%Y-%%m', date) = '{current_month}'"]
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Сравнение с предыдущим месяцем
    prev_month = (datetime.now().replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
    prev_month_expenses = expenses.extra(
        where=[f"strftime('%%Y-%%m', date) = '{prev_month}'"]
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Изменение в процентах
    if prev_month_expenses > 0:
        change_percent = ((current_month_expenses - prev_month_expenses) / prev_month_expenses) * 100
    else:
        change_percent = 100 if current_month_expenses > 0 else 0
    
    context = {
        'pets': pets,
        'total_stats': total_stats,
        'by_category': by_category,
        'by_pet': by_pet,
        'monthly_stats': monthly_stats,
        'chart_data': json.dumps(chart_data),
        'current_month_expenses': current_month_expenses,
        'prev_month_expenses': prev_month_expenses,
        'change_percent': change_percent,
        'expense_count': expenses.count(),
        'pet_count': pets.count(),
        'current_month': current_month,
    }
    return render(request, 'pets/analytics.html', context)

@login_required
def export_expenses_csv(request):
    """Экспорт расходов в CSV"""
    import csv
    from django.http import HttpResponse
    
    expenses = Expense.objects.filter(pet__owner=request.user)
    
    # Создаем HTTP-ответ с CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="expenses.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Дата', 'Питомец', 'Категория', 'Сумма', 'Валюта', 'Описание'])
    
    for expense in expenses:
        writer.writerow([
            expense.date,
            expense.pet.name,
            expense.category.name,
            expense.amount,
            expense.currency,
            expense.description
        ])
    
    return response

