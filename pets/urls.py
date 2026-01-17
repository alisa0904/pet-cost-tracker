from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .views import (
    PetUpdateView, 
    ExpenseUpdateView, 
    PetDeleteView, 
    ExpenseDeleteView,
    global_search,
    register_view,
    emergency_login,  # Добавьте этот импорт
)

app_name = 'pets'

urlpatterns = [
    # Главная страница
    path('', views.home, name='home'),  
    
    # Аутентификация
    path('accounts/login/', auth_views.LoginView.as_view(
        template_name='pets/login.html',
        redirect_authenticated_user=True
    ), name='login'),
    
    path('accounts/logout/', auth_views.LogoutView.as_view(
        next_page='pets:home'
    ), name='logout'),
    
    path('accounts/register/', register_view, name='register'),
    
    path('accounts/emergency-login/', views.emergency_login, name='emergency_login'),
    
    # Питомцы
    path('list/', views.pet_list, name='pet_list'),
    path('add/', views.pet_add, name='pet_add'),
    path('<int:pk>/', views.pet_detail, name='pet_detail'),
    path('<int:pk>/edit/', PetUpdateView.as_view(), name='pet_edit'),
    path('<int:pk>/delete/', PetDeleteView.as_view(), name='pet_delete'),
    
    # Расходы
    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/add/', views.expense_add, name='expense_add'),
    path('expenses/<int:pk>/edit/', ExpenseUpdateView.as_view(), name='expense_edit'),
    path('expenses/<int:pk>/delete/', ExpenseDeleteView.as_view(), name='expense_delete'),
    
    # Аналитика
    path('analytics/', views.analytics, name='analytics'),
    
    # Экспорт
    path('export/csv/', views.export_expenses_csv, name='export_csv'),
    
    # Поиск
    path('search/', global_search, name='global_search'),
]