# useful coomands aide memoir
# docker compose run --rm backend python manage.py makemigrations
# docker compose run --rm backend python manage.py migrate
# docker compose run --rm backend python manage.py test



from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


# ---------------------------------------------------------------------------
# Catalogue models
# ---------------------------------------------------------------------------

class Artist(models.Model):
    """Stores canonical artist information."""

    artist_name = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
    )

    musicbrainz_artist_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
    )

    def __str__(self):
        return self.artist_name


class Genre(models.Model):
    """Stores primary music genre categories."""

    genre = models.CharField(
        max_length=100,
        unique=True,
    )

    def __str__(self):
        return self.genre


class Tag(models.Model):
    """
    Stores flexible descriptive tags.

    Unlike Genre, a track can have multiple weighted tags such as:
    rock, alternative, energetic, melancholy or 1990s.
    """

    CATEGORY_CHOICES = [
        ("genre", "Genre"),
        ("mood", "Mood"),
        ("era", "Era"),
        ("context", "Listening context"),
        ("other", "Other"),
    ]

    name = models.CharField(
        max_length=100,
        unique=True,
    )

    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default="other",
    )

    def __str__(self):
        return self.name


class Album(models.Model):
    """Stores album information linked to an artist."""

    album_name = models.CharField(
        max_length=255,
        db_index=True,
    )

    artist = models.ForeignKey(
        Artist,
        on_delete=models.CASCADE,
        related_name="albums",
    )

    musicbrainz_release_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
    )

    musicbrainz_release_group_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_index=True,
    )

    release_year = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    cover_image_url = models.URLField(
        blank=True,
    )

    cover_thumbnail_url = models.URLField(
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["artist", "album_name"],
                name="unique_album_per_artist",
            )
        ]
        ordering = ["artist__artist_name", "album_name"]

    def __str__(self):
        return f"{self.album_name} - {self.artist.artist_name}"


class Track(models.Model):
    """
    Core music catalogue entity.

    Stores track metadata, external identifiers and recommendation
    attributes.
    """

    ENRICHMENT_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("matched", "Matched"),
        ("ambiguous", "Ambiguous"),
        ("not_found", "Not found"),
        ("failed", "Failed"),
    ]

    track_name = models.CharField(
        max_length=255,
        db_index=True,
    )

    artist = models.ForeignKey(
        Artist,
        on_delete=models.CASCADE,
        related_name="tracks",
    )

    album = models.ForeignKey(
        Album,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tracks",
    )

    genre = models.ForeignKey(
        Genre,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tracks",
    )

    tags = models.ManyToManyField(
        Tag,
        through="TrackTag",
        related_name="tracks",
        blank=True,
    )

    msd_track_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
    )

    msd_song_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_index=True,
    )

    musicbrainz_recording_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
    )

    duration_seconds = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0)],
    )

    release_year = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    tempo = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0)],
    )

    # Normalised NextTrack scale: 1 to 10.
    energy = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(10),
        ],
    )

    mood = models.CharField(
        max_length=100,
        blank=True,
    )

    loudness = models.FloatField(
        null=True,
        blank=True,
    )

    key = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(11),
        ],
    )

    mode = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1),
        ],
    )

    familiarity = models.FloatField(
        null=True,
        blank=True,
    )

    popularity = models.FloatField(
        null=True,
        blank=True,
    )

    enrichment_status = models.CharField(
        max_length=20,
        choices=ENRICHMENT_STATUS_CHOICES,
        default="pending",
        db_index=True,
    )

    enrichment_error = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["artist", "track_name"],
                name="track_artist_name_idx",
            ),
            models.Index(
                fields=["genre", "energy"],
                name="track_genre_energy_idx",
            ),
            models.Index(
                fields=["tempo"],
                name="track_tempo_idx",
            ),
        ]
        ordering = ["artist__artist_name", "track_name"]

    def __str__(self):
        return f"{self.track_name} - {self.artist.artist_name}"


class TrackTag(models.Model):
    """Stores the strength of a descriptive tag assigned to a track."""

    track = models.ForeignKey(
        Track,
        on_delete=models.CASCADE,
        related_name="track_tags",
    )

    tag = models.ForeignKey(
        Tag,
        on_delete=models.CASCADE,
        related_name="track_tags",
    )

    weight = models.FloatField(
        default=1.0,
        validators=[MinValueValidator(0.0)],
    )

    source = models.CharField(
        max_length=50,
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["track", "tag"],
                name="unique_tag_per_track",
            )
        ]
        ordering = ["-weight"]

    def __str__(self):
        return f"{self.track} - {self.tag} ({self.weight})"


# ---------------------------------------------------------------------------
# Recommendation session models
# ---------------------------------------------------------------------------

class Session(models.Model):
    """Represents a single recommendation request."""

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    popularity = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(10),
        ],
    )

    genre_pref = models.CharField(
        max_length=100,
        blank=True,
    )

    energy_pref = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(10),
        ],
    )

    mood_pref = models.CharField(
        max_length=100,
        blank=True,
    )

    tempo_pref = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0)],
    )

    user_rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ],
    )

    def __str__(self):
        return f"Session {self.id} - {self.created_at}"


class SessionTrack(models.Model):
    """Stores tracks entered during a recommendation session."""

    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name="session_tracks",
    )

    track = models.ForeignKey(
        Track,
        on_delete=models.CASCADE,
        related_name="session_entries",
    )

    position = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "position"],
                name="unique_position_per_session",
            ),
            models.UniqueConstraint(
                fields=["session", "track"],
                name="unique_track_per_session",
            ),
        ]

    def __str__(self):
        return f"{self.session} - {self.track} ({self.position})"


class RecommendationResult(models.Model):
    """Stores a recommendation generated for a session."""

    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name="recommendation_results",
    )

    track = models.ForeignKey(
        Track,
        on_delete=models.CASCADE,
        related_name="recommendation_results",
    )

    score = models.FloatField()

    reason = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-score", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "track"],
                name="unique_recommendation_per_session",
            )
        ]

    def __str__(self):
        return f"{self.track} - score {self.score}"


# ---------------------------------------------------------------------------
# Import and enrichment staging models
# ---------------------------------------------------------------------------

class ImportedTrackData(models.Model):
    """
    Stores raw external data before it is cleaned and mapped into the
    catalogue models.
    """

    SOURCE_CHOICES = [
        ("msd", "Million Song Dataset"),
        ("lastfm", "Last.fm Dataset"),
        ("musicbrainz", "MusicBrainz"),
        ("cover_art", "Cover Art Archive"),
    ]

    source = models.CharField(
        max_length=50,
        choices=SOURCE_CHOICES,
    )

    source_track_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    source_song_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    artist_name = models.CharField(
        max_length=255,
        blank=True,
    )

    artist_mbid = models.CharField(
        max_length=100,
        blank=True,
    )

    album_name = models.CharField(
        max_length=255,
        blank=True,
    )

    album_mbid = models.CharField(
        max_length=100,
        blank=True,
    )

    recording_mbid = models.CharField(
        max_length=100,
        blank=True,
    )

    track_name = models.CharField(
        max_length=255,
        blank=True,
    )

    genre = models.CharField(
        max_length=100,
        blank=True,
    )

    duration_seconds = models.FloatField(
        null=True,
        blank=True,
    )

    release_year = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    tempo = models.FloatField(
        null=True,
        blank=True,
    )

    energy = models.FloatField(
        null=True,
        blank=True,
    )

    mood = models.CharField(
        max_length=100,
        blank=True,
    )

    raw_data = models.JSONField(
        null=True,
        blank=True,
    )

    processed = models.BooleanField(
        default=False,
        db_index=True,
    )

    processing_error = models.TextField(
        blank=True,
    )

    imported_at = models.DateTimeField(
        auto_now_add=True,
    )

    processed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["source", "source_track_id"],
                name="import_source_track_idx",
            ),
            models.Index(
                fields=["artist_name", "track_name"],
                name="import_artist_track_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["source", "source_track_id"],
                name="unique_imported_source_track",
            )
        ]
        ordering = ["-imported_at"]

    def __str__(self):
        return f"{self.source} - {self.track_name}"


# ---------------------------------------------------------------------------
# Prototype evaluation model
# ---------------------------------------------------------------------------

class PrototypeFeedback(models.Model):
    """Stores feedback gathered during prototype evaluation."""

    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name="feedback",
        null=True,
        blank=True,
    )

    recommendation_relevance = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ],
    )

    explanation_clarity = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ],
    )

    interface_ease_of_use = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ],
    )

    search_clarity = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ],
    )

    comments = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return f"Feedback {self.id} - Session {self.session_id}"
