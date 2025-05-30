from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import RegisterForm
from django.contrib.auth import login as auth_login, authenticate, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from .forms import PostForm
from .models import Post
from datetime import datetime
from .tasks import publish_post
import requests
from django.contrib.auth import get_user_model
from .models import Post, Platform
from django.utils import timezone


def home_redirect(request):
    return redirect('register')

def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            messages.success(request, f"Account created for {user.username}!")
            # Optional: redirect by role
            if user.role == 'admin':
                return redirect('dashboards/admDashboard')
            elif user.role == 'creator':
                return redirect('dashboards/creatorDashboard')
            elif user.role == 'manager':
                return redirect('dashboards/managerDashboard')
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

def generate_ai_content(prompt="Generate a social media caption."):
    API_URL = "https://api-inference.huggingface.co/models/gpt2"
    headers = {"Authorization": "Bearer YOUR_HUGGINGFACE_TOKEN"} #comechange this
    payload = {"inputs": prompt}
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        return response.json()[0]['generated_text']
    except Exception:
        return "Could not generate AI content."

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
                publish_post.apply_async((post.id,), countdown=eta)
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


@login_required
def analyticsDashboard(request):
    if request.user.role not in ['admin', 'manager']:
        return redirect('unauthorized')

    data = {
        'draft': Post.objects.filter(status='draft').count(),
        'scheduled': Post.objects.filter(status='scheduled').count(),
        'approved': Post.objects.filter(status='approved').count(),
        'published': Post.objects.filter(status='published').count(),
    }
    return render(request, 'dashboard/analytics.html', {'data': data})


############
#DASHBOARDS#
############

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