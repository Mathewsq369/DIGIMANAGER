from django.urls import path
from . import views

urlpatterns = [
    path('', views.login, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout, name='logout'),

    #dashboards
    path('admin/dashboard/', views.admDashboard, name='admin_dashboard'),
    path('creator/dashboard/', views.creatorDashboard, name='creator_dashboard'),
    path('manager/dashboard/', views.managerDashboard, name='manager_dashboard'),
    path('dashboard/', views.genericDashboard, name='dashboard'),

    #########
    path('create/', views.createPost, name='create_post'),
    path('approve/', views.approvePosts, name='approve_posts'),
    path('approve/<int:post_id>/', views.approvePostAction, name='approve_post'),
    path('analytics/', views.analyticsDashboard, name='analytics_dashboard'),
]
