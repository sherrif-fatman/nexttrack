# =========================================================
# ENRICH STAGING GENRES COMMAND
#
# Uses artist_term.db from the Million Song Dataset to add
# genre/tag data to ImportedTrackData before the data is
# processed into the production Track table.
#
# Usage:
# python manage.py enrich_staging_genres --limit 5000
# =========================================================

import sqlite3
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from recommendations.models import ImportedTrackData


class Command(BaseCommand):
    help = "Enrich ImportedTrackData records with genre terms from artist_term.db"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=5000,
            help="Number of staging records to enrich"
        )

        parser.add_argument(
            "--db-path",
            type=str,
            default=None,
            help="Optional path to MSD artist_term.db"
        )

    def handle(self, *args, **options):
        db_path = self.get_db_path(options["db_path"])
        limit = options["limit"]

        if not db_path.exists():
            raise CommandError(f"artist_term.db not found: {db_path}")

        enriched_count = self.enrich_staging_records(
            db_path=db_path,
            limit=limit
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Staging genre enrichment complete. Enriched: {enriched_count}"
            )
        )

    def get_db_path(self, supplied_path):
        if supplied_path:
            return Path(supplied_path)

        return (
            Path(__file__).resolve().parents[3]
            / "recommendations"
            / "external_data"
            / "msd"
            / "artist_term.db"
        )

    def enrich_staging_records(self, db_path, limit):
        connection = sqlite3.connect(db_path)
        connection.row_factory = sqlite3.Row

        try:
            staged_tracks = ImportedTrackData.objects.filter(
                source="MSD",
                genre=""
            )[:limit]

            enriched_count = 0

            for staged_track in staged_tracks:
                raw_data = staged_track.raw_data or {}
                artist_id = raw_data.get("artist_id")

                if not artist_id:
                    continue

                genre = self.get_best_genre_for_artist(
                    connection=connection,
                    artist_id=artist_id
                )

                if not genre:
                    continue

                staged_track.genre = genre
                staged_track.save(update_fields=["genre"])

                enriched_count += 1

            return enriched_count

        finally:
            connection.close()

    def get_best_genre_for_artist(self, connection, artist_id):
        row = connection.execute(
            """
            SELECT term
            FROM artist_term
            WHERE artist_id = ?
            LIMIT 1
            """,
            [artist_id]
        ).fetchone()

        if not row:
            return ""

        return row["term"].strip()