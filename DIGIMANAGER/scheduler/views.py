import base64
import os
import calendar
from io import BytesIO
from datetime import timedelta

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
from PIL import Image

from .forms import RegisterForm, PostForm, ContentPromptForm, PlatformForm
from .models import Content, ContentPrompt, Post, Platform
from .tasks import publishPost
from .aiUtils import generateCaptionAi
from .utils.aiGeneration import generate_image_gpt4, refine_image_gpt4, generate_image_sd


#######################
# AI IMAGE GENERATION #
#######################

@login_required
def generate_ai_image(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    prompt = request.GET.get("prompt", "A futuristic sunset")
    image_url = generate_image_gpt4(post, prompt)
    return JsonResponse({"status": "success", "image_url": image_url})

@login_required
def refine_ai_image(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    prompt = request.GET.get("prompt", "Make it look more realistic")
    image_call_id = request.GET.get("image_call_id")
    image_url = refine_image_gpt4(post, image_call_id, prompt)
    return JsonResponse({"status": "success", "image_url": image_url})

@login_required
def generate_sd_image(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    prompt = request.GET.get("prompt", "A robot in a forest")
    image_url = generate_image_sd(post, prompt)
    return JsonResponse({"status": "success", "image_url": image_url})


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
        if form.is_valid():
            post = form.save(commit=False)
            post.user = request.user
            post.status = request.POST.get('status', 'draft')
            post.save()

            if post.status == 'scheduled' and post.scheduled_time:
                eta = (post.scheduled_time - timezone.now()).total_seconds()
                publishPost.apply_async((post.id,), countdown=eta)

            messages.success(request, "Post saved successfully.")
            return redirect('creatorDashboard')
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
    post = get_object_or_404(Post, id=post_id)
    if request.user != post.user:
        return redirect('unauthorized')

    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, "Post updated successfully.")
            return redirect('myPosts')
    else:
        form = PostForm(instance=post)

    return render(request, 'posts/createPost.html', {'form': form})

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
        'my_posts': my_posts,
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