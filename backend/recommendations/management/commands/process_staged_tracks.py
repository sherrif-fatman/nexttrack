"""
Process staged Million Song Dataset records into the cleaned
NextTrack catalogue.

The source records are stored in ImportedTrackData. This command
creates or updates:

- Artist
- Album
- Genre
- Track

Usage:

docker compose run --rm backend \
    python manage.py process_staged_tracks --limit 5000

Optional retry of failed rows:

docker compose run --rm backend \
    python manage.py process_staged_tracks --limit 5000 --retry-errors
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from difflib import SequenceMatcher
import unicodedata

from recommendations.models import (
    Album,
    Artist,
    Genre,
    ImportedTrackData,
    Track,
)


class Command(BaseCommand):
    help = (
        "Process staged MSD records into the production catalogue tables."
    )

    SOURCE_NAME = "msd"
    UNKNOWN_ALBUM = "Unknown Album"
    UNKNOWN_GENRE = "Unknown"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=5000,
            help="Maximum number of staged records to process.",
        )

        parser.add_argument(
            "--retry-errors",
            action="store_true",
            help=(
                "Retry unprocessed records that already contain "
                "a processing error."
            ),
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        retry_errors = options["retry_errors"]

        if limit <= 0:
            raise CommandError("--limit must be greater than zero.")

        staged_tracks = ImportedTrackData.objects.filter(
            source=self.SOURCE_NAME,
            processed=False,
        )

        if not retry_errors:
            staged_tracks = staged_tracks.filter(
                processing_error="",
            )

        staged_tracks = staged_tracks.order_by("id")[:limit]

        processed_count = 0
        error_count = 0

        for staged_track in staged_tracks.iterator(
            chunk_size=500,
        ):
            try:
                self.process_single_track(staged_track)
                processed_count += 1

            except Exception as error:
                error_count += 1
                self.record_processing_error(
                    staged_track=staged_track,
                    error=error,
                )

                self.stderr.write(
                    self.style.ERROR(
                        f"Failed staging record {staged_track.id}: {error}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Processing complete. "
                f"Processed: {processed_count}, "
                f"errors: {error_count}."
            )
        )

    @transaction.atomic
    def process_single_track(self, staged_track):
        """
        Convert one staging row into catalogue records.

        The transaction ensures that Artist, Album, Genre and Track
        changes are rolled back together if processing fails.
        """

        track_name = self.clean_required_text(
            staged_track.track_name,
            "track name",
        )

        artist_name = self.clean_required_text(
            staged_track.artist_name,
            "artist name",
        )

        album_name = (
            self.clean_optional_text(staged_track.album_name)
            or self.UNKNOWN_ALBUM
        )

        genre_name = (
            self.clean_optional_text(staged_track.genre)
            or self.UNKNOWN_GENRE
        )

        raw_data = staged_track.raw_data or {}

        artist = self.get_or_update_artist(
            artist_name=artist_name,
            artist_mbid=self.clean_optional_text(
                staged_track.artist_mbid
            ),
        )

        album = self.get_or_update_album(
            artist=artist,
            album_name=album_name,
            release_year=(
                staged_track.release_year
                or self.clean_year(raw_data.get("year"))
            ),
            release_mbid=self.clean_optional_text(
                staged_track.album_mbid
            ),
        )

        genre, _ = Genre.objects.get_or_create(
            genre=genre_name,
        )

        familiarity = self.clean_float(
            raw_data.get("artist_familiarity")
        )

        popularity = self.clean_float(
            raw_data.get("artist_hotttnesss")
        )

        track_defaults = {
            "msd_song_id": (
                self.clean_optional_text(
                    staged_track.source_song_id
                )
            ),
            "track_name": track_name,
            "artist": artist,
            "album": album,
            "genre": genre,
            "musicbrainz_recording_id": (
                self.clean_optional_text(
                    staged_track.recording_mbid
                ) or None
            ),
            "duration_seconds": (
                staged_track.duration_seconds
                or self.clean_float(raw_data.get("duration"))
            ),
            "release_year": (
                staged_track.release_year
                or self.clean_year(raw_data.get("year"))
            ),
            "tempo": staged_track.tempo,
            "energy": self.normalise_energy(staged_track.energy),
            "mood": self.clean_optional_text(
                staged_track.mood
            ),
            "familiarity": familiarity,
            "popularity": popularity,
            "enrichment_status": "pending",
            "enrichment_error": "",
        }

        Track.objects.update_or_create(
            msd_track_id=staged_track.source_track_id,
            defaults=track_defaults,
        )

        staged_track.processed = True
        staged_track.processing_error = ""
        staged_track.processed_at = timezone.now()

        staged_track.save(
            update_fields=[
                "processed",
                "processing_error",
                "processed_at",
            ]
        )

    def get_or_update_artist(
        self,
        artist_name,
        artist_mbid,
    ):
        """
        Match by MusicBrainz ID only when the existing artist name is
        compatible with the staged artist credit.
        """

        artist_mbid = artist_mbid or None

        if artist_mbid:
            existing_artist = Artist.objects.filter(
                musicbrainz_artist_id=artist_mbid,
            ).first()

            if existing_artist:
                if self.artist_names_compatible(
                    existing_artist.artist_name,
                    artist_name,
                ):
                    return existing_artist

                raise ValueError(
                    "Conflicting MusicBrainz artist match: "
                    f"staged artist '{artist_name}' uses MBID "
                    f"{artist_mbid}, already assigned to "
                    f"'{existing_artist.artist_name}'."
                )

        artist, _ = Artist.objects.get_or_create(
            artist_name=artist_name,
        )

        if artist_mbid and not artist.musicbrainz_artist_id:
            artist.musicbrainz_artist_id = artist_mbid
            artist.save(
                update_fields=["musicbrainz_artist_id"]
            )

        return artist


    @staticmethod
    def normalise_artist_name(value):
        value = unicodedata.normalize("NFKD", value or "")
        value = "".join(
            character
            for character in value
            if not unicodedata.combining(character)
        )

        return " ".join(
            value.casefold()
            .replace("_", " ")
            .replace(";", " ")
            .replace(",", " ")
            .split()
        )


    @classmethod
    def artist_names_compatible(cls, first_name, second_name):
        first = cls.normalise_artist_name(first_name)
        second = cls.normalise_artist_name(second_name)

        if first == second:
            return True

        if first in second or second in first:
            return True

        first_primary = cls.normalise_artist_name(
            first_name.replace("_", ";").split(";")[0]
        )
        second_primary = cls.normalise_artist_name(
            second_name.replace("_", ";").split(";")[0]
        )

        if first_primary and first_primary == second_primary:
            return True

        similarity = SequenceMatcher(
            None,
            first,
            second,
        ).ratio()

        return similarity >= 0.75

    def get_or_update_album(
        self,
        artist,
        album_name,
        release_year,
        release_mbid,
    ):
        """
        Albums are unique by artist and album name.

        The current staging field album_mbid is treated as a release
        identifier until a separate release-group value is imported.
        """

        album, _ = Album.objects.get_or_create(
            artist=artist,
            album_name=album_name,
        )

        changed_fields = []

        if release_year and album.release_year != release_year:
            album.release_year = release_year
            changed_fields.append("release_year")

        if (
            release_mbid
            and album.musicbrainz_release_id != release_mbid
        ):
            existing_album = Album.objects.filter(
                musicbrainz_release_id=release_mbid,
            ).exclude(
                pk=album.pk,
            ).first()

            if existing_album:
                raise ValueError(
                    "MusicBrainz release ID is already assigned "
                    f"to album {existing_album.id}."
                )

            album.musicbrainz_release_id = release_mbid
            changed_fields.append("musicbrainz_release_id")

        if changed_fields:
            album.save(update_fields=changed_fields)

        return album

    def record_processing_error(
        self,
        staged_track,
        error,
    ):
        """
        Record a processing failure without marking the row processed.
        """

        staged_track.processed = False
        staged_track.processing_error = str(error)[:2000]
        staged_track.processed_at = timezone.now()

        staged_track.save(
            update_fields=[
                "processed",
                "processing_error",
                "processed_at",
            ]
        )

    @staticmethod
    def clean_required_text(value, field_name):
        cleaned_value = Command.clean_optional_text(value)

        if not cleaned_value:
            raise ValueError(f"Missing {field_name}.")

        return cleaned_value

    @staticmethod
    def clean_optional_text(value):
        if value is None:
            return ""

        return str(value).strip()

    @staticmethod
    def clean_float(value):
        if value in (None, ""):
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def clean_year(value):
        if value in (None, "", 0, "0"):
            return None

        try:
            year = int(value)
        except (TypeError, ValueError):
            return None

        if 1000 <= year <= 9999:
            return year

        return None

    @staticmethod
    def normalise_energy(value):
        """
        Accept either an existing 1-10 value or a source value in the
        range 0-1.

        No popularity or familiarity field is used as an energy proxy.
        """

        if value in (None, ""):
            return None

        try:
            energy = float(value)
        except (TypeError, ValueError):
            return None

        if 0.0 <= energy <= 1.0:
            return max(1, min(10, round(energy * 9) + 1))

        if 1.0 <= energy <= 10.0:
            return round(energy)

        return None