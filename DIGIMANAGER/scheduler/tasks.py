from celery import shared_task
from .models import Post
from django.core.mail import send_mail


@shared_task
def publish_scheduled_post(post_id):
    from .models import Post
    post = Post.objects.filter(id=post_id).first()
    if not post or post.status != 'scheduled':
        return f"[Stub] No action needed"
    print(f"[Stub] Posting to {post.platform.name} - ID {post.id}")
    post.status = 'published'
    post.save()
    # In Celery task `publish_scheduled_post`:
    send_notification(post.user, 'Post Published', f'Your post "{post.content[:50]}" has just been published.')

    return f"[Stub] Published post {post.id}"
