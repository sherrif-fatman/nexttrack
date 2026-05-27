from django.contrib import admin

from django.contrib import admin

from .models import (
    Artist,
    Genre,
    Album,
    Track,
    Session,
    SessionTrack,
    RecommendationResult,
    PrototypeFeedback
)


# =========================================================
# ARTIST ADMIN
# =========================================================
@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = ("id", "artist_name")
    search_fields = ("artist_name",)


# =========================================================
# GENRE ADMIN
# =========================================================
@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ("id", "genre")
    search_fields = ("genre",)


# =========================================================
# ALBUM ADMIN
# =========================================================
@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    list_display = ("id", "album_name", "artist")
    search_fields = ("album_name",)
    list_filter = ("artist",)


# =========================================================
# TRACK ADMIN
# =========================================================
@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "track_name",
        "artist",
        "album",
        "genre",
        "tempo",
        "energy",
        "mood",
    )

    search_fields = (
        "track_name",
        "artist__artist_name",
    )

    list_filter = (
        "genre",
        "mood",
    )


# =========================================================
# SESSION ADMIN
# =========================================================
@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created_at",
        "genre_pref",
        "mood_pref",
        "energy_pref",
        "tempo_pref",
        "user_rating",
    )

    list_filter = (
        "genre_pref",
        "mood_pref",
    )


# =========================================================
# SESSION TRACK ADMIN
# =========================================================
@admin.register(SessionTrack)
class SessionTrackAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "session",
        "track",
        "position",
    )

    list_filter = ("session",)


# =========================================================
# RECOMMENDATION RESULT ADMIN
# =========================================================
@admin.register(RecommendationResult)
class RecommendationResultAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "session",
        "track",
        "score",
        "created_at",
    )

    list_filter = ("created_at",)


# =========================================================
# USER TESTING MODEL ADMIN
# =========================================================


@admin.register(PrototypeFeedback)
class PrototypeFeedbackAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "session",
        "recommendation_relevance",
        "explanation_clarity",
        "interface_ease_of_use",
        "search_clarity",
        "comments",
        "created_at",
    )

    list_filter = ("created_at",)
