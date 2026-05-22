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

    artist = models.ForeignKey(
        Artist,
        on_delete=models.CASCADE,
        related_name="albums"
    )

    def __str__(self):
        return self.album_name


# =========================================================
# TRACK MODEL
# Core music catalogue entity
# Stores track metadata and recommendation attributes
# =========================================================
class Track(models.Model):
    track_name = models.CharField(max_length=255)

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
