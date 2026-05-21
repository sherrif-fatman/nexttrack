from django.urls import path
from .views import recommend_track

urlpatterns = [
    path("recommend/", recommend_track, name="recommend-track"),
]