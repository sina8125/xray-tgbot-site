from django.urls import path
from . import views

urlpatterns = [
    path('webhook/', views.StartBot.as_view()),
    path('config/', views.GetConfigView.as_view()),
]