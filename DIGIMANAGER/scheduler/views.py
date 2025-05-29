from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import RegisterForm
from django.contrib.auth import login as auth_login, authenticate, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse

# Create your views here.
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
                return redirect('admin_dashboard')
            elif user.role == 'creator':
                return redirect('creator_dashboard')
            elif user.role == 'manager':
                return redirect('manager_dashboard')
            else:
                return redirect('dashboard')
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
                return redirect('admin_dashboard')
            elif user.role == 'creator':
                return redirect('creator_dashboard')
            elif user.role == 'manager':
                return redirect('manager_dashboard')
            else:
                return redirect('dashboard')  # fallback

    else:
        form = AuthenticationForm()
    return render(request, 'users/login.html', {'form': form})

def logout(request):
    auth_logout(request)
    messages.info(request, "You have successfully logged out.")
    return redirect('login')

@login_required
def admDashboard(request):
    return HttpResponse("Admin Dashboard")

@login_required
def creatorDashboard(request):
    return HttpResponse("Creator Dashboard")

@login_required
def managerDashboard(request):
    return HttpResponse("Manager Dashboard")

@login_required
def genericDashboard(request):
    return HttpResponse("Generic Dashboard")