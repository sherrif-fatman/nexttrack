# =========================================================
# IMPORT MSD TO STAGING TESTS
#
# These tests create a temporary SQLite database that mimics
# the MSD track_metadata.db structure.
# =========================================================

import sqlite3
import tempfile
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase

from recommendations.models import ImportedTrackData


class ImportMSDToStagingCommandTest(TestCase):

    # =====================================================
    # CREATE TEMPORARY MSD-LIKE SQLITE DATABASE
    # =====================================================
    def create_temp_msd_database(self):
        temp_file = tempfile.NamedTemporaryFile(
            suffix=".db",
            delete=False
        )

        db_path = Path(temp_file.name)
        temp_file.close()

        connection = sqlite3.connect(db_path)
        cursor = connection.cursor()

        # -------------------------------------------------
        # Create a songs table matching MSD metadata fields
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
        # Insert two sample rows
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
    def test_import_msd_to_staging_creates_imported_track_data(self):
        db_path = self.create_temp_msd_database()

        call_command(
            "import_msd_to_staging",
            "--db-path",
            str(db_path),
            "--limit",
            "2"
        )

        self.assertEqual(
            ImportedTrackData.objects.count(),
            2
        )

        staged_track = ImportedTrackData.objects.get(
            source_track_id="TRTEST001"
        )

        self.assertEqual(
            staged_track.source,
            "MSD"
        )

        self.assertEqual(
            staged_track.source_song_id,
            "SOTEST001"
        )

        self.assertEqual(
            staged_track.artist_name,
            "Test Artist One"
        )

        self.assertEqual(
            staged_track.artist_mbid,
            "mbid-artist-001"
        )

        self.assertEqual(
            staged_track.album_name,
            "Test Album One"
        )

        self.assertEqual(
            staged_track.track_name,
            "Test Track One"
        )

        self.assertFalse(
            staged_track.processed
        )

        self.assertEqual(
            staged_track.raw_data["year"],
            2001
        )

        db_path.unlink()

    # =====================================================
    # TEST: CLEAR OPTION REMOVES EXISTING MSD STAGING DATA
    # =====================================================
    def test_import_with_clear_removes_existing_msd_records(self):
        ImportedTrackData.objects.create(
            source="MSD",
            source_track_id="OLDTRACK",
            track_name="Old Track"
        )

        db_path = self.create_temp_msd_database()

        call_command(
            "import_msd_to_staging",
            "--db-path",
            str(db_path),
            "--limit",
            "1",
            "--clear"
        )

        self.assertFalse(
            ImportedTrackData.objects.filter(
                source_track_id="OLDTRACK"
            ).exists()
        )

        self.assertEqual(
            ImportedTrackData.objects.count(),
            1
        )

        db_path.unlink()