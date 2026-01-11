# petcosttracker/urls.py - ИЗМЕНИТЬ ТАК
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.views.generic.base import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Перенаправление с корня на главную страницу pets
    path('', RedirectView.as_view(pattern_name='pets:home', permanent=False)),
    
    # Все маршруты pets доступны от корня
    path('', include('pets.urls')),  # <-- БЕЗ префикса 'pets/'
    
    # Аутентификация
    path('accounts/login/', auth_views.LoginView.as_view(
        template_name='registration/login.html'
    ), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(
        next_page='pets:home'
    ), name='logout'),
]