from django.urls import path
from . import views

urlpatterns = [
    path('', views.login, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout, name='logout'),

    #dashboards
    path('dashboards/admDashboard', views.admDashboard, name='admDashboard'),
    path('dashboards/creatorDashboard', views.creatorDashboard, name='creatorDashboard'),
    path('dashboards/managerDashboard', views.managerDashboard, name='managerDashboard'),
    #path('dashboard/', views.genericDashboard, name='dashboard'),
    #path('unauthorized/', views.unauthorized, name='unauthorized'),

    # Content Management
    path('create/', views.createPost, name='createPost'),
    path('my-posts/', views.myPosts, name='myPosts'),
    path('post/<int:post_id>/', views.viewPost, name='viewPost'),
    path('post/<int:post_id>/edit/', views.editPost, name='editPost'),
    path('post/<int:post_id>/delete/', views.deletePost, name='deletePost'),

    # Approvals
    path('approve-posts/', views.approvePosts, name='approvePosts'),
    path('approve-post/<int:post_id>/', views.approvePostAction, name='approvePost'),
    path('reject-post/<int:post_id>/', views.rejectPostAction, name='rejectPost'),

    # Analytics
    path('analytics/', views.analyticsDashboard, name='analyticsDashboard'),

    #platforms
    path('platforms/', views.managePlatforms, name='managePlatforms'),
    path('manage-platforms/', views.managePlatforms, name='managePlatforms'),
    path('platform/edit/<int:pk>/', views.editPlatform, name='editPlatform'),
    path('platform/delete/<int:pk>/', views.deletePlatform, name='deletePlatform'),
    
    #Captions
    path('generate/', views.generateCaption, name='generateCaption'),
    path('captions/history/', views.captionHistory, name='captionHistory'),
    path('drafts/', views.drafts, name='drafts'),
]