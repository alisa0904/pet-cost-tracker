from django.urls import path
from . import views

app_name = 'pets'

urlpatterns = [
    path('', views.home, name='home'),
    path('pets/', views.pet_list, name='pet_list'),
    path('pets/<int:pk>/', views.pet_detail, name='pet_detail'),
    path('pets/add/', views.pet_add, name='pet_add'),
    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/add/', views.expense_add, name='expense_add'),
    path('analytics/', views.analytics, name='analytics'),
    path('export/csv/', views.export_expenses_csv, name='export_expenses_csv'),
]