from django.urls import path
from . import views

urlpatterns = [
    path('', views.login, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout, name='logout'),

    #dashboards
    path('dashboards/admDashboard', views.admDashboard, name='admin_dashboard'),
    path('dashboards/creatorDashboard', views.creatorDashboard, name='creator_dashboard'),
    path('dashboards/managerDashboard', views.managerDashboard, name='manager_dashboard'),
    #path('dashboard/', views.genericDashboard, name='dashboard'),

    #########
    path('create/', views.createPost, name='create_post'),
    path('approve/', views.approvePosts, name='approve_posts'),
    path('approve/<int:post_id>/', views.approvePostAction, name='approve_post'),
    path('analytics/', views.analyticsDashboard, name='analytics_dashboard'),
]


##############################
from django.urls import path
from . import views

urlpatterns = [
    path('admin/dashboard/', views.admDashboard, name='admDashboard'),
    path('manager/dashboard/', views.managerDashboard, name='managerDashboard'),
    path('creator/dashboard/', views.creatorDashboard, name='creatorDashboard'),
    path('unauthorized/', views.unauthorized, name='unauthorized'),

    # Content Management
    path('create/', views.createPost, name='createPost'),
    path('my-posts/', views.myPosts, name='myPosts'),
    path('post/<int:post_id>/', views.viewPost, name='view_post'),
    path('post/<int:post_id>/edit/', views.editPost, name='edit_post'),
    path('post/<int:post_id>/delete/', views.deletePost, name='delete_post'),

    # Approvals
    path('approve-posts/', views.approvePosts, name='approvePosts'),
    path('approve-post/<int:post_id>/', views.approvePostAction, name='approve_post'),
    path('reject-post/<int:post_id>/', views.rejectPostAction, name='reject_post'),

    # Analytics
    path('analytics/', views.analyticsDashboard, name='analyticsDashboard'),
]