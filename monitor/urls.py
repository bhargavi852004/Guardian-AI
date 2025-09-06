from django.urls import path
from . import views
from .views import home_redirect

urlpatterns = [
    path('', home_redirect, name='home'),
    path('register/', views.register_user, name='register'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('select_child/', views.select_child, name='select_child'),
    path('set_child/', views.set_child, name='set_child'),
    path('switch_child/', views.switch_child, name='switch_child'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('alerts/', views.view_alerts, name='view_alerts'),
    path('api/log_browsing_data/', views.log_browsing_data, name='log_browsing_data'),
    path('api/validate_child_email/', views.validate_child_email, name='validate_child_email'),
]
