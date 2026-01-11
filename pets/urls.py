from django.urls import path
from . import views
from .views import (
    PetUpdateView, 
    ExpenseUpdateView, 
    PetDeleteView, 
    ExpenseDeleteView,
    global_search
)

app_name = 'pets'

urlpatterns = [
    # Главная страница (доступна по /pets/)
    path('', views.home, name='home'),
    
    # Питомцы (без префикса 'pets/' так как он уже в главном urls.py)
    path('', views.pet_list, name='pet_list'),  # Должно быть path('', ...) а не path('pets/', ...)
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