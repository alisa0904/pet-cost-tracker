from django.urls import path
from . import views

app_name = 'pets'

urlpatterns = [
    path('', views.pet_list, name='pet_list'),
    path('pet/<int:pet_id>/', views.pet_detail, name='pet_detail'),
]