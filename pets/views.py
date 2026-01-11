from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Sum, Count, Avg, Q, Min, Max
from django.utils import timezone
from datetime import timedelta, datetime
from django.core.paginator import Paginator
from django.http import HttpResponse
import json
from django.views.generic import UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
import io
import base64
from django.db.models.functions import TruncMonth, TruncDate, ExtractMonth, ExtractYear
import matplotlib
matplotlib.use('Agg')  # Важно: устанавливаем бэкенд ДО импорта pyplot
import matplotlib.pyplot as plt
from .models import Pet, Expense, ExpenseCategory
from .forms import PetForm, ExpenseForm

# Проверка доступности matplotlib для аналитики
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError as e:
    print(f"Matplotlib import error: {e}")
    MATPLOTLIB_AVAILABLE = False
    plt = None
    np = None

# ==================== АУТЕНТИФИКАЦИЯ ====================

def login_view(request):
    """Обработчик входа в систему"""
    if request.user.is_authenticated:
        return redirect('pets:home')
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f'Добро пожаловать, {username}!')
                next_page = request.GET.get('next', 'pets:home')
                return redirect(next_page)
        else:
            messages.error(request, 'Неправильное имя пользователя или пароль')
    else:
        form = AuthenticationForm()
    
    return render(request, 'registration/login.html', {'form': form})

def logout_view(request):
    """Выход из системы"""
    logout(request)
    messages.success(request, 'Вы успешно вышли из системы')
    return redirect('pets:home')

def register_view(request):
    """Регистрация нового пользователя"""
    if request.user.is_authenticated:
        return redirect('pets:home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        email = request.POST.get('email', '')
        
        if password != password2:
            messages.error(request, 'Пароли не совпадают')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Пользователь с таким именем уже существует')
        else:
            user = User.objects.create_user(
                username=username, 
                password=password, 
                email=email
            )
            login(request, user)
            messages.success(request, f'Аккаунт {username} успешно создан!')
            return redirect('pets:home')
    
    return render(request, 'registration/register.html')

def create_default_data():
    """Создание тестовых данных"""
    try:
        # Создаем администратора
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123'
            )
            print("✅ Создан администратор: admin / admin123")
        
        # Создаем тестового пользователя
        if not User.objects.filter(username='test').exists():
            User.objects.create_user(
                username='test',
                email='test@example.com',
                password='test123'
            )
            print("✅ Создан тестовый пользователь: test / test123")
        
        # Создаем категории, если их нет
        if not ExpenseCategory.objects.exists():
            categories = [
                {'name': 'Корм', 'color': '#FF6384'},
                {'name': 'Ветеринар', 'color': '#36A2EB'},
                {'name': 'Игрушки', 'color': '#FFCE56'},
                {'name': 'Аксессуары', 'color': '#4BC0C0'},
                {'name': 'Груминг', 'color': '#9966FF'},
                {'name': 'Страхование', 'color': '#FF9F40'},
                {'name': 'Лекарства', 'color': '#8AC926'},
                {'name': 'Другое', 'color': '#C9CBCF'},
            ]
            for cat in categories:
                ExpenseCategory.objects.create(name=cat['name'], color=cat['color'])
            print("✅ Созданы категории расходов по умолчанию")
        else:
            print(f"ℹ️  В базе уже есть {ExpenseCategory.objects.count()} категорий")
            
    except Exception as e:
        print(f"⚠️  Ошибка создания данных: {e}")

# Вызываем создание данных при импорте
try:
    create_default_data()
except:
    pass

# ==================== ОСНОВНЫЕ VIEW ====================

def home(request):
    """Главная страница с общей статистикой"""
    if request.user.is_authenticated:
        pets = Pet.objects.filter(owner=request.user)
        expenses = Expense.objects.filter(pet__owner=request.user)
    else:
        pets = Pet.objects.all()
        expenses = Expense.objects.all()
    
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
    
    monthly_data = expenses.annotate(
        month=TruncMonth('date')
    ).values('month').annotate(
        total=Sum('amount')
    ).order_by('month')[:6]
    
    # Форматируем данные для шаблона
    monthly_data_formatted = [
        {'month': item['month'].strftime('%Y-%m'), 'total': item['total']}
        for item in monthly_data
    ]
    
    context = {
        'pets': pets,
        'total_expenses': total_expenses,
        'monthly_expenses': monthly_expenses,
        'recent_expenses': recent_expenses,
        'category_stats': category_stats,
        'pet_stats': pet_stats,
        'monthly_data': monthly_data_formatted,
        'pet_count': pets.count(),
        'expense_count': expenses.count(),
    }
    return render(request, 'home.html', context)

@login_required
def pet_list(request):
    """Список всех питомцев пользователя с суммарными расходами"""
    if request.user.is_authenticated:
        pets = Pet.objects.filter(owner=request.user)
    else:
        pets = Pet.objects.all()
    
    pets = pets.annotate(
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
    paginator = Paginator(pets, 9)
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
    pet = get_object_or_404(Pet, pk=pk)
    
    if request.user.is_authenticated and pet.owner != request.user:
        messages.error(request, 'У вас нет доступа к этому питомцу')
        return redirect('pets:pet_list')
    
    expenses = pet.expenses.all().order_by('-date')
    
    # Статистика
    total_spent = expenses.aggregate(total=Sum('amount'))['total'] or 0
    avg_expense = expenses.aggregate(avg=Avg('amount'))['avg'] or 0
    
    # Расходы по категориям
    by_category = expenses.values('category__name', 'category__color').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')
    
    monthly_expenses = expenses.annotate(
        month=TruncMonth('date')
    ).values('month').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-month')
    
    # Форматируем для шаблона
    monthly_expenses_formatted = []
    for item in monthly_expenses[:12]:
        monthly_expenses_formatted.append({
            'month': item['month'].strftime('%Y-%m'),
            'total': item['total'],
            'count': item['count']
        })
    
    # Последние расходы
    recent_expenses = expenses[:10]
    
    context = {
        'pet': pet,
        'expenses': recent_expenses,
        'total_spent': total_spent,
        'avg_expense': avg_expense,
        'by_category': by_category,
        'monthly_expenses': monthly_expenses_formatted,
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
    if request.user.is_authenticated:
        expenses = Expense.objects.filter(pet__owner=request.user)
    else:
        expenses = Expense.objects.all()
    
    expenses = expenses.select_related('pet', 'category')
    
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
    paginator = Paginator(expenses, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Статистика
    total_amount = expenses.aggregate(total=Sum('amount'))['total'] or 0
    avg_amount = expenses.aggregate(avg=Avg('amount'))['avg'] or 0
    
    context = {
        'page_obj': page_obj,
        'total_amount': total_amount,
        'avg_amount': avg_amount,
        'pets': Pet.objects.all() if not request.user.is_authenticated else Pet.objects.filter(owner=request.user),
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
    # Создаем категории если их нет
    if ExpenseCategory.objects.count() == 0:
        categories = [
            {'name': 'Корм', 'color': '#FF6384'},
            {'name': 'Ветеринар', 'color': '#36A2EB'},
            {'name': 'Игрушки', 'color': '#FFCE56'},
            {'name': 'Аксессуары', 'color': '#4BC0C0'},
            {'name': 'Груминг', 'color': '#9966FF'},
            {'name': 'Страхование', 'color': '#FF9F40'},
            {'name': 'Лекарства', 'color': '#8AC926'},
            {'name': 'Другое', 'color': '#C9CBCF'},
        ]
        for cat in categories:
            ExpenseCategory.objects.create(name=cat['name'], color=cat['color'])
        messages.info(request, 'Созданы категории расходов по умолчанию')
    
    if request.method == 'POST':
        form = ExpenseForm(request.user, request.POST, request.FILES)
        if form.is_valid():
            expense = form.save()
            messages.success(request, 
                f'Расход на сумму {expense.amount}₽ успешно добавлен для {expense.pet.name}!')
            return redirect('pets:expense_list')
    else:
        form = ExpenseForm(user=request.user)
        
        # Если передан параметр pet в GET
        pet_id = request.GET.get('pet')
        if pet_id:
            try:
                pet = Pet.objects.get(id=pet_id)
                if request.user.is_authenticated and pet.owner != request.user:
                    messages.error(request, 'Вы не можете добавлять расходы для этого питомца')
                else:
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
    """
    Страница аналитики с переключением между таблицами и графиками
    """
    # Получаем данные
    if request.user.is_authenticated:
        pets = Pet.objects.filter(owner=request.user)
        expenses = Expense.objects.filter(pet__owner=request.user)
    else:
        pets = Pet.objects.all()
        expenses = Expense.objects.all()
    
    if not expenses.exists():
        return render(request, 'pets/analytics.html', {
            'pets': pets,
            'no_data': True,
            'matplotlib_error': not MATPLOTLIB_AVAILABLE
        })
    
    # Определяем режим отображения
    view_mode = request.GET.get('view', 'table')
    period = request.GET.get('period', 'month')
    
    # ==================== РЕЖИМ ГРАФИКОВ ====================
    if view_mode == 'charts':
        if not MATPLOTLIB_AVAILABLE:
            return render(request, 'pets/analytics.html', {
                'pets': pets,
                'no_data': False,
                'view_mode': 'charts',
                'matplotlib_error': True,
                'period': period,
                'stats': None,
                'chart1': None,
                'chart2': None,
                'chart3': None
            })
        
        # Определяем даты для фильтрации
        today = timezone.now().date()
        if period == 'week':
            start_date = today - timedelta(days=7)
        elif period == 'month':
            start_date = today - timedelta(days=30)
        elif period == 'year':
            start_date = today - timedelta(days=365)
        else:
            start_date = today - timedelta(days=30)
        
        # Фильтруем расходы
        filtered_expenses = expenses.filter(date__gte=start_date)
        
        # Если нет данных за период, показываем всё
        if not filtered_expenses.exists():
            filtered_expenses = expenses
        
        # Статистика
        stats = {
            'total_expenses': filtered_expenses.aggregate(Sum('amount'))['amount__sum'] or 0,
            'average_expense': filtered_expenses.aggregate(Avg('amount'))['amount__avg'] or 0,
            'expense_count': filtered_expenses.count(),
        }
        
        # ГРАФИК 1: Круговая диаграмма по категориям
        chart1 = None
        try:
            category_data = filtered_expenses.values('category__name').annotate(
                total=Sum('amount')
            ).order_by('-total')[:6]
            
            if category_data:
                categories = []
                amounts = []
                
                for item in category_data:
                    cat_name = item['category__name'] or 'Без категории'
                    if cat_name:
                        categories.append(cat_name[:15])
                        amounts.append(float(item['total']))
                
                if categories and amounts:
                    fig, ax = plt.subplots(figsize=(8, 8))
                    colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40']
                    ax.pie(amounts, labels=categories, colors=colors[:len(categories)], 
                          autopct='%1.1f%%', startangle=90)
                    ax.set_title('Расходы по категориям', fontsize=14)
                    ax.axis('equal')
                    
                    buf1 = io.BytesIO()
                    fig.savefig(buf1, format='png', dpi=80, bbox_inches='tight')
                    buf1.seek(0)
                    chart1 = base64.b64encode(buf1.getvalue()).decode('utf-8')
                    buf1.close()
                    plt.close(fig)
        except Exception as e:
            print(f"Ошибка при построении графика 1: {e}")
            chart1 = None
        finally:
            if 'fig' in locals():
                plt.close(fig)
        
        # ГРАФИК 2: Линейный график по времени
        chart2 = None
        try:
            # Группируем по дням или месяцам в зависимости от периода
            if period == 'week':
                date_data = filtered_expenses.annotate(
                    day=TruncDate('date')
                ).values('day').annotate(
                    total=Sum('amount')
                ).order_by('day')
            else:
                date_data = filtered_expenses.annotate(
                    month=TruncMonth('date')
                ).values('month').annotate(
                    total=Sum('amount')
                ).order_by('month')
            
            if date_data:
                dates = []
                amounts = []
                
                for item in date_data:
                    if 'day' in item:
                        dates.append(item['day'].strftime('%d.%m'))
                    else:
                        dates.append(item['month'].strftime('%b %Y'))
                    amounts.append(float(item['total']))
                
                if len(dates) > 1:
                    fig, ax = plt.subplots(figsize=(10, 5))
                    ax.plot(dates, amounts, marker='o', linewidth=2, color='#36A2EB')
                    ax.fill_between(dates, amounts, alpha=0.2, color='#36A2EB')
                    ax.set_title('Динамика расходов', fontsize=14)
                    ax.set_xlabel('Период')
                    ax.set_ylabel('Сумма (руб)')
                    ax.grid(True, alpha=0.3)
                    plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
                    plt.tight_layout()
                    
                    buf2 = io.BytesIO()
                    fig.savefig(buf2, format='png', dpi=80)
                    buf2.seek(0)
                    chart2 = base64.b64encode(buf2.getvalue()).decode('utf-8')
                    buf2.close()
                    plt.close(fig)
        except Exception as e:
            print(f"Ошибка при построении графика 2: {e}")
            chart2 = None
        finally:
            if 'fig' in locals():
                plt.close(fig)
        
        # ГРАФИК 3: Столбчатая диаграмма по питомцам
        chart3 = None
        try:
            pet_data = filtered_expenses.values('pet__name').annotate(
                total=Sum('amount')
            ).order_by('-total')[:5]
            
            if pet_data:
                pet_names = []
                pet_amounts = []
                
                for item in pet_data:
                    name = item['pet__name'] or 'Без имени'
                    if name:
                        pet_names.append(name[:12])
                        pet_amounts.append(float(item['total']))
                
                if pet_names and pet_amounts:
                    fig, ax = plt.subplots(figsize=(10, 6))
                    colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF']
                    bars = ax.bar(pet_names, pet_amounts, color=colors[:len(pet_names)])
                    ax.set_title('Расходы по питомцам', fontsize=14)
                    ax.set_xlabel('Питомец')
                    ax.set_ylabel('Сумма (руб)')
                    ax.grid(axis='y', alpha=0.3)
                    
                    # Добавляем значения на столбцы
                    for bar in bars:
                        height = bar.get_height()
                        ax.text(bar.get_x() + bar.get_width()/2., height,
                               f'{height:,.0f}₽',
                               ha='center', va='bottom')
                    
                    plt.tight_layout()
                    
                    buf3 = io.BytesIO()
                    fig.savefig(buf3, format='png', dpi=80)
                    buf3.seek(0)
                    chart3 = base64.b64encode(buf3.getvalue()).decode('utf-8')
                    buf3.close()
                    plt.close(fig)
        except Exception as e:
            print(f"Ошибка при построении графика 3: {e}")
            chart3 = None
        finally:
            if 'fig' in locals():
                plt.close(fig)
        
        context = {
            'pets': pets,
            'view_mode': view_mode,
            'period': period,
            'stats': stats,
            'chart1': chart1,
            'chart2': chart2,
            'chart3': chart3,
            'no_data': not filtered_expenses.exists(),
            'matplotlib_error': False,
            'filtered_data_count': filtered_expenses.count(),
            'all_data_count': expenses.count(),
            'start_date': start_date,
            'end_date': today,
        }
    
    # ==================== РЕЖИМ ТАБЛИЦ ====================
    else:
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
        monthly_stats = expenses.annotate(
            month=TruncMonth('date')
        ).values('month').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('month')
        
        # Форматируем для шаблона
        monthly_stats_formatted = []
        for item in monthly_stats:
            monthly_stats_formatted.append({
                'month': item['month'].strftime('%Y-%m'),
                'total': item['total'],
                'count': item['count']
            })
        
        # Сравнение с предыдущим месяцем
        current_month_start = datetime.now().replace(day=1)
        current_month_expenses = expenses.filter(
            date__gte=current_month_start
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        prev_month_end = current_month_start - timedelta(days=1)
        prev_month_start = prev_month_end.replace(day=1)
        prev_month_expenses = expenses.filter(
            date__gte=prev_month_start,
            date__lte=prev_month_end
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Изменение в процентах
        if prev_month_expenses > 0:
            change_percent = ((current_month_expenses - prev_month_expenses) / prev_month_expenses) * 100
        else:
            change_percent = 100 if current_month_expenses > 0 else 0
        
        context = {
            'pets': pets,
            'view_mode': view_mode,
            'total_stats': total_stats,
            'by_category': by_category,
            'by_pet': by_pet,
            'monthly_stats': monthly_stats_formatted,
            'current_month_expenses': current_month_expenses,
            'prev_month_expenses': prev_month_expenses,
            'change_percent': change_percent,
            'expense_count': expenses.count(),
            'pet_count': pets.count(),
            'current_month': current_month_start.strftime('%Y-%m'),
            'no_data': False,
            'matplotlib_error': not MATPLOTLIB_AVAILABLE,
        }
    
    return render(request, 'pets/analytics.html', context)

def export_expenses_csv(request):
    """Экспорт расходов в CSV"""
    import csv
    
    expenses = Expense.objects.all()
    
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

class PetUpdateView(LoginRequiredMixin, UpdateView):
    """Редактирование питомца"""
    model = Pet
    form_class = PetForm
    template_name = 'pets/pet_form.html'
    
    def get_queryset(self):
        if self.request.user.is_authenticated:
            return Pet.objects.filter(owner=self.request.user)
        return Pet.objects.all()
    
    def get_success_url(self):
        messages.success(self.request, f'Питомец "{self.object.name}" успешно обновлен!')
        return reverse_lazy('pets:pet_detail', kwargs={'pk': self.object.pk})

class ExpenseUpdateView(LoginRequiredMixin, UpdateView):
    """Редактирование расхода"""
    model = Expense
    template_name = 'pets/expense_form.html'
    
    def get_form_class(self):
        class ExpenseUpdateForm(ExpenseForm):
            def __init__(self, *args, **kwargs):
                kwargs['user'] = self.request.user
                super().__init__(*args, **kwargs)
        
        return ExpenseUpdateForm
    
    def get_queryset(self):
        if self.request.user.is_authenticated:
            return Expense.objects.filter(pet__owner=self.request.user)
        return Expense.objects.all()
    
    def get_success_url(self):
        messages.success(self.request, f'Расход успешно обновлен!')
        return reverse_lazy('pets:expense_list')

class PetDeleteView(LoginRequiredMixin, DeleteView):
    """Удаление питомца"""
    model = Pet
    template_name = 'pets/pet_confirm_delete.html'
    success_url = reverse_lazy('pets:pet_list')
    
    def get_queryset(self):
        if self.request.user.is_authenticated:
            return Pet.objects.filter(owner=self.request.user)
        return Pet.objects.all()
    
    def delete(self, request, *args, **kwargs):
        pet = self.get_object()
        messages.success(request, f'Питомец "{pet.name}" успешно удален!')
        return super().delete(request, *args, **kwargs)

class ExpenseDeleteView(LoginRequiredMixin, DeleteView):
    """Удаление расхода"""
    model = Expense
    template_name = 'pets/expense_confirm_delete.html'
    success_url = reverse_lazy('pets:expense_list')
    
    def get_queryset(self):
        if self.request.user.is_authenticated:
            return Expense.objects.filter(pet__owner=self.request.user)
        return Expense.objects.all()
    
    def delete(self, request, *args, **kwargs):
        expense = self.get_object()
        messages.success(request, f'Расход на сумму {expense.amount}₽ успешно удален!')
        return super().delete(request, *args, **kwargs)

def global_search(request):
    """Глобальный поиск по всем данным"""
    query = request.GET.get('q', '').strip()
    
    if not query:
        return redirect('pets:home')
    
    # Поиск по питомцам
    pets = Pet.objects.all().filter(
        Q(name__icontains=query) |
        Q(breed__icontains=query) |
        Q(species__icontains=query) |
        Q(notes__icontains=query)
    )[:10]
    
    # Поиск по расходам
    expenses = Expense.objects.all().filter(
        Q(description__icontains=query) |
        Q(category__name__icontains=query) |
        Q(notes__icontains=query)
    ).select_related('pet', 'category')[:10]
    
    # Статистика поиска
    total_results = pets.count() + expenses.count()
    
    context = {
        'query': query,
        'pets': pets,
        'expenses': expenses,
        'total_results': total_results,
        'pet_count': pets.count(),
        'expense_count': expenses.count(),
    }
    
    return render(request, 'pets/search_results.html', context)