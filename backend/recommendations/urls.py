from django.urls import path
from .views import recommend_track, search_tracks, submit_feedback

urlpatterns = [
    path("recommend/", recommend_track, name="recommend-track"),
    path("tracks/search/", search_tracks, name="track-search"),
    path("feedback/", submit_feedback, name="submit-feedback"),
]