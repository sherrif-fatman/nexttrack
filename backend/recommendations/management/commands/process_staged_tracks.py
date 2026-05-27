# =========================================================
#aide memoir to run  docker compose run --rm backend python manage.py process_staged_tracks --limit 5000
# PROCESS STAGED TRACKS COMMAND
#
# Converts records from ImportedTrackData into the cleaned
# production tables used by the recommendation engine:
#
# Artist
# Album
# Genre
# Track
#
# Usage:
# python manage.py process_staged_tracks --limit 5000
# =========================================================

from django.core.management.base import BaseCommand
from django.utils import timezone

from recommendations.models import (
    ImportedTrackData,
    Artist,
    Album,
    Genre,
    Track,
)


class Command(BaseCommand):
    help = "Process staged imported track data into production music tables"

    # =====================================================
    # COMMAND ARGUMENTS
    # =====================================================
    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=5000,
            help="Number of staged records to process"
        )

    # =====================================================
    # MAIN COMMAND ENTRY POINT
    # =====================================================
    def handle(self, *args, **options):
        limit = options["limit"]

        staged_tracks = ImportedTrackData.objects.filter(
            source="MSD",
            processed=False
        )[:limit]

        processed_count = 0
        error_count = 0

        for staged_track in staged_tracks:
            try:
                self.process_single_track(staged_track)
                processed_count += 1

            except Exception as error:
                error_count += 1

                staged_track.processing_error = str(error)
                staged_track.processed_at = timezone.now()
                staged_track.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"Processing complete. "
                f"Processed: {processed_count}, "
                f"Errors: {error_count}"
            )
        )

    # =====================================================
    # PROCESS ONE STAGED TRACK
    # =====================================================
    def process_single_track(self, staged_track):

        # -------------------------------------------------
        # Validate required fields
        # -------------------------------------------------
        if not staged_track.track_name:
            raise ValueError("Missing track name")

        if not staged_track.artist_name:
            raise ValueError("Missing artist name")

        if not staged_track.album_name:
            album_name = "Unknown Album"
        else:
            album_name = staged_track.album_name

        # -------------------------------------------------
        # Create or update Artist
        # -------------------------------------------------
        artist, _ = Artist.objects.update_or_create(
            artist_name=staged_track.artist_name,
            defaults={
                "musicbrainz_artist_id": staged_track.artist_mbid or ""
            }
        )

        # -------------------------------------------------
        # Create or get Album
        # -------------------------------------------------
        album, _ = Album.objects.get_or_create(
            album_name=album_name,
            artist=artist
        )

        # -------------------------------------------------
        # Genre is unknown at this stage.
        # Later we can populate this using artist_term.db
        # or tagtraum genre annotations.
        # -------------------------------------------------
        genre_name = staged_track.genre or "Unknown"

        genre, _ = Genre.objects.get_or_create(
            genre=genre_name
        )

        # -------------------------------------------------
        # Extract optional raw metadata
        # -------------------------------------------------
        raw_data = staged_track.raw_data or {}

        year = raw_data.get("year")
        artist_hotttnesss = raw_data.get("artist_hotttnesss")

        # -------------------------------------------------
        # Convert artist_hotttnesss into a rough energy proxy
        #
        # This is temporary and can be replaced later with
        # actual audio feature data from .h5 files.
        # -------------------------------------------------
        energy = None

        if artist_hotttnesss is not None:
            energy = round(float(artist_hotttnesss) * 10)

        # -------------------------------------------------
        # Create or update Track
        # -------------------------------------------------
        Track.objects.update_or_create(
            msd_track_id=staged_track.source_track_id,
            defaults={
                "msd_song_id": staged_track.source_song_id,
                "track_name": staged_track.track_name,
                "artist": artist,
                "album": album,
                "genre": genre,
                "energy": energy,
                "mood": "",
            }
        )

        # -------------------------------------------------
        # Mark staging row as processed
        # -------------------------------------------------
        staged_track.processed = True
        staged_track.processing_error = ""
        staged_track.processed_at = timezone.now()
        staged_track.save()