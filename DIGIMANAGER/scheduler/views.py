from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import RegisterForm
from django.contrib.auth import login as auth_login, authenticate, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from .forms import PostForm
from .models import Content, ContentPrompt, Post, Platform
from datetime import datetime
from .tasks import publishPost
import requests
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Count
from .forms import ContentPromptForm, PlatformForm
from .aiUtils import generateCaptionAi
import os
from django.http import JsonResponse
from django.core.files.base import ContentFile
from django.conf import settings
from django.utils.crypto import get_random_string
from PIL import Image
from io import BytesIO

@csrf_exempt
def generateImage(request):
    if request.method == 'POST':
        caption = request.POST.get('caption')
        model = request.POST.get('model', 'dalle')

        # 1. Generate image URL using mock or actual API
        if model == 'deepai':
            api_url = 'https://api.deepai.org/api/text2img'
            response = requests.post(
                api_url,
                data={'text': caption},
                headers={'api-key': 'f9acbf17-62ad-4229-bd8c-f85b044019fa'}
            )
            image_url = response.json()
        elif model == 'stablediffusion':
            # Replace with real API URL
            image_url = "https://via.placeholder.com/500x300.png?text=Stable+Diffusion+Image"
        else:
            # Mock DALL·E (or integrate real OpenAI API)
            image_url = "https://via.placeholder.com/500x300.png?text=DALL·E+Image"

        # 2. Download and save image locally to MEDIA_ROOT
        try:
            img_response = requests.get(image_url)
            if img_response.status_code == 200:
                filename = f"ai_generated/{get_random_string(12)}.jpg"
                path = os.path.join(settings.MEDIA_ROOT, filename)
                os.makedirs(os.path.dirname(path), exist_ok=True)

                with open(path, 'wb') as f:
                    f.write(img_response.content)

                return JsonResponse({'image_url': settings.MEDIA_URL + filename})
        except Exception as e:
            return JsonResponse({'error': str(e)})

    return JsonResponse({'error': 'Invalid request'}, status=400)

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

            # Redirect based on user role
            if user.role == 'admin':
                return redirect('dashboards/admDashboard')
            elif user.role == 'creator':
                return redirect('dashboards/creatorDashboard')
            elif user.role == 'manager':
                return redirect('dashboards/managerDashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'users/login.html', {'form': form})

def logout(request):
    auth_logout(request)
    messages.info(request, "Log out successful.")
    return redirect('login')


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


@login_required
def createPost(request):
    if request.user.role != 'creator':
        return redirect('unauthorized')

    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.user = request.user

            if 'generate_ai' in request.POST:
                post.content = generate_ai_content()
                return render(request, 'posts/createPost.html', {'form': form})

            post.save()
            if post.status == 'scheduled':
                from django.utils import timezone
                from datetime import timedelta
                eta = (post.scheduled_time - timezone.now()).total_seconds()
                publishPost.apply_async((post.id,), countdown=eta)
            return redirect('creatorDashboard')
    else:
        form = PostForm()
    return render(request, 'posts/createPost.html', {'form': form})

@login_required
def approvePosts(request):
    if request.user.role != 'manager':
        return redirect('unauthorized')

    posts = Post.objects.filter(status='draft')
    return render(request, 'posts/approvePosts.html', {'posts': posts})

@login_required
def approvePostAction(request, post_id):
    post = Post.objects.get(id=post_id)
    post.status = 'approved'
    post.save()
    return redirect('approvePosts')

############
#DASHBOARDS#
############

@login_required
def analyticsDashboard(request):
    if request.user.role not in ['admin', 'manager']:
        return redirect('unauthorized')

    # Current status breakdown for pie/bar chart
    status_counts = Post.objects.values('status').annotate(count=Count('status'))
    status_data = {item['status']: item['count'] for item in status_counts}

    # Example monthly post count over last 6 months for trend analysis
    from django.utils.timezone import now
    import calendar
    from datetime import timedelta

    months = []
    post_counts = []

    for i in range(5, -1, -1):  # Last 6 months
        month = (now() - timedelta(days=30 * i)).month
        year = (now() - timedelta(days=30 * i)).year
        month_name = calendar.month_name[month]

        count = Post.objects.filter(
            created_at__month=month,
            created_at__year=year
        ).count()

        months.append(month_name)
        post_counts.append(count)

    return render(request, 'dashboards/analytics.html', {
        'status_labels': list(status_data.keys()),
        'status_values': list(status_data.values()),
        'month_labels': months,
        'month_data': post_counts
    })

User = get_user_model()

# Admin Dashboard View
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

# Manager Dashboard View
@login_required
def managerDashboard(request):
    if request.user.role != 'manager':
        return redirect('unauthorized')
    
    scheduled_posts = Post.objects.filter(status='scheduled', scheduled_time__lte=timezone.now())
    
    return render(request, 'dashboards/managerDashboard.html', {
        'scheduled_posts': scheduled_posts,
    })

# Creator Dashboard View
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

# Unauthorized View
def unauthorized(request):
    return render(request, 'dashboards/unauthorized.html')

@login_required
def createPost(request):
    if request.user.role != 'creator':
        return redirect('unauthorized')

    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.user = request.user
            # Set post status from form or default to draft
            post.status = request.POST.get('status', 'draft')
            post.save()

            # Handle scheduled post
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
    posts = Post.objects.filter(user=request.user)  # Filter by current user
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
            return redirect('myPosts')
    else:
        form = PostForm(instance=post)

    return render(request, 'posts/createPost.html', {'form': form})


@login_required
def deletePost(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.user == post.user:
        post.delete()
    return redirect('myPosts')


@login_required
def approvePosts(request):
    if request.user.role not in ['admin', 'manager']:
        return redirect('unauthorized')

    pending_posts = Post.objects.filter(status='scheduled')
    return render(request, 'posts/approvePosts.html', {'pending_posts': pending_posts})


@login_required
def rejectPostAction(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    post.status = 'rejected'
    post.save()
    return redirect('approvePosts')

@login_required
def managePlatforms(request):
    if not hasattr(request.user, 'role') or request.user.role not in ['admin', 'manager']:
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

@login_required
def drafts(request):
    user_drafts = Post.objects.filter(user=request.user, status='draft').order_by('-created_at')
    return render(request, 'scheduler/drafts.html', {'drafts': user_drafts})