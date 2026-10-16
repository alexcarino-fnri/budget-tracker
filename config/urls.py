"""
URL configuration for Budget Tracker project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('accounts/', include('accounts.urls')),
    path('wallets/', include('wallets.urls')),
    path('transactions/', include('transactions.urls')),
    path('budgets/', include('budgets.urls')),
    path('debts/', include('debts.urls')),
    path('reports/', include('reports.urls')),
]

from django.urls import re_path
from django.views.static import serve

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
else:
    # In production without an external reverse proxy (e.g. Render Web Services),
    # allow Django to serve media uploads (receipts, avatars, etc.)
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]
