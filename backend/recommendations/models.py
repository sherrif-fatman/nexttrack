# useful coomands aide memoir
# docker compose run --rm backend python manage.py makemigrations
# docker compose run --rm backend python manage.py migrate
# docker compose run --rm backend python manage.py test



from django.db import models

# =========================================================
# ARTIST MODEL
# Stores artist information
# =========================================================
class Artist(models.Model):
    artist_name = models.CharField(max_length=255, unique=True)
    musicbrainz_artist_id = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.artist_name


# =========================================================
# GENRE MODEL
# Stores music genre categories
# =========================================================
class Genre(models.Model):
    genre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.genre


# =========================================================
# ALBUM MODEL
# Stores album information linked to an artist
# =========================================================
class Album(models.Model):
    album_name = models.CharField(max_length=255)
    musicbrainz_release_id = models.CharField(max_length=100, blank=True)

    artist = models.ForeignKey(
        Artist,
        on_delete=models.CASCADE,
        related_name="albums"
    )
    cover_image_url = models.URLField(blank=True)
    

    def __str__(self):
        return self.album_name


# =========================================================
# TRACK MODEL
# Core music catalogue entity
# Stores track metadata and recommendation attributes
# =========================================================
class Track(models.Model):
    track_name = models.CharField(max_length=255)
    msd_track_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    msd_song_id = models.CharField(max_length=100, blank=True, null=True)

    album = models.ForeignKey(
        Album,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tracks"
    )

    artist = models.ForeignKey(
        Artist,
        on_delete=models.CASCADE,
        related_name="tracks"
    )

    genre = models.ForeignKey(
        Genre,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tracks"
    )

    tempo = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    energy = models.PositiveSmallIntegerField(
        null=True,
        blank=True
    )

    mood = models.CharField(
        max_length=100,
        blank=True
    )

    def __str__(self):
        return f"{self.track_name} - {self.artist.artist_name}"


# =========================================================
# SESSION MODEL
# Represents a single recommendation request/session
# Stores user recommendation preferences
# =========================================================
class Session(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)

    popularity = models.PositiveSmallIntegerField(
        null=True,
        blank=True
    )

    genre_pref = models.CharField(
        max_length=100,
        blank=True
    )

    energy_pref = models.PositiveSmallIntegerField(
        null=True,
        blank=True
    )

    mood_pref = models.CharField(
        max_length=100,
        blank=True
    )

    tempo_pref = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    user_rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True
    )

    def __str__(self):
        return f"Session {self.id} - {self.created_at}"


# =========================================================
# SESSION TRACK MODEL
# Stores tracks entered during a recommendation session
# Maintains listening order using 'position'
# =========================================================
class SessionTrack(models.Model):
    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name="session_tracks"
    )

    track = models.ForeignKey(
        Track,
        on_delete=models.CASCADE,
        related_name="session_entries"
    )

    position = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ["position"]

    def __str__(self):
        return f"{self.session} - {self.track} ({self.position})"


# =========================================================
# RECOMMENDATION RESULT MODEL
# Stores recommendation results generated for a session
# Includes recommendation score and explanation
# =========================================================
class RecommendationResult(models.Model):
    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name="recommendation_results"
    )

    track = models.ForeignKey(
        Track,
        on_delete=models.CASCADE,
        related_name="recommendation_results"
    )

    score = models.FloatField()

    reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-score", "-created_at"]

    def __str__(self):
        return f"{self.track} - score {self.score}"
    

# =========================================================
# Staging model to handle import and data cleanliness
# IMPORTED TRACK DATA MODEL
# Stores raw external music data before it is cleaned and
# mapped into Artist, Album, Genre and Track.
# =========================================================
class ImportedTrackData(models.Model):
    SOURCE_CHOICES = [
        ("MSD", "Million Song Dataset"),
        ("MUSICBRAINZ", "MusicBrainz"),
    ]

    source = models.CharField(
        max_length=50,
        choices=SOURCE_CHOICES
    )

    source_track_id = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    source_song_id = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    artist_name = models.CharField(
        max_length=255,
        blank=True
    )

    artist_mbid = models.CharField(
        max_length=100,
        blank=True
    )

    album_name = models.CharField(
        max_length=255,
        blank=True
    )

    track_name = models.CharField(
        max_length=255,
        blank=True
    )

    genre = models.CharField(
        max_length=100,
        blank=True
    )

    tempo = models.FloatField(
        null=True,
        blank=True
    )

    energy = models.FloatField(
        null=True,
        blank=True
    )

    mood = models.CharField(
        max_length=100,
        blank=True
    )

    raw_data = models.JSONField(
        null=True,
        blank=True
    )

    processed = models.BooleanField(
        default=False
    )

    processing_error = models.TextField(
        blank=True
    )

    imported_at = models.DateTimeField(
        auto_now_add=True
    )

    processed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        indexes = [
            models.Index(fields=["source"]),
            models.Index(fields=["processed"]),
            models.Index(fields=["source_track_id"]),
        ]

    def __str__(self):
        return f"{self.source} - {self.track_name}"
    

# =========================================================
# PROTOTYPE FEEDBACK MODEL
# Stores user feedback from prototype testing
# =========================================================
class PrototypeFeedback(models.Model):
    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name="feedback",
        null=True,
        blank=True
    )

    recommendation_relevance = models.PositiveSmallIntegerField()
    explanation_clarity = models.PositiveSmallIntegerField()
    interface_ease_of_use = models.PositiveSmallIntegerField()
    search_clarity = models.PositiveSmallIntegerField()

    comments = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback {self.id} - Session {self.session_id}"
