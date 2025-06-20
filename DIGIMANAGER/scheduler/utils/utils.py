import shutil, os
from django.conf import settings

def cleanup_temp_images():
    temp_dir = os.path.join(settings.MEDIA_ROOT, "ai_temp")
    if os.path.isdir(temp_dir):
        shutil.rmtree(temp_dir)
        os.makedirs(temp_dir, exist_ok=True)
