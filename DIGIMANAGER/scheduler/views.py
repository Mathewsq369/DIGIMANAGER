import base64
import os
import calendar
from io import BytesIO
from datetime import timedelta

import torch
from diffusers import StableDiffusionPipeline
import uuid

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login as auth_login, authenticate, logout as auth_logout, get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from django.core.files.base import ContentFile
from django.conf import settings
from django.utils.crypto import get_random_string
from django.db.models import Count
from PIL import Image, ImageDraw

from .forms import RegisterForm, PostForm, ContentPromptForm, PlatformForm
from .models import Content, ContentPrompt, Post, Platform
from .tasks import auto_publish_scheduled_posts
from .aiUtils import generateCaptionAi
from .utils.aiGeneration import generate_dalle_image, refine_image_gpt4, generate_image_sd
from django.views.decorators.http import require_POST
from django.core.files import File
import logging

from urllib.request import urlretrieve
from urllib.parse import urlparse

#######################
# AI IMAGE GENERATION #
#######################

@require_POST
@csrf_exempt
def generate_ai_image(request, post_id=None):
    caption = request.POST.get("caption")
    model = request.POST.get("model", "dalle")

    if not caption or not model:
        return JsonResponse({"error": "Missing caption or model."}, status=400)

    try:
        # Simulate or generate image
        if model == "stablediffusion":
            try:
                # Placeholder logic for actual Stable Diffusion model
                image = Image.new('RGB', (600, 400), color='lightblue')
                draw = ImageDraw.Draw(image)
                draw.text((10, 180), f"SD: {caption}", fill='black')
            except Exception:
                return JsonResponse({"image_url": "https://dummyimage.com/600x400/cccccc/000000&text=AI+Unavailable"})
        else:
            # Default model (e.g. DALL·E simulation)
            image = Image.new('RGB', (600, 400), color='lightgray')
            draw = ImageDraw.Draw(image)
            draw.text((10, 180), f"{model.upper()}: {caption}", fill='black')

        # Save generated image to buffer
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)

        filename = f"{uuid.uuid4()}.png"
        relative_path = f"ai_temp/{filename}"
        absolute_path = os.path.join(settings.MEDIA_ROOT, relative_path)
        os.makedirs(os.path.dirname(absolute_path), exist_ok=True)

        # Write image to disk
        with open(absolute_path, "wb") as f:
            f.write(buffer.getvalue())

        image_url = settings.MEDIA_URL + relative_path

        # If post ID is provided, save image to the post
        if post_id:
            try:
                post = Post.objects.get(id=post_id)
                # Move image to permanent location
                final_rel_path = f"posts/{filename}"
                final_abs_path = os.path.join(settings.MEDIA_ROOT, final_rel_path)
                os.makedirs(os.path.dirname(final_abs_path), exist_ok=True)
                os.rename(absolute_path, final_abs_path)

                post.image.name = final_rel_path  # store relative path
                post.save()

                image_url = settings.MEDIA_URL + final_rel_path
            except Post.DoesNotExist:
                return JsonResponse({"error": "Post not found."}, status=404)

        return JsonResponse({"image_url": image_url})

    except Exception as e:
        return JsonResponse({"error": "Unexpected server error.", "details": str(e)}, status=500)


@login_required
def refine_ai_image(request):
    if request.method == 'POST':
        raw_prompt = request.POST.get('prompt')
        refined_prompt = ai_prompt_enhancer(raw_prompt)  # Optional NLP enhancer
        refined_image = generate_image_from_prompt(refined_prompt)
        return render(request, 'ai/refine_result.html', {'image': refined_image, 'prompt': refined_prompt})
    return render(request, 'ai/refine.html')


def generate_image_sd(prompt):
    model_id = "stabilityai/stable-diffusion-2-1"
    device = "cuda" if torch.cuda.is_available() else "cpu"
    pipe = StableDiffusionPipeline.from_pretrained(
        model_id,
        torch_dtype=torch.float16,
        cache_dir=settings.HUGGINGFACE_CACHE_DIR
    ).to(device)

    result = pipe(prompt, num_inference_steps=50).images[0]

    filename = f"{uuid.uuid4()}.png"
    image_path = os.path.join(settings.MEDIA_ROOT, "generated", filename)
    os.makedirs(os.path.dirname(image_path), exist_ok=True)
    result.save(image_path)

    return image_path  # Returns absolute path; convert to URL in view


##########
# AUTH   #
##########

def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            messages.success(request, f"Account created for {user.username}!")
            return redirect('login')
    else:
        form = RegisterForm()
    return render(request, 'users/register.html', {'form': form})

def login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            messages.success(request, f"Welcome {user.username}!")

            if user.role == 'admin':
                return redirect('admDashboard')
            elif user.role == 'creator':
                return redirect('creatorDashboard')
            elif user.role == 'manager':
                return redirect('managerDashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'users/login.html', {'form': form})

def logout(request):
    auth_logout(request)
    messages.info(request, "Log out successful.")
    return redirect('login')


####################
# CAPTION GENERATOR#
####################

@login_required
def generateCaption(request):
    caption = None
    if request.method == 'POST':
        form = ContentPromptForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            obj.generated_caption = generateCaptionAi(obj.prompt, obj.tone)
            obj.status = 'draft'
            obj.save()
            caption = obj
            messages.success(request, "Caption generated and saved as draft.")
    else:
        form = ContentPromptForm()
    return render(request, 'scheduler/generateCaption.html', {'form': form, 'caption': caption})

@login_required
def captionHistory(request):
    captions = ContentPrompt.objects.filter(user=request.user).order_by('-timestamp')
    return render(request, 'scheduler/captionHistory.html', {'captions': captions})


###############
# POSTS       #
###############

@login_required
def createPost(request):
    if request.user.role != 'creator':
        return redirect('unauthorized')

    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)

        # Hidden input used to pass the AI-generated image URL from the frontend
        ai_image_url = request.POST.get('ai_image_url')

        if form.is_valid():
            post = form.save(commit=False)
            post.user = request.user
            post.status = request.POST.get('status', 'draft')

            # No manual image uploaded, but an AI-generated one exists
            if not request.FILES.get('image') and ai_image_url:
                try:
                    parsed_url = urlparse(ai_image_url)
                    filename = os.path.basename(parsed_url.path)
                    temp_path = os.path.join(settings.MEDIA_ROOT, 'ai_temp', filename)

                    if os.path.exists(temp_path):
                        final_path = os.path.join(settings.MEDIA_ROOT, 'posts', filename)
                        os.makedirs(os.path.dirname(final_path), exist_ok=True)
                        os.rename(temp_path, final_path)

                        post.image.name = f'posts/{filename}'
                    else:
                        messages.warning(request, "AI-generated image not found in temp storage.")
                except Exception as e:
                    messages.error(request, f"Error processing AI image: {str(e)}")

            post.save()

            # Handle scheduled posts
            if post.status == 'scheduled' and post.scheduled_time:
                eta = (post.scheduled_time - timezone.now()).total_seconds()
                publishPost.apply_async((post.id,), countdown=eta)

            messages.success(request, "Post saved successfully.")
            return redirect('creatorDashboard')
        else:
            messages.error(request, "Please correct the form errors.")
    else:
        form = PostForm()

    return render(request, 'posts/createPost.html', {'form': form})

@login_required
def myPosts(request):
    posts = Post.objects.filter(user=request.user)
    return render(request, 'posts/postList.html', {'posts': posts})

@login_required
def viewPost(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.user != post.user and request.user.role not in ['admin', 'manager']:
        return redirect('unauthorized')
    return render(request, 'posts/postDetail.html', {'post': post})

@login_required
def editPost(request, post_id):
    post = get_object_or_404(Post, pk=post_id)

    if request.user.id != post.user_id:
        return redirect('unauthorized')  # You can customize this

    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            updated_post = form.save(commit=False)

            # Optional: Handle AI-generated image URL from hidden input
            ai_image_url = request.POST.get('ai_image_url')
            if ai_image_url:
                updated_post.image = ai_image_url  # This works if image is a URL field or handle as needed

            updated_post.save()
            return redirect('viewPost', post_id=updated_post.pk)
    else:
        form = PostForm(instance=post)

    context = {
        'form': form,
        'post': post,
    }
    return render(request, 'posts/createPost.html', context)

@login_required
def deletePost(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.user == post.user:
        post.delete()
        messages.success(request, "Post deleted.")
    return redirect('myPosts')


####################
# POST APPROVAL    #
####################

@login_required
def approvePosts(request):
    if request.user.role not in ['admin', 'manager']:
        return redirect('unauthorized')
    pending_posts = Post.objects.filter(status='scheduled')
    return render(request, 'posts/approvePosts.html', {'pending_posts': pending_posts})

@login_required
def approvePostAction(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    post.status = 'approved'
    post.save()
    return redirect('approvePosts')

@login_required
def rejectPostAction(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    post.status = 'rejected'
    post.save()
    return redirect('approvePosts')


#################
# PLATFORMS     #
#################

@login_required
def managePlatforms(request):
    if request.user.role not in ['admin', 'manager']:
        return redirect('unauthorized')

    platforms = Platform.objects.filter(added_by=request.user).order_by('-created_at')
    form = PlatformForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        platform = form.save(commit=False)
        platform.added_by = request.user
        platform.save()
        messages.success(request, f"{platform.name.title()} added successfully.")
        return redirect('managePlatforms')

    return render(request, 'platforms/managePlatforms.html', {
        'form': form,
        'platforms': platforms,
    })

@login_required
def editPlatform(request, pk):
    platform = get_object_or_404(Platform, pk=pk, added_by=request.user)
    if request.user.role not in ['admin', 'manager']:
        return redirect('unauthorized')

    form = PlatformForm(request.POST or None, instance=platform)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Platform updated successfully.")
        return redirect('managePlatforms')

    return render(request, 'platforms/editPlatform.html', {'form': form, 'platform': platform})

@login_required
def deletePlatform(request, pk):
    platform = get_object_or_404(Platform, pk=pk, added_by=request.user)
    if request.user.role not in ['admin', 'manager']:
        return redirect('unauthorized')

    if request.method == 'POST':
        platform.delete()
        messages.success(request, "Platform deleted successfully.")
        return redirect('managePlatforms')

    return render(request, 'platforms/deletePlatform.html', {'platform': platform})


##################
# DASHBOARDS     #
##################

User = get_user_model()

@login_required
def admDashboard(request):
    if request.user.role != 'admin':
        return redirect('unauthorized')
    users = User.objects.all()
    posts = Post.objects.all()
    return render(request, 'dashboards/admDashboard.html', {
        'users': users,
        'posts': posts,
    })

@login_required
def managerDashboard(request):
    if request.user.role != 'manager':
        return redirect('unauthorized')
    scheduled_posts = Post.objects.filter(status='scheduled', scheduled_time__lte=timezone.now())
    return render(request, 'dashboards/managerDashboard.html', {
        'scheduled_posts': scheduled_posts,
    })

@login_required
def creatorDashboard(request):
    if request.user.role != 'creator':
        return redirect('unauthorized')
    my_posts = Post.objects.filter(user=request.user)
    platforms = Platform.objects.all()
    return render(request, 'dashboards/creatorDashboard.html', {
        'posts': my_posts,
        'platforms': platforms,
    })

def unauthorized(request):
    return render(request, 'dashboards/unauthorized.html')


##################
# DRAFTS VIEW    #
##################

@login_required
def drafts(request):
    user_drafts = Post.objects.filter(user=request.user, status='draft').order_by('-created_at')
    return render(request, 'scheduler/drafts.html', {'drafts': user_drafts})


##################
# ANALYTICS      #
##################

@login_required
def analyticsDashboard(request):
    if request.user.role not in ['admin', 'manager']:
        return redirect('unauthorized')

    status_counts = Post.objects.values('status').annotate(count=Count('status'))
    status_data = {item['status']: item['count'] for item in status_counts}

    months = []
    post_counts = []

    for i in range(5, -1, -1):
        dt = timezone.now() - timedelta(days=30 * i)
        month_name = calendar.month_name[dt.month]
        count = Post.objects.filter(
            created_at__month=dt.month,
            created_at__year=dt.year
        ).count()
        months.append(month_name)
        post_counts.append(count)

    return render(request, 'dashboards/analytics.html', {
        'status_labels': list(status_data.keys()),
        'status_values': list(status_data.values()),
        'month_labels': months,
        'month_data': post_counts
    })