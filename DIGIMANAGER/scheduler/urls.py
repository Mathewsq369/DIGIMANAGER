# project/urls.py

from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('', views.login, name='login'),
    path('logout/', views.logout, name='logout'),

    # AI Image
    path('ai/generate/<int:post_id>/', views.generate_ai_image, name='generate_ai_image'),
    path('ai/refine/<int:post_id>/', views.refine_ai_image, name='refine_ai_image'),
    path('ai/sd/<int:post_id>/', views.generate_image_sd, name='generate_sd_image'),

    # Caption
    path('caption/generate/', views.generateCaption, name='generateCaption'),
    path('caption/history/', views.captionHistory, name='captionHistory'),

    # Posts & drafts
    path('posts/create/', views.createPost, name='createPost'),
    path('posts/', views.myPosts, name='myPosts'),
    path('posts/drafts/', views.drafts, name='drafts'),
    path('posts/<int:post_id>/', views.viewPost, name='viewPost'),
    path('posts/<int:post_id>/edit/', views.editPost, name='editPost'),
    path('posts/<int:post_id>/delete/', views.deletePost, name='deletePost'),

    # Approvals
    path('posts/approve/', views.approvePosts, name='approvePosts'),
    path('posts/approve/<int:post_id>/', views.approvePostAction, name='approvePostAction'),
    path('posts/reject/<int:post_id>/', views.rejectPostAction, name='rejectPostAction'),

    # Platforms
    path('platforms/manage/', views.managePlatforms, name='managePlatforms'),
    path('platforms/<int:pk>/edit/', views.editPlatform, name='editPlatform'),
    path('platforms/<int:pk>/delete/', views.deletePlatform, name='deletePlatform'),

    # Dashboards
    path('creator-dashboard/', views.creatorDashboard, name='creatorDashboard'),
    path('admin-dashboard/', views.admDashboard, name='admDashboard'),
    path('manager-dashboard/', views.managerDashboard, name='managerDashboard'),
    path('analytics/', views.analyticsDashboard, name='analyticsDashboard'),
    path('unauthorized/', views.unauthorized, name='unauthorized'),
]