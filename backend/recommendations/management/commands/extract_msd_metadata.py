import sqlite3
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from recommendations.models import ImportedTrackData


class Command(BaseCommand):
    help = (
        "Import track metadata from MSD track_metadata.db "
        "into the ImportedTrackData staging table."
    )

    SOURCE_NAME = "msd"

    # =====================================================
    # COMMAND ARGUMENTS
    # =====================================================
    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=5000,
            help=(
                "Maximum number of tracks to import. "
                "Used for both random and HDF5-subset imports."
            ),
        )

        parser.add_argument(
            "--db-path",
            type=str,
            default=None,
            help="Optional path to MSD track_metadata.db",
        )

        parser.add_argument(
            "--h5-path",
            type=str,
            default=None,
            help=(
                "Optional path to the MSD HDF5 subset. "
                "When supplied, only tracks represented by "
                "HDF5 files are imported."
            ),
        )

        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing MSD staged records before importing",
        )

    # =====================================================
    # MAIN COMMAND ENTRY POINT
    # =====================================================
    def handle(self, *args, **options):
        limit = options["limit"]
        clear_existing = options["clear"]

        if limit <= 0:
            raise CommandError("--limit must be greater than zero")

        db_path = self.get_db_path(
            options["db_path"]
        )

        if not db_path.exists():
            raise CommandError(
                f"MSD database not found: {db_path}"
            )

        if not db_path.is_file():
            raise CommandError(
                f"MSD database path is not a file: {db_path}"
            )

        h5_path = None

        if options["h5_path"]:
            h5_path = Path(
                options["h5_path"]
            ).expanduser().resolve()

            if not h5_path.exists():
                raise CommandError(
                    f"HDF5 data path not found: {h5_path}"
                )

            if not h5_path.is_dir():
                raise CommandError(
                    f"HDF5 data path is not a directory: {h5_path}"
                )

        if clear_existing:
            deleted_count, _ = (
                ImportedTrackData.objects
                .filter(source=self.SOURCE_NAME)
                .delete()
            )

            self.stdout.write(
                self.style.WARNING(
                    f"Cleared {deleted_count} existing "
                    "MSD staging records"
                )
            )

        if h5_path:
            track_ids = self.get_h5_track_ids(
                h5_path=h5_path,
                limit=limit,
            )

            self.stdout.write(
                f"Found {len(track_ids)} HDF5 track IDs"
            )

            (
                created_count,
                updated_count,
                skipped_count,
            ) = self.import_tracks_by_id(
                db_path=db_path,
                track_ids=track_ids,
            )

        else:
            (
                created_count,
                updated_count,
                skipped_count,
            ) = self.import_random_tracks(
                db_path=db_path,
                limit=limit,
            )

        self.stdout.write(
            self.style.SUCCESS(
                "MSD staging import complete. "
                f"Created: {created_count}, "
                f"updated: {updated_count}, "
                f"skipped: {skipped_count}"
            )
        )

    # =====================================================
    # DEFAULT DATABASE PATH
    # =====================================================
    def get_db_path(self, supplied_path):
        if supplied_path:
            return Path(
                supplied_path
            ).expanduser().resolve()

        return (
            Path(__file__).resolve().parents[3]
            / "recommendations"
            / "external_data"
            / "msd"
            / "track_metadata.db"
        )

    # =====================================================
    # COLLECT HDF5 TRACK IDS
    # =====================================================
    def get_h5_track_ids(
        self,
        h5_path,
        limit,
    ):
        """
        Use HDF5 filenames as MSD track IDs.

        Example:
            TRARRZU128F4253CA2.h5
            ->
            TRARRZU128F4253CA2
        """

        track_ids = []

        for path in h5_path.rglob("*.h5"):
            track_ids.append(path.stem)

            if len(track_ids) >= limit:
                break

        return track_ids

    # =====================================================
    # IMPORT TRACKS MATCHING HDF5 IDS
    # =====================================================
    def import_tracks_by_id(
        self,
        db_path,
        track_ids,
    ):
        try:
            connection = sqlite3.connect(
                str(db_path)
            )

            connection.row_factory = sqlite3.Row

        except sqlite3.Error as error:
            raise CommandError(
                f"Could not open MSD SQLite database: {error}"
            ) from error

        try:
            created_count = 0
            updated_count = 0
            skipped_count = 0

            cursor = connection.cursor()

            for track_id in track_ids:

                row = cursor.execute(
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
                    WHERE track_id = ?
                    """,
                    [track_id],
                ).fetchone()

                if not row:
                    skipped_count += 1
                    continue

                created = self.save_staging_row(
                    row
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

            return (
                created_count,
                updated_count,
                skipped_count,
            )

        except sqlite3.Error as error:
            raise CommandError(
                f"Error reading MSD SQLite database: {error}"
            ) from error

        finally:
            connection.close()

    # =====================================================
    # RANDOM IMPORT
    # =====================================================
    def import_random_tracks(
        self,
        db_path,
        limit,
    ):
        try:
            connection = sqlite3.connect(
                str(db_path)
            )

            connection.row_factory = sqlite3.Row

        except sqlite3.Error as error:
            raise CommandError(
                f"Could not open MSD SQLite database: {error}"
            ) from error

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
                [limit],
            ).fetchall()

            created_count = 0
            updated_count = 0
            skipped_count = 0

            for row in rows:

                source_track_id = self.clean_text(
                    row["track_id"]
                )

                if not source_track_id:
                    skipped_count += 1
                    continue

                created = self.save_staging_row(
                    row
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

            return (
                created_count,
                updated_count,
                skipped_count,
            )

        except sqlite3.Error as error:
            raise CommandError(
                f"Error reading MSD SQLite database: {error}"
            ) from error

        finally:
            connection.close()

    # =====================================================
    # SAVE ONE STAGING RECORD
    # =====================================================
    def save_staging_row(
        self,
        row,
    ):
        source_track_id = self.clean_text(
            row["track_id"]
        )

        if not source_track_id:
            return False

        duration_seconds = self.clean_float(
            row["duration"]
        )

        release_year = self.clean_year(
            row["year"]
        )

        raw_data = {
            "artist_id": self.clean_text(
                row["artist_id"]
            ),
            "duration": duration_seconds,
            "artist_familiarity": self.clean_float(
                row["artist_familiarity"]
            ),
            "artist_hotttnesss": self.clean_float(
                row["artist_hotttnesss"]
            ),
            "year": release_year,
            "track_7digitalid": self.clean_integer(
                row["track_7digitalid"]
            ),
            "shs_perf": self.clean_integer(
                row["shs_perf"]
            ),
            "shs_work": self.clean_integer(
                row["shs_work"]
            ),
        }

        _, created = (
            ImportedTrackData.objects
            .update_or_create(
                source=self.SOURCE_NAME,
                source_track_id=source_track_id,
                defaults={
                    "source_song_id": self.clean_text(
                        row["song_id"]
                    ),
                    "artist_name": self.clean_text(
                        row["artist_name"]
                    ),
                    "artist_mbid": self.clean_text(
                        row["artist_mbid"]
                    ),
                    "album_name": self.clean_text(
                        row["release"]
                    ),
                    "track_name": self.clean_text(
                        row["title"]
                    ),
                    "duration_seconds": (
                        duration_seconds
                    ),
                    "release_year": release_year,
                    "raw_data": raw_data,
                    "processed": False,
                    "processed_at": None,
                    "processing_error": "",
                },
            )
        )

        return created

    # =====================================================
    # CLEANING HELPERS
    # =====================================================
    @staticmethod
    def clean_text(value):
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
    def clean_integer(value):
        if value in (None, ""):
            return None

        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def clean_year(value):
        if value in (
            None,
            "",
            0,
            "0",
        ):
            return None

        try:
            year = int(value)
        except (TypeError, ValueError):
            return None

        if 1000 <= year <= 9999:
            return year

        return None