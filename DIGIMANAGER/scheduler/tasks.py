from celery import shared_task
from django.utils import timezone
from .models import Post

@shared_task
def auto_publish_scheduled_posts():
    now = timezone.now()
    scheduled_posts = Post.objects.filter(status='scheduled', scheduled_time__lte=now)

    for post in scheduled_posts:
        post.status = 'published'
        post.save()
