from celery import shared_task
from .models import Post

@shared_task
def publish_scheduled_post(post_id):
    from .models import Post
    post = Post.objects.filter(id=post_id).first()
    if not post or post.status != 'scheduled':
        return f"[Stub] No action needed"
    print(f"[Stub] Posting to {post.platform.name} - ID {post.id}")
    post.status = 'published'
    post.save()
    return f"[Stub] Published post {post.id}"
