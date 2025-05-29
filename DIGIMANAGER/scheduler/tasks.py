from celery import shared_task
from .models import Post

@shared_task
def publish_post(post_id):
    try:
        post = Post.objects.get(id=post_id)
        post.status = 'published'
        post.save()
    except Post.DoesNotExist:
        pass