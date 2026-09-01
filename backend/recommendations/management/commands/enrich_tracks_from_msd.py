from pathlib import Path

import h5py

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from recommendations.models import (
    Tag,
    Track,
    TrackTag,
)

from recommendations.services.tag_filter import (
    filter_artist_terms,
)


class Command(BaseCommand):
    help = (
        "Enrich existing NextTrack catalogue tracks using "
        "Million Song Dataset HDF5 files."
    )

    SOURCE_NAME = "msd_artist_terms"

    # =====================================================
    # COMMAND ARGUMENTS
    # =====================================================
    def add_arguments(self, parser):

        parser.add_argument(
            "--data-path",
            type=str,
            default="/data/msd",
            help=(
                "Root directory containing the MSD HDF5 subset. "
                "Defaults to /data/msd."
            ),
        )

        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help=(
                "Maximum number of matching catalogue tracks "
                "to enrich."
            ),
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help=(
                "Inspect and validate enrichment without "
                "saving database changes."
            ),
        )

    # =====================================================
    # MAIN COMMAND ENTRY POINT
    # =====================================================
    def handle(self, *args, **options):

        data_path = Path(
            options["data_path"]
        ).expanduser().resolve()

        limit = options["limit"]
        dry_run = options["dry_run"]

        # -------------------------------------------------
        # Validate command arguments
        # -------------------------------------------------
        if not data_path.exists():
            raise CommandError(
                f"MSD data path not found: {data_path}"
            )

        if not data_path.is_dir():
            raise CommandError(
                f"MSD data path is not a directory: {data_path}"
            )

        if limit is not None and limit <= 0:
            raise CommandError(
                "--limit must be greater than zero"
            )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "DRY RUN: no database changes will be saved."
                )
            )

        # -------------------------------------------------
        # Locate all HDF5 files recursively.
        # -------------------------------------------------
        h5_files = data_path.rglob("*.h5")

        scanned_count = 0
        matched_count = 0
        enriched_count = 0
        skipped_count = 0
        error_count = 0

        # -------------------------------------------------
        # Process files one at a time.
        # -------------------------------------------------
        for h5_path in h5_files:

            scanned_count += 1

            try:
                result = self.process_h5_file(
                    h5_path=h5_path,
                    dry_run=dry_run,
                )

                if result == "matched":
                    matched_count += 1
                    enriched_count += 1

                elif result == "skipped":
                    skipped_count += 1

                # -----------------------------------------
                # Stop after the requested number of
                # matching catalogue tracks.
                # -----------------------------------------
                if (
                    limit is not None
                    and matched_count >= limit
                ):
                    break

            except Exception as error:
                error_count += 1

                self.stderr.write(
                    self.style.ERROR(
                        f"Failed {h5_path}: {error}"
                    )
                )

        # -------------------------------------------------
        # Final summary
        # -------------------------------------------------
        self.stdout.write(
            self.style.SUCCESS(
                "MSD HDF5 enrichment complete. "
                f"Scanned: {scanned_count}, "
                f"matched: {matched_count}, "
                f"enriched: {enriched_count}, "
                f"skipped: {skipped_count}, "
                f"errors: {error_count}."
            )
        )

    # =====================================================
    # PROCESS ONE HDF5 FILE
    # =====================================================
    def process_h5_file(
        self,
        h5_path,
        dry_run=False,
    ):
        """
        Read one MSD HDF5 file and enrich the corresponding
        Track record.

        Returns:

            "matched"
                A matching catalogue track was found and
                enrichment was performed.

            "skipped"
                No matching Track record was found.
        """

        with h5py.File(h5_path, "r") as h5_file:

            # -------------------------------------------------
            # MSD HDF5 groups
            # -------------------------------------------------
            analysis_songs = h5_file["analysis"]["songs"]
            metadata_songs = h5_file["metadata"]["songs"]
            musicbrainz_songs = h5_file["musicbrainz"]["songs"]

            if len(analysis_songs) == 0:
                return "skipped"

            analysis_row = analysis_songs[0]
            metadata_row = metadata_songs[0]
            musicbrainz_row = musicbrainz_songs[0]

            # -------------------------------------------------
            # Track ID is our main catalogue match.
            # -------------------------------------------------
            track_id = self.decode_text(
                analysis_row["track_id"]
            )

            if not track_id:
                return "skipped"

            track = (
                Track.objects
                .select_related("artist")
                .filter(msd_track_id=track_id)
                .first()
            )

            # -------------------------------------------------
            # HDF5 subset contains more tracks than may exist
            # in the current catalogue.
            # -------------------------------------------------
            if not track:
                return "skipped"

            # -------------------------------------------------
            # Extract usable numeric metadata.
            # -------------------------------------------------
            tempo = self.clean_positive_float(
                analysis_row["tempo"]
            )

            loudness = self.clean_float(
                analysis_row["loudness"]
            )

            duration = self.clean_positive_float(
                analysis_row["duration"]
            )

            key = self.clean_key(
                analysis_row["key"]
            )

            mode = self.clean_mode(
                analysis_row["mode"]
            )

            familiarity = self.clean_float(
                metadata_row["artist_familiarity"]
            )

            song_hotness = self.clean_float(
                metadata_row["song_hotttnesss"]
            )

            release_year = self.clean_year(
                musicbrainz_row["year"]
            )

            # -------------------------------------------------
            # Extract and filter weighted artist terms.
            # -------------------------------------------------
            filtered_tags = self.get_filtered_artist_terms(
                h5_file
            )

            # -------------------------------------------------
            # Display useful dry-run information.
            # -------------------------------------------------
            if dry_run:
                self.stdout.write(
                    (
                        f"{track_id} | "
                        f"{track.track_name} | "
                        f"tempo={tempo} | "
                        f"loudness={loudness} | "
                        f"key={key} | "
                        f"mode={mode} | "
                        f"tags={len(filtered_tags)}"
                    )
                )

                return "matched"

            # -------------------------------------------------
            # Save changes atomically.
            # -------------------------------------------------
            with transaction.atomic():

                self.update_track_fields(
                    track=track,
                    tempo=tempo,
                    loudness=loudness,
                    duration=duration,
                    key=key,
                    mode=mode,
                    familiarity=familiarity,
                    song_hotness=song_hotness,
                    release_year=release_year,
                )

                self.update_track_tags(
                    track=track,
                    filtered_tags=filtered_tags,
                )

            return "matched"

    # =====================================================
    # EXTRACT FILTERED ARTIST TERMS
    # =====================================================
    def get_filtered_artist_terms(self, h5_file):
        """
        Read artist_terms and artist_terms_weight from the
        MSD HDF5 metadata group.

        Non-musical descriptors are removed using the
        curated NextTrack term filter.
        """

        metadata_group = h5_file["metadata"]

        raw_terms = metadata_group["artist_terms"][:]
        raw_weights = metadata_group[
            "artist_terms_weight"
        ][:]

        terms = [
            self.decode_text(term)
            for term in raw_terms
        ]

        weights = [
            self.clean_float(weight)
            for weight in raw_weights
        ]

        return filter_artist_terms(
            terms,
            weights,
        )

    # =====================================================
    # UPDATE TRACK FIELDS
    # =====================================================
    def update_track_fields(
        self,
        track,
        tempo,
        loudness,
        duration,
        key,
        mode,
        familiarity,
        song_hotness,
        release_year,
    ):
        """
        Update usable HDF5-derived metadata.

        Energy and danceability are intentionally excluded
        because profiling of the MSD subset showed those
        fields contain only zero values.
        """

        changed_fields = []

        # -------------------------------------------------
        # Tempo
        # -------------------------------------------------
        if tempo is not None:
            if track.tempo != tempo:
                track.tempo = tempo
                changed_fields.append("tempo")

        # -------------------------------------------------
        # Loudness
        # -------------------------------------------------
        if loudness is not None:
            if track.loudness != loudness:
                track.loudness = loudness
                changed_fields.append("loudness")

        # -------------------------------------------------
        # Duration
        # -------------------------------------------------
        if duration is not None:
            if track.duration_seconds != duration:
                track.duration_seconds = duration
                changed_fields.append(
                    "duration_seconds"
                )

        # -------------------------------------------------
        # Key
        #
        # Important:
        # key=0 is valid and must not be treated as missing.
        # -------------------------------------------------
        if key is not None:
            if track.key != key:
                track.key = key
                changed_fields.append("key")

        # -------------------------------------------------
        # Mode
        #
        # mode=0 is valid and must not be treated as missing.
        # -------------------------------------------------
        if mode is not None:
            if track.mode != mode:
                track.mode = mode
                changed_fields.append("mode")

        # -------------------------------------------------
        # Artist familiarity
        # -------------------------------------------------
        if familiarity is not None:
            if track.familiarity != familiarity:
                track.familiarity = familiarity
                changed_fields.append(
                    "familiarity"
                )

        # -------------------------------------------------
        # Song popularity / hotness
        #
        # Missing song_hotttnesss values are left unchanged.
        # -------------------------------------------------
        if song_hotness is not None:
            if track.popularity != song_hotness:
                track.popularity = song_hotness
                changed_fields.append(
                    "popularity"
                )

        # -------------------------------------------------
        # Release year
        #
        # Only populate it if the track currently lacks one.
        # This avoids overwriting an existing catalogue value.
        # -------------------------------------------------
        if (
            release_year is not None
            and track.release_year is None
        ):
            track.release_year = release_year
            changed_fields.append(
                "release_year"
            )

        if changed_fields:
            track.save(
                update_fields=changed_fields
            )

    # =====================================================
    # UPDATE WEIGHTED TRACK TAGS
    # =====================================================
    def update_track_tags(
        self,
        track,
        filtered_tags,
    ):
        """
        Store filtered MSD artist terms as weighted TrackTag
        relationships.

        update_or_create() keeps the operation idempotent so
        the command can safely be re-run.
        """

        for item in filtered_tags:

            term = item["term"]
            weight = item["weight"]

            tag, _ = Tag.objects.get_or_create(
                name=term,
                defaults={
                    "category": "genre",
                },
            )

            TrackTag.objects.update_or_create(
                track=track,
                tag=tag,
                defaults={
                    "weight": weight,
                    "source": self.SOURCE_NAME,
                },
            )

    # =====================================================
    # CLEANING HELPERS
    # =====================================================
    @staticmethod
    def decode_text(value):
        """
        Decode bytes values returned by HDF5 into normal
        Python strings.
        """

        if value is None:
            return ""

        if isinstance(value, bytes):
            return value.decode(
                "utf-8",
                errors="ignore"
            ).strip()

        return str(value).strip()

    @staticmethod
    def clean_float(value):
        if value is None:
            return None

        try:
            value = float(value)
        except (TypeError, ValueError):
            return None

        # NaN does not equal itself.
        if value != value:
            return None

        return value

    @classmethod
    def clean_positive_float(cls, value):
        value = cls.clean_float(value)

        if value is None:
            return None

        if value <= 0:
            return None

        return value

    @staticmethod
    def clean_key(value):
        """
        MSD keys range from 0 to 11.

        Zero is a valid musical key value.
        """

        try:
            value = int(value)
        except (TypeError, ValueError):
            return None

        if 0 <= value <= 11:
            return value

        return None

    @staticmethod
    def clean_mode(value):
        """
        MSD mode values:

            0 = minor
            1 = major

        Zero is valid and must not be treated as missing.
        """

        try:
            value = int(value)
        except (TypeError, ValueError):
            return None

        if value in (0, 1):
            return value

        return None

    @staticmethod
    def clean_year(value):
        try:
            value = int(value)
        except (TypeError, ValueError):
            return None

        if value == 0:
            return None

        if 1000 <= value <= 9999:
            return value

        return None