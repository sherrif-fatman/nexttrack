import requests

from django.core.management.base import BaseCommand
from django.db import transaction

from recommendations.models import Album


class Command(BaseCommand):
    help = "Enrich album artwork using the Cover Art Archive."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Maximum number of albums to process.",
        )

        parser.add_argument(
            "--retry-missing",
            action="store_true",
            help="Retry albums that currently have no artwork.",
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Check artwork availability without saving changes.",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        retry_missing = options["retry_missing"]
        dry_run = options["dry_run"]

        albums = Album.objects.exclude(
            musicbrainz_release_id__isnull=True,
        ).exclude(
            musicbrainz_release_id=""
        )

        if not retry_missing:
            albums = albums.filter(cover_image_url="")

        if limit:
            albums = albums[:limit]

        processed = 0
        enriched = 0
        missing = 0
        errors = 0

        for album in albums:
            processed += 1

            try:
                artwork = self.find_artwork(album)

                if not artwork:
                    missing += 1

                    self.stdout.write(
                        self.style.WARNING(
                            f"No artwork: {album.album_name} "
                            f"— {album.artist.artist_name}"
                        )
                    )
                    continue

                if dry_run:
                    enriched += 1

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Would enrich: {album.album_name}"
                        )
                    )
                    continue

                with transaction.atomic():
                    album.cover_image_url = artwork["image"]
                    album.cover_thumbnail_url = artwork["thumbnail"]

                    album.save(
                        update_fields=[
                            "cover_image_url",
                            "cover_thumbnail_url",
                        ]
                    )

                enriched += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Enriched: {album.album_name}"
                    )
                )

            except Exception as exc:
                errors += 1

                self.stdout.write(
                    self.style.ERROR(
                        f"Error: {album.album_name} "
                        f"— {album.artist.artist_name}: {exc}"
                    )
                )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Artwork enrichment complete. "
                f"Processed: {processed}, "
                f"enriched: {enriched}, "
                f"missing: {missing}, "
                f"errors: {errors}."
            )
        )

    def find_artwork(self, album):
        """
        Try the MusicBrainz release first.
        Fall back to the release group if one is available.
        """

        if album.musicbrainz_release_id:
            artwork = self.fetch_artwork(
                "release",
                album.musicbrainz_release_id,
            )

            if artwork:
                return artwork

        if album.musicbrainz_release_group_id:
            artwork = self.fetch_artwork(
                "release-group",
                album.musicbrainz_release_group_id,
            )

            if artwork:
                return artwork

        return None

    def fetch_artwork(self, entity_type, mbid):
        url = (
            "https://coverartarchive.org/"
            f"{entity_type}/{mbid}"
        )

        response = requests.get(
            url,
            timeout=10,
            headers={
                "User-Agent": (
                    "NextTrack/1.0 "
                    "(University recommendation prototype)"
                )
            },
        )

        if response.status_code == 404:
            return None

        response.raise_for_status()

        data = response.json()

        images = data.get("images", [])

        if not images:
            return None

        # Prefer artwork explicitly marked as the front cover.
        front_images = [
            image
            for image in images
            if image.get("front") is True
        ]

        selected = front_images[0] if front_images else images[0]

        image_url = selected.get("image")

        thumbnails = selected.get("thumbnails", {})

        thumbnail_url = (
            thumbnails.get("500")
            or thumbnails.get("250")
            or thumbnails.get("small")
            or image_url
        )

        if not image_url:
            return None

        return {
            "image": image_url,
            "thumbnail": thumbnail_url,
        }