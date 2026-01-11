from django.urls import path
from . import views
from .views import (
    PetUpdateView, 
    ExpenseUpdateView, 
    PetDeleteView, 
    ExpenseDeleteView,
    global_search,
    login_view,
    logout_view,
    register_view,
    emergency_login
)

app_name = 'pets'

urlpatterns = [
    # Главная страница
    path('', views.home, name='home'),
    
    # Аутентификация
    path('accounts/login/', views.login_view, name='login'),
    path('accounts/logout/', views.logout_view, name='logout'),
    path('accounts/register/', views.register_view, name='register'),
    path('accounts/emergency/', views.emergency_login, name='emergency_login'),
    
    # Питомцы
    path('pets/', views.pet_list, name='pet_list'),
    path('pets/add/', views.pet_add, name='pet_add'),
    path('pets/<int:pk>/', views.pet_detail, name='pet_detail'),
    path('pets/<int:pk>/edit/', PetUpdateView.as_view(), name='pet_edit'),
    path('pets/<int:pk>/delete/', PetDeleteView.as_view(), name='pet_delete'),
    
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