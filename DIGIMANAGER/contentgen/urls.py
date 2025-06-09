from django.urls import path
from . import views

urlpatterns = [
    path('generate/', views.generate_caption, name='generateCaption'),
    path('caption/<int:pk>/', views.caption_detail, name='captionDetail'),
]