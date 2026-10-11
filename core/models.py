from django.db import models
from django.contrib.auth.models import User

class NotificationDismissal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notification_dismissals')
    notification_key = models.CharField(max_length=150, db_index=True)
    dismissed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'notification_key')
        ordering = ['-dismissed_at']

    def __str__(self):
        return f"{self.user.username} dismissed {self.notification_key}"

