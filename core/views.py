from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.http import HttpResponse, JsonResponse
from django.conf import settings
import json
from .services import get_dashboard_metrics

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'core/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        metrics = get_dashboard_metrics(self.request.user)
        context.update(metrics)
        # JSON serialize charts for Chart.js in template
        context['charts_json'] = json.dumps(metrics['charts'])
        return context


def manifest_view(request):
    manifest_path = settings.BASE_DIR / 'static' / 'manifest.json'
    if manifest_path.exists():
        with open(manifest_path, 'r') as f:
            data = json.load(f)
        return JsonResponse(data, content_type='application/manifest+json')
    return JsonResponse({}, status=404)


def service_worker_view(request):
    sw_path = settings.BASE_DIR / 'static' / 'sw.js'
    if sw_path.exists():
        with open(sw_path, 'r') as f:
            content = f.read()
        return HttpResponse(content, content_type='application/javascript')
    return HttpResponse("// sw not found", content_type='application/javascript', status=404)


from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.shortcuts import redirect
from .models import NotificationDismissal
from .context_processors import global_finance_context

@login_required
def read_and_redirect_notification(request, key):
    """
    Marks notification as read/dismissed and redirects to designated page.
    """
    NotificationDismissal.objects.get_or_create(user=request.user, notification_key=key)
    next_url = request.GET.get('next') or request.POST.get('next')
    if next_url and next_url.startswith('/'):
        return redirect(next_url)
    return redirect('core:dashboard')


@login_required
@require_http_methods(["POST", "GET"])
def clear_notification(request, key):
    """
    Clears / dismisses an individual notification.
    """
    NotificationDismissal.objects.get_or_create(user=request.user, notification_key=key)
    if request.headers.get('HX-Request') or request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({"status": "cleared", "key": key})
    
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('core:dashboard')


@login_required
@require_http_methods(["POST"])
def clear_all_notifications(request):
    """
    Clears / dismisses all currently active notifications for the user.
    """
    ctx = global_finance_context(request)
    for n in ctx.get('notifications', []):
        NotificationDismissal.objects.get_or_create(
            user=request.user,
            notification_key=n['key']
        )

    if request.headers.get('HX-Request') or request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({"status": "all_cleared"})

    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('core:dashboard')

