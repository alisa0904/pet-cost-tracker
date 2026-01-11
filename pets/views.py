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

from .models import Pet, Expense, ExpenseCategory
from .forms import PetForm, ExpenseForm

# Для графиков Matplotlib
try:
    import matplotlib
    matplotlib.use('Agg')  # Для работы без GUI
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    plt = None

# ==================== АУТЕНТИФИКАЦИЯ ====================

def login_view(request):
    """Обработчик входа в систему"""
    # Если пользователь уже авторизован, перенаправляем на главную
    if request.user.is_authenticated:
        return redirect('pets:home')
    
    if request.method == 'POST':
        # Используем стандартную форму Django
        form = AuthenticationForm(request, data=request.POST)
        
        if form.is_valid():
            # Аутентифицируем пользователя
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f'Добро пожаловать, {username}!')
                # Перенаправляем на главную или на следующую страницу
                next_page = request.GET.get('next', 'pets:home')
                return redirect(next_page)
        else:
            # Если форма не валидна, показываем ошибку
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

def emergency_login(request):
    """Экстренный вход для тестирования (создает пользователя если нет)"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Простая проверка для теста
        if username == 'admin' and password == 'admin123':
            try:
                user = User.objects.get(username='admin')
                # Обновляем пароль на всякий случай
                user.set_password('admin123')
                user.save()
            except User.DoesNotExist:
                # Создаем суперпользователя
                user = User.objects.create_superuser(
                    username='admin',
                    email='admin@example.com',
                    password='admin123'
                )
            
            # Логиним
            login(request, user)
            messages.success(request, 'Экстренный вход выполнен!')
            return redirect('pets:home')
        else:
            messages.error(request, 'Неправильные тестовые данные')
    
    return render(request, 'registration/login.html')

def create_default_users():
    """Создание пользователей по умолчанию при запуске приложения"""
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
    except Exception as e:
        print(f"⚠️  Ошибка создания пользователей: {e}")

# Вызываем создание пользователей при импорте
try:
    create_default_users()
except:
    pass  # Игнорируем ошибки при миграциях

# ==================== ОСНОВНЫЕ VIEW ====================

def home(request):
    """Главная страница с общей статистикой"""
    # Обрабатываем аутентифицированных и анонимных пользователей
    if request.user.is_authenticated:
        # Для залогиненных пользователей показываем их данные
        pets = Pet.objects.filter(owner=request.user)
        expenses = Expense.objects.filter(pet__owner=request.user)
    else:
        # Для анонимных пользователей показываем ВСЕ данные (временно)
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
    # Если пользователь залогинен, показываем его питомцев
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
    pet = get_object_or_404(Pet, pk=pk)
    
    # Если пользователь залогинен, проверяем владельца
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
    for item in monthly_expenses[:12]:  # Последние 12 месяцев
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
    # Если пользователь залогинен, показываем его расходы
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
                pet = Pet.objects.get(id=pet_id)
                # Проверяем владельца, если пользователь залогинен
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
    # Если пользователь залогинен, показываем его данные
    if request.user.is_authenticated:
        pets = Pet.objects.filter(owner=request.user)
        expenses = Expense.objects.filter(pet__owner=request.user)
    else:
        pets = Pet.objects.all()
        expenses = Expense.objects.all()
    
    if not expenses.exists():
        return render(request, 'pets/analytics.html', {
            'pets': pets,
            'no_data': True
        })
    
    # Определяем режим отображения
    view_mode = request.GET.get('view', 'table')
    period = request.GET.get('period', 'month')
    
    # Если запрошены графики
    if view_mode == 'charts':
        if not MATPLOTLIB_AVAILABLE:
            return render(request, 'pets/analytics.html', {
                'pets': pets,
                'no_data': False,
                'view_mode': 'charts',
                'matplotlib_error': True,
                'period': period
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
            start_date = today - timedelta(days=30)  # По умолчанию месяц
        
        # Фильтруем расходы
        filtered_expenses = expenses.filter(date__gte=start_date)
        
        # Если нет данных за период, показываем всё с предупреждением
        show_warning = False
        if not filtered_expenses.exists():
            filtered_expenses = expenses
            show_warning = True
            period = 'all'
        
        # СТАТИСТИКА для графиков
        stats = {
            'total_expenses': filtered_expenses.aggregate(Sum('amount'))['amount__sum'] or 0,
            'average_expense': filtered_expenses.aggregate(Avg('amount'))['amount__avg'] or 0,
            'expense_count': filtered_expenses.count(),
        }
        
        # ГРАФИК 1: Расходы по категориям
        chart1 = None
        try:
            category_data = filtered_expenses.values('category__name').annotate(
                total=Sum('amount')
            ).order_by('-total')
            
            if category_data:
                categories = [item['category__name'] or 'Без категории' for item in category_data]
                amounts = [float(item['total']) for item in category_data]
                
                plt.figure(figsize=(10, 6))
                colors = ['#4e79a7', '#f28e2c', '#e15759', '#76b7b2', '#59a14f', '#edc949', '#af7aa1', '#ff9da7']
                plt.bar(categories[:8], amounts[:8], color=colors[:len(categories)])
                plt.title(f'Расходы по категориям ({period})', fontsize=14, fontweight='bold')
                plt.xlabel('Категория', fontsize=12)
                plt.ylabel('Сумма (руб)', fontsize=12)
                plt.xticks(rotation=45, ha='right')
                plt.grid(axis='y', alpha=0.3)
                plt.tight_layout()
                
                buf1 = io.BytesIO()
                plt.savefig(buf1, format='png', dpi=100, bbox_inches='tight')
                buf1.seek(0)
                chart1 = base64.b64encode(buf1.getvalue()).decode('utf-8')
                buf1.close()
                plt.clf()
        except Exception as e:
            print(f"Ошибка при построении графика 1: {e}")
            chart1 = None
        
        # ГРАФИК 2: Динамика расходов по времени
        chart2 = None
        try:
            # Группируем по дням
            if period in ['week', 'month']:
                date_data = filtered_expenses.annotate(
                    day=TruncDate('date')
                ).values('day').annotate(
                    total=Sum('amount')
                ).order_by('day')
                
                if date_data:
                    dates = [item['day'].strftime('%d.%m') for item in date_data]
                    amounts = [float(item['total']) for item in date_data]
                    
                    plt.figure(figsize=(12, 5))
                    plt.plot(dates, amounts, marker='o', linewidth=2, color='#4e79a7')
                    plt.fill_between(dates, amounts, alpha=0.2, color='#4e79a7')
                    plt.title(f'Динамика расходов ({period})', fontsize=14, fontweight='bold')
                    plt.xlabel('Дата', fontsize=12)
                    plt.ylabel('Сумма (руб)', fontsize=12)
                    plt.grid(True, alpha=0.3)
                    plt.xticks(rotation=45)
                    plt.tight_layout()
                    
                    buf2 = io.BytesIO()
                    plt.savefig(buf2, format='png', dpi=100, bbox_inches='tight')
                    buf2.seek(0)
                    chart2 = base64.b64encode(buf2.getvalue()).decode('utf-8')
                    buf2.close()
                    plt.clf()
        except Exception as e:
            print(f"Ошибка при построении графика 2: {e}")
            chart2 = None
        
        # ГРАФИК 3: Распределение по питомцам
        chart3 = None
        try:
            pet_data = filtered_expenses.values('pet__name').annotate(
                total=Sum('amount')
            ).order_by('-total')
            
            if len(pet_data) > 1:  # Круговую диаграмму строим только если есть несколько питомцев
                pet_names = [item['pet__name'] or 'Без имени' for item in pet_data]
                pet_amounts = [float(item['total']) for item in pet_data]
                
                plt.figure(figsize=(8, 8))
                colors = ['#4e79a7', '#f28e2c', '#e15759', '#76b7b2', '#59a14f', '#edc949']
                plt.pie(pet_amounts, labels=pet_names, colors=colors[:len(pet_names)], 
                        autopct='%1.1f%%', startangle=90)
                plt.title(f'Распределение по питомцам ({period})', fontsize=14, fontweight='bold')
                plt.axis('equal')
                plt.tight_layout()
                
                buf3 = io.BytesIO()
                plt.savefig(buf3, format='png', dpi=100, bbox_inches='tight')
                buf3.seek(0)
                chart3 = base64.b64encode(buf3.getvalue()).decode('utf-8')
                buf3.close()
                plt.clf()
        except Exception as e:
            print(f"Ошибка при построении графика 3: {e}")
            chart3 = None
        
        context = {
            'pets': pets,
            'view_mode': view_mode,
            'period': period,
            'start_date': start_date,
            'end_date': today,
            'stats': stats,
            'chart1': chart1,
            'chart2': chart2,
            'chart3': chart3,
            'no_data': False,
            'show_warning': show_warning,
            'filtered_data_count': filtered_expenses.count(),
            'all_data_count': expenses.count(),
        }
    
    # РЕЖИМ ТАБЛИЦ (по умолчанию)
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
        }
    
    return render(request, 'pets/analytics.html', context)

def export_expenses_csv(request):
    """Экспорт расходов в CSV"""
    import csv
    from django.http import HttpResponse
    
    expenses = Expense.objects.all()
    
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