# command aide memoir: docker compose run --rm backend python manage.py seed_tracks 

import csv
from pathlib import Path

from django.core.management.base import BaseCommand

from recommendations.models import (
    Artist,
    Genre,
    Album,
    Track
)


# =========================================================
# DJANGO MANAGEMENT COMMAND
# This command seeds the database using CSV test data
#
# Usage:
# python manage.py seed_tracks
# =========================================================
class Command(BaseCommand):

    # Command description shown in Django help
    help = "Seed the database with test track data from CSV"

    # =====================================================
    # MAIN COMMAND EXECUTION
    # =====================================================
    def handle(self, *args, **options):

        # =================================================
        # BUILD FILE PATH TO CSV
        #
        # __file__ = current file
        # parents[2] navigates back to recommendations/
        # =================================================
        csv_path = (
            Path(__file__).resolve().parents[2]
            / "test_data.csv"
        )

        # =================================================
        # CHECK CSV EXISTS
        # =================================================
        if not csv_path.exists():

            self.stderr.write(
                self.style.ERROR(
                    f"CSV file not found: {csv_path}"
                )
            )

            return

        # =================================================
        # TRACK HOW MANY RECORDS ARE CREATED/UPDATED
        # =================================================
        created_count = 0
        updated_count = 0

        # =================================================
        # OPEN CSV FILE
        # =================================================
        with open(
            csv_path,
            newline="",
            encoding="utf-8"
        ) as csvfile:

            # =============================================
            # READ CSV ROWS AS DICTIONARIES
            #
            # Example:
            # row["artist_name"]
            # =============================================
            reader = csv.DictReader(csvfile)

            # =============================================
            # LOOP THROUGH EACH CSV ROW
            # =============================================
            for row in reader:

                # =========================================
                # CREATE OR GET ARTIST
                #
                # Prevents duplicates
                # =========================================
                artist, _ = Artist.objects.get_or_create(
                    artist_name=row["artist_name"].strip()
                )

                # =========================================
                # CREATE OR GET GENRE
                # =========================================
                genre, _ = Genre.objects.get_or_create(
                    genre=row["genre"].strip()
                )

                # =========================================
                # CREATE OR GET ALBUM
                #
                # Album linked to artist
                # =========================================
                album, _ = Album.objects.get_or_create(
                    album_name=row["album_name"].strip(),
                    artist=artist
                )

                # =========================================
                # CREATE OR UPDATE TRACK
                #
                # update_or_create:
                # - creates if missing
                # - updates if existing
                # =========================================
                track, created = Track.objects.update_or_create(

                    # Fields used to identify uniqueness
                    track_name=row["track_name"].strip(),
                    artist=artist,

                    # Fields updated if record exists
                    defaults={
                        "album": album,
                        "genre": genre,
                        "tempo": int(row["tempo"]),
                        "energy": int(row["energy"]),
                        "mood": row["mood"].strip(),
                    }
                )

                # =========================================
                # TRACK CREATE VS UPDATE COUNTS
                # =========================================
                if created:
                    created_count += 1
                else:
                    updated_count += 1

        # =================================================
        # SUCCESS OUTPUT
        # =================================================
        self.stdout.write(

            self.style.SUCCESS(
                f"Seed complete. "
                f"Created: {created_count}, "
                f"Updated: {updated_count}"
            )
        )