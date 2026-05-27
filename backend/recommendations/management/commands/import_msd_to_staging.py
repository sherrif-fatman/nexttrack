#imports data from MSD into staging table fro review and cleaning if necessary before import into live database
#aid memoir useful commands for insepcting sqlite databases sqlite3 backend/recommendations/external_data/msd/track_metadata.db


# =========================================================
# IMPORT MSD TO STAGING COMMAND
#
# Imports track metadata from the Million Song Dataset
# SQLite database into the ImportedTrackData staging table.
#
# Usage:
# python manage.py import_msd_to_staging --limit 5000
# =========================================================

import sqlite3
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from recommendations.models import ImportedTrackData


class Command(BaseCommand):
    help = "Import random tracks from MSD track_metadata.db into staging table"

    # =====================================================
    # COMMAND ARGUMENTS
    # =====================================================
    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=5000,
            help="Number of random tracks to import"
        )

        parser.add_argument(
            "--db-path",
            type=str,
            default=None,
            help="Optional path to MSD track_metadata.db"
        )

        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing MSD staged records before importing"
        )

    # =====================================================
    # MAIN COMMAND ENTRY POINT
    # =====================================================
    def handle(self, *args, **options):
        limit = options["limit"]
        clear_existing = options["clear"]

        db_path = self.get_db_path(options["db_path"])

        if not db_path.exists():
            raise CommandError(f"MSD database not found: {db_path}")

        if clear_existing:
            deleted_count, _ = ImportedTrackData.objects.filter(
                source="MSD"
            ).delete()

            self.stdout.write(
                self.style.WARNING(
                    f"Cleared {deleted_count} existing MSD staging records"
                )
            )

        imported_count = self.import_tracks_from_sqlite(
            db_path=db_path,
            limit=limit
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"MSD staging import complete. Imported: {imported_count}"
            )
        )

    # =====================================================
    # GET DATABASE PATH
    #
    # Uses provided --db-path if supplied.
    # Otherwise uses the default project location.
    # =====================================================
    def get_db_path(self, supplied_path):
        if supplied_path:
            return Path(supplied_path)

        return (
                Path(__file__).resolve().parents[3]
                / "recommendations"
                / "external_data"
                / "msd"
                / "track_metadata.db"
            )

    # =====================================================
    # IMPORT TRACKS FROM SQLITE
    #
    # Reads random rows from the MSD SQLite database
    # and stores them in ImportedTrackData.
    # =====================================================
    def import_tracks_from_sqlite(self, db_path, limit):
        connection = sqlite3.connect(db_path)
        connection.row_factory = sqlite3.Row

        try:
            cursor = connection.cursor()

            rows = cursor.execute(
                """
                SELECT
                    track_id,
                    title,
                    song_id,
                    release,
                    artist_id,
                    artist_mbid,
                    artist_name,
                    duration,
                    artist_familiarity,
                    artist_hotttnesss,
                    year,
                    track_7digitalid,
                    shs_perf,
                    shs_work
                FROM songs
                ORDER BY RANDOM()
                LIMIT ?
                """,
                [limit]
            ).fetchall()

            imported_count = 0

            for row in rows:
                source_track_id = self.clean_value(row["track_id"])

                # -----------------------------------------
                # Skip rows without a source track ID.
                # We need this to identify the MSD record.
                # -----------------------------------------
                if not source_track_id:
                    continue

                # -----------------------------------------
                # Store extra MSD fields as JSON.
                # This preserves useful metadata without
                # forcing everything into production tables.
                # -----------------------------------------
                raw_data = {
                    "artist_id": self.clean_value(row["artist_id"]),
                    "duration": row["duration"],
                    "artist_familiarity": row["artist_familiarity"],
                    "artist_hotttnesss": row["artist_hotttnesss"],
                    "year": row["year"],
                    "track_7digitalid": row["track_7digitalid"],
                    "shs_perf": row["shs_perf"],
                    "shs_work": row["shs_work"],
                }

                # -----------------------------------------
                # update_or_create makes the command safe
                # to run more than once.
                # -----------------------------------------
                _, created = ImportedTrackData.objects.update_or_create(
                    source="MSD",
                    source_track_id=source_track_id,
                    defaults={
                        "source_song_id": self.clean_value(row["song_id"]),
                        "artist_name": self.clean_value(row["artist_name"]),
                        "artist_mbid": self.clean_value(row["artist_mbid"]),
                        "album_name": self.clean_value(row["release"]),
                        "track_name": self.clean_value(row["title"]),
                        "raw_data": raw_data,
                        "processed": False,
                        "processing_error": "",
                    }
                )

                if created:
                    imported_count += 1

            return imported_count

        finally:
            connection.close()

    # =====================================================
    # CLEAN VALUE
    #
    # Converts None values to empty strings and removes
    # whitespace from text fields.
    # =====================================================
    def clean_value(self, value):
        if value is None:
            return ""

        return str(value).strip()