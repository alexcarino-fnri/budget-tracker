from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('manifest.json', views.manifest_view, name='manifest'),
    path('sw.js', views.service_worker_view, name='service_worker'),
    path('notifications/read-and-redirect/<str:key>/', views.read_and_redirect_notification, name='read_and_redirect_notification'),
    path('notifications/clear/<str:key>/', views.clear_notification, name='clear_notification'),
    path('notifications/clear-all/', views.clear_all_notifications, name='clear_all_notifications'),
]
