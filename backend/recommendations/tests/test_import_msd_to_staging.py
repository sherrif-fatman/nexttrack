# =========================================================
# EXTRACT MSD METADATA TESTS
#
# These tests create a temporary SQLite database that mimics
# the MSD track_metadata.db structure.
#
# The extract_msd_metadata management command should import
# rows into ImportedTrackData, which acts as the staging
# table before catalogue processing takes place.
# =========================================================

import sqlite3
import tempfile
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase

from recommendations.models import ImportedTrackData


class ExtractMSDMetadataCommandTest(TestCase):

    # =====================================================
    # CREATE TEMPORARY MSD-LIKE SQLITE DATABASE
    # =====================================================
    def create_temp_msd_database(self):
        """
        Create a temporary SQLite database containing a small
        songs table that resembles the structure used by the
        Million Song Dataset track_metadata.db file.
        """

        temp_file = tempfile.NamedTemporaryFile(
            suffix=".db",
            delete=False,
        )

        db_path = Path(temp_file.name)
        temp_file.close()

        connection = sqlite3.connect(db_path)
        cursor = connection.cursor()

        # -------------------------------------------------
        # Create a songs table containing the MSD metadata
        # fields used by extract_msd_metadata.
        # -------------------------------------------------
        cursor.execute(
            """
            CREATE TABLE songs (
                track_id TEXT PRIMARY KEY,
                title TEXT,
                song_id TEXT,
                release TEXT,
                artist_id TEXT,
                artist_mbid TEXT,
                artist_name TEXT,
                duration REAL,
                artist_familiarity REAL,
                artist_hotttnesss REAL,
                year INT,
                track_7digitalid INT,
                shs_perf INT,
                shs_work INT
            )
            """
        )

        # -------------------------------------------------
        # Insert two representative sample rows.
        # -------------------------------------------------
        cursor.execute(
            """
            INSERT INTO songs VALUES (
                'TRTEST001',
                'Test Track One',
                'SOTEST001',
                'Test Album One',
                'ARTEST001',
                'mbid-artist-001',
                'Test Artist One',
                210.5,
                0.7,
                0.5,
                2001,
                12345,
                -1,
                0
            )
            """
        )

        cursor.execute(
            """
            INSERT INTO songs VALUES (
                'TRTEST002',
                'Test Track Two',
                'SOTEST002',
                'Test Album Two',
                'ARTEST002',
                '',
                'Test Artist Two',
                180.0,
                0.4,
                0.3,
                1999,
                67890,
                -1,
                0
            )
            """
        )

        connection.commit()
        connection.close()

        return db_path

    # =====================================================
    # TEST: COMMAND IMPORTS TRACKS INTO STAGING
    # =====================================================
    def test_extract_msd_metadata_creates_imported_track_data(self):
        """
        Verify that rows from the temporary MSD database are
        imported into ImportedTrackData correctly.
        """

        db_path = self.create_temp_msd_database()

        try:
            call_command(
                "extract_msd_metadata",
                "--db-path",
                str(db_path),
                "--limit",
                "2",
            )

            # Both sample tracks should have been imported.
            self.assertEqual(
                ImportedTrackData.objects.count(),
                2,
            )

            staged_track = ImportedTrackData.objects.get(
                source_track_id="TRTEST001",
            )

            # -------------------------------------------------
            # Check the main staging fields.
            # -------------------------------------------------
            self.assertEqual(
                staged_track.source,
                "msd",
            )

            self.assertEqual(
                staged_track.source_song_id,
                "SOTEST001",
            )

            self.assertEqual(
                staged_track.artist_name,
                "Test Artist One",
            )

            self.assertEqual(
                staged_track.artist_mbid,
                "mbid-artist-001",
            )

            self.assertEqual(
                staged_track.album_name,
                "Test Album One",
            )

            self.assertEqual(
                staged_track.track_name,
                "Test Track One",
            )

            self.assertEqual(
                staged_track.duration_seconds,
                210.5,
            )

            self.assertEqual(
                staged_track.release_year,
                2001,
            )

            # Newly imported staging records should not yet
            # be marked as processed.
            self.assertFalse(
                staged_track.processed,
            )

            # -------------------------------------------------
            # Check additional MSD values retained in raw_data.
            # -------------------------------------------------
            self.assertEqual(
                staged_track.raw_data["artist_id"],
                "ARTEST001",
            )

            self.assertEqual(
                staged_track.raw_data["year"],
                2001,
            )

            self.assertEqual(
                staged_track.raw_data["artist_familiarity"],
                0.7,
            )

            self.assertEqual(
                staged_track.raw_data["artist_hotttnesss"],
                0.5,
            )

        finally:
            # Always remove the temporary database, even if an
            # assertion fails.
            db_path.unlink(missing_ok=True)

    # =====================================================
    # TEST: CLEAR OPTION REMOVES EXISTING MSD STAGING DATA
    # =====================================================
    def test_extract_with_clear_removes_existing_msd_records(self):
        """
        Verify that --clear removes existing MSD staging records
        before importing the new sample data.
        """

        # Create an old MSD staging record that should be removed.
        ImportedTrackData.objects.create(
            source="msd",
            source_track_id="OLDTRACK",
            track_name="Old Track",
        )

        db_path = self.create_temp_msd_database()

        try:
            call_command(
                "extract_msd_metadata",
                "--db-path",
                str(db_path),
                "--limit",
                "1",
                "--clear",
            )

            # The previous MSD record should have been deleted.
            self.assertFalse(
                ImportedTrackData.objects.filter(
                    source_track_id="OLDTRACK",
                ).exists()
            )

            # Only the newly imported record should remain.
            self.assertEqual(
                ImportedTrackData.objects.count(),
                1,
            )

        finally:
            db_path.unlink(missing_ok=True)