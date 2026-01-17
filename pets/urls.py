from django.urls import path
from . import views
from .views import (
    PetUpdateView, 
    ExpenseUpdateView, 
    PetDeleteView, 
    ExpenseDeleteView,
    global_search,
    register_view,  
)

app_name = 'pets'

urlpatterns = [
    # Главная страница
    path('', views.home, name='home'),  
    
    # Регистрация 
    path('accounts/register/', register_view, name='register'),  # /pets/accounts/register/
    
    # Питомцы
    path('list/', views.pet_list, name='pet_list'),  # /pets/list/
    path('add/', views.pet_add, name='pet_add'),  # /pets/add/
    path('<int:pk>/', views.pet_detail, name='pet_detail'),  # /pets/3/
    path('<int:pk>/edit/', PetUpdateView.as_view(), name='pet_edit'),  # /pets/3/edit/
    path('<int:pk>/delete/', PetDeleteView.as_view(), name='pet_delete'),  # /pets/3/delete/
    
    # Расходы
    path('expenses/', views.expense_list, name='expense_list'),  # /pets/expenses/
    path('expenses/add/', views.expense_add, name='expense_add'),  # /pets/expenses/add/
    path('expenses/<int:pk>/edit/', ExpenseUpdateView.as_view(), name='expense_edit'),  # /pets/expenses/3/edit/
    path('expenses/<int:pk>/delete/', ExpenseDeleteView.as_view(), name='expense_delete'),  # /pets/expenses/3/delete/
    
    # Аналитика
    path('analytics/', views.analytics, name='analytics'),  # /pets/analytics/
    
    # Экспорт
    path('export/csv/', views.export_expenses_csv, name='export_csv'),  # /pets/export/csv/
    
    # Поиск
    path('search/', global_search, name='global_search'),  # /pets/search/
]