import time
import requests

from django.core.management.base import BaseCommand

from recommendations.models import Album


MUSICBRAINZ_SEARCH_URL = "https://musicbrainz.org/ws/2/release/"


class Command(BaseCommand):
    help = "Match NextTrack albums to MusicBrainz releases."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Maximum number of albums to process.",
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show matches without saving them.",
        )

        parser.add_argument(
            "--delay",
            type=float,
            default=1.1,
            help="Delay between MusicBrainz requests in seconds.",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        dry_run = options["dry_run"]
        delay = options["delay"]

        albums = (
            Album.objects
            .select_related("artist")
            .filter(musicbrainz_release_id__isnull=True)
            .order_by("id")
        )

        if limit:
            albums = albums[:limit]

        processed = 0
        matched = 0
        unmatched = 0
        errors = 0

        for album in albums:
            processed += 1

            try:
                result = self.find_musicbrainz_match(album)

                if not result:
                    unmatched += 1

                    self.stdout.write(
                        self.style.WARNING(
                            f"No confident match: "
                            f"{album.album_name} — "
                            f"{album.artist.artist_name}"
                        )
                    )

                    time.sleep(delay)
                    continue

                release_id = result["release_id"]
                release_group_id = result.get("release_group_id")
                score = result.get("score")

                if dry_run:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Would match: "
                            f"{album.album_name} — "
                            f"{album.artist.artist_name} "
                            f"=> {release_id} "
                            f"(score {score})"
                        )
                    )
                else:
                    album.musicbrainz_release_id = release_id
                    album.musicbrainz_release_group_id = release_group_id

                    album.save(
                        update_fields=[
                            "musicbrainz_release_id",
                            "musicbrainz_release_group_id",
                        ]
                    )

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Matched: "
                            f"{album.album_name} — "
                            f"{album.artist.artist_name}"
                        )
                    )

                matched += 1

            except Exception as exc:
                errors += 1

                self.stdout.write(
                    self.style.ERROR(
                        f"Error: {album.album_name} — "
                        f"{album.artist.artist_name}: {exc}"
                    )
                )

            time.sleep(delay)

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "MusicBrainz album matching complete. "
                f"Processed: {processed}, "
                f"matched: {matched}, "
                f"unmatched: {unmatched}, "
                f"errors: {errors}."
            )
        )

    def find_musicbrainz_match(self, album):
        artist = album.artist

        album_name = album.album_name.strip()
        artist_name = artist.artist_name.strip()

        if artist.musicbrainz_artist_id:
            query = (
                f'release:"{album_name}" '
                f'arid:{artist.musicbrainz_artist_id}'
            )
        else:
            query = (
                f'release:"{album_name}" '
                f'artist:"{artist_name}"'
            )

        for attempt in range(3):
            try:
                response = requests.get(
                    MUSICBRAINZ_SEARCH_URL,
                    params={
                        "query": query,
                        "fmt": "json",
                        "limit": 5,
                    },
                    headers={
                        "User-Agent": (
                            "NextTrack/1.0 "
                            "(University recommendation prototype)"
                        )
                    },
                    timeout=30,
                )

                response.raise_for_status()
                break

            except requests.RequestException:
                if attempt == 2:
                    raise

                time.sleep(2 * (attempt + 1))

        data = response.json()

        releases = data.get("releases", [])

        if not releases:
            return None

        best = self.choose_best_match(
            album_name,
            artist_name,
            releases,
        )

        return best

    def choose_best_match(
        self,
        album_name,
        artist_name,
        releases,
    ):
        for release in releases:
            score = int(release.get("score", 0))

            # Keep matching conservative.
            if score < 90:
                continue

            release_title = (
                release.get("title") or ""
            ).strip()

            if release_title.casefold() != album_name.casefold():
                continue

            artist_credit = release.get(
                "artist-credit",
                []
            )

            credit_names = []

            for credit in artist_credit:
                artist = credit.get("artist", {})
                name = artist.get("name")

                if name:
                    credit_names.append(name.casefold())

            if (
                credit_names
                and artist_name.casefold()
                not in credit_names
            ):
                continue

            release_group = release.get(
                "release-group",
                {}
            )

            return {
                "release_id": release.get("id"),
                "release_group_id": release_group.get("id"),
                "score": score,
            }

        return None