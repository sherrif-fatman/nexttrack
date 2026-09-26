"""
Offline evaluation command for the NextTrack recommendation engine.

This command compares the final deployed heuristic weighting against an
equal-weight baseline and a series of leave-one-feature-out ablation
configurations. In each ablation condition, one similarity component is
removed and the remaining final-system weights are renormalised to sum to
1.0. The experiment measures how sensitive the Top-20 recommendation set is
to the weighting scheme and to each component.

The evaluation design was informed by recommender-system evaluation literature
that distinguishes offline comparative evaluation from user studies and
emphasises careful baseline comparison:

- Shani, G. and Gunawardana, A. (2011), "Evaluating Recommendation Systems",
  in Recommender Systems Handbook, Springer.
- Rendle, S., Zhang, L. and Koren, Y. (2019), "On the Difficulty of Evaluating
  Baselines: A Study on Recommender Systems", arXiv:1905.01395.

These references motivate comparative offline evaluation and careful baseline
use; they are not presented as the source of NextTrack's exact custom
leave-one-component-out procedure or its chosen weights.

The final configuration is treated as the reference condition. Top-20 overlap
is a ranking-sensitivity measure: it shows how much the recommendation set
changes under another configuration. It does not establish that one
configuration is more relevant or accurate than another.

The three illustrative seed tracks are controlled case examples used for
sanity checking and explanation. The main ablation analysis uses the frozen
session contexts from the completed participant evaluation.

Explicit user refinement boosts are deliberately excluded from this offline
ablation so that the four base similarity components can be compared under
controlled weighting conditions.

This command is intended for evaluation only. It does not modify recommendation
results or other database records.
"""

import csv
from pathlib import Path

from django.core.management.base import BaseCommand
from recommendations.models import Track

from recommendations.services.similarity import (
    calculate_tag_similarity,
    calculate_tempo_similarity,
    calculate_loudness_similarity,
    calculate_key_mode_similarity,
)

from recommendations.services.recommender import _get_track_tags


EXPERIMENT_CONFIGURATIONS = {
    "final": {
        "tags": 0.50,
        "tempo": 0.20,
        "loudness": 0.20,
        "key_mode": 0.10,
    },
    "equal_weight": {
        "tags": 0.25,
        "tempo": 0.25,
        "loudness": 0.25,
        "key_mode": 0.25,
    },
    "no_tags": {
        "tags": 0.00,
        "tempo": 0.40,
        "loudness": 0.40,
        "key_mode": 0.20,
    },
    "no_tempo": {
        "tags": 0.625,
        "tempo": 0.00,
        "loudness": 0.25,
        "key_mode": 0.125,
    },
    "no_loudness": {
        "tags": 0.625,
        "tempo": 0.25,
        "loudness": 0.00,
        "key_mode": 0.125,
    },
    "no_key_mode": {
        "tags": 5 / 9,
        "tempo": 2 / 9,
        "loudness": 2 / 9,
        "key_mode": 0.00,
    },
}

ILLUSTRATIVE_SEEDS = [
    {
        "id": 4488,
        "artist": "John Mayer",
        "track": "Something's Missing",
    },

    {
        "id": 6451,
        "artist": "Taylor Swift",
        "track": "Should've Said No",
    },

    {
        "id": 18,
        "artist": "Linkin Park",
        "track": "Crawling (Album Version)",
    },
]


class Command(BaseCommand):
    help = (
        "Run offline baseline and ablation evaluation "
        "for the NextTrack recommender."
    )

    def _validate_configurations(self):
        """
        Confirm that every experimental weighting configuration
        totals 1.0.
        """

        for name, weights in EXPERIMENT_CONFIGURATIONS.items():
            total = sum(weights.values())

            if abs(total - 1.0) > 0.000001:
                raise ValueError(
                    f"Configuration '{name}' has invalid "
                    f"weight total: {total}"
                )

    def _calculate_experimental_score(self, component_scores, weights):
        """
        Combine similarity components using the supplied
        experimental weighting configuration.
        """

        return (
            component_scores["tags"] * weights["tags"]
            + component_scores["tempo"] * weights["tempo"]
            + component_scores["loudness"] * weights["loudness"]
            + component_scores["key_mode"] * weights["key_mode"]
        )

    def _load_illustrative_seeds(self):
        """
        Load and verify the controlled illustrative seed tracks.
        """

        seed_tracks = []

        for seed in ILLUSTRATIVE_SEEDS:
            track = (
                Track.objects
                .select_related("artist")
                .prefetch_related("track_tags__tag")
                .get(id=seed["id"])
            )

            if (
                track.track_name != seed["track"]
                or track.artist.artist_name != seed["artist"]
            ):
                raise ValueError(
                    f"Seed track ID {seed['id']} does not match "
                    f"{seed['artist']} - {seed['track']}."
                )

            seed_tracks.append(track)

        return seed_tracks

    def _calculate_components(self, source_track, candidate_track):
        """
        Calculate the four raw similarity components between
        a source track and a candidate track.

        No experimental weighting is applied here.
        """

        source_tags = _get_track_tags(source_track)
        candidate_tags = _get_track_tags(candidate_track)

        return {
            "tags": calculate_tag_similarity(
                source_tags,
                candidate_tags,
            ),
            "tempo": calculate_tempo_similarity(
                source_track.tempo,
                candidate_track.tempo,
            ),
            "loudness": calculate_loudness_similarity(
                source_track.loudness,
                candidate_track.loudness,
            ),
            "key_mode": calculate_key_mode_similarity(
                source_track.key,
                source_track.mode,
                candidate_track.key,
                candidate_track.mode,
            ),
        }

    def _rank_candidates(self, source_track, weights, limit=10):
        """
        Rank catalogue candidates for a single illustrative seed
        using the supplied experimental weights.
        """

        candidates = (
            Track.objects
            .exclude(id=source_track.id)
            .exclude(artist_id=source_track.artist_id)
            .select_related(
                "artist",
                "album",
            )
            .prefetch_related(
                "track_tags__tag",
            )
        )

        scored_candidates = []

        for candidate in candidates:
            components = self._calculate_components(
                source_track,
                candidate,
            )

            score = self._calculate_experimental_score(
                components,
                weights,
            )

            scored_candidates.append({
                "track": candidate,
                "score": score,
                "components": components,
            })

        scored_candidates.sort(
            key=lambda item: item["score"],
            reverse=True,
        )

        return scored_candidates[:limit]

    def _calculate_overlap(self, reference_results, comparison_results):
        """
        Calculate the number and proportion of tracks shared
        between two ranked result lists.
        """

        reference_ids = {
            result["track"].id
            for result in reference_results
        }

        comparison_ids = {
            result["track"].id
            for result in comparison_results
        }

        shared_ids = reference_ids & comparison_ids

        return {
            "shared_count": len(shared_ids),
            "total": len(reference_ids),
            "percentage": (
                len(shared_ids) / len(reference_ids) * 100
                if reference_ids
                else 0.0
            ),
        }

    def _load_participant_session_rows(self):
        """
        Load the frozen production session-track export used for
        offline evaluation.
        """

        csv_path = (
            Path("/app/evaluation_data")
            / "nexttrack_evaluation_session_tracks.csv"
        )

        with csv_path.open(
            mode="r",
            encoding="utf-8-sig",
            newline="",
        ) as csv_file:
            reader = csv.DictReader(csv_file)
            rows = list(reader)

        session_ids = {
            row["session_id"]
            for row in rows
        }

        return rows, session_ids

    def _validate_participant_track_ids(self, participant_rows):
        """
        Confirm that every track referenced by the frozen production
        evaluation export exists in the local catalogue.
        """

        track_ids = {
            int(row["track_id"])
            for row in participant_rows
        }

        existing_track_ids = set(
            Track.objects
            .filter(id__in=track_ids)
            .values_list("id", flat=True)
        )

        missing_track_ids = track_ids - existing_track_ids

        if missing_track_ids:
            raise ValueError(
                "Participant evaluation tracks are missing from the "
                f"local catalogue: {sorted(missing_track_ids)}"
            )

        return track_ids

    def _build_participant_sessions(self, participant_rows):
        """
        Reconstruct participant session contexts from the frozen
        production session-track export.
        """

        sessions = {}

        for row in participant_rows:
            session_id = row["session_id"]

            if session_id not in sessions:
                sessions[session_id] = []

            sessions[session_id].append(row)

        participant_sessions = {}

        for session_id, rows in sessions.items():
            rows.sort(
                key=lambda row: int(row["position"])
            )

            track_ids = [
                int(row["track_id"])
                for row in rows
            ]

            tracks_by_id = {
                track.id: track
                for track in (
                    Track.objects
                    .filter(id__in=track_ids)
                    .select_related("artist")
                    .prefetch_related("track_tags__tag")
                )
            }

            participant_sessions[session_id] = [
                tracks_by_id[track_id]
                for track_id in track_ids
            ]

        return participant_sessions

    def _calculate_session_components(
        self,
        source_tracks,
        candidate_track,
    ):
        """
        Calculate mean component similarities between a candidate
        and all tracks in a participant session context.
        """

        comparisons = [
            self._calculate_components(
                source_track,
                candidate_track,
            )
            for source_track in source_tracks
        ]

        comparison_count = len(comparisons)

        return {
            "tags": sum(
                item["tags"] for item in comparisons
            ) / comparison_count,
            "tempo": sum(
                item["tempo"] for item in comparisons
            ) / comparison_count,
            "loudness": sum(
                item["loudness"] for item in comparisons
            ) / comparison_count,
            "key_mode": sum(
                item["key_mode"] for item in comparisons
            ) / comparison_count,
        }

    def _rank_session_candidates(
        self,
        source_tracks,
        weights,
        limit=20,
    ):
        """
        Rank catalogue candidates for a multi-track session context
        using the supplied experimental weights.
        """

        source_track_ids = {
            track.id
            for track in source_tracks
        }

        source_artist_ids = {
            track.artist_id
            for track in source_tracks
        }

        candidates = (
            Track.objects
            .exclude(id__in=source_track_ids)
            .exclude(artist_id__in=source_artist_ids)
            .select_related(
                "artist",
                "album",
            )
            .prefetch_related(
                "track_tags__tag",
            )
        )

        scored_candidates = []

        for candidate in candidates:
            components = self._calculate_session_components(
                source_tracks,
                candidate,
            )

            score = self._calculate_experimental_score(
                components,
                weights,
            )

            scored_candidates.append({
                "track": candidate,
                "score": score,
                "components": components,
            })

        scored_candidates.sort(
            key=lambda item: item["score"],
            reverse=True,
        )

        return scored_candidates[:limit]

    def _calculate_session_candidate_components(
        self,
        source_tracks,
    ):
        """
        Calculate candidate component similarities once for a session
        so that all experimental configurations use identical inputs.
        """

        source_track_ids = {
            track.id
            for track in source_tracks
        }

        source_artist_ids = {
            track.artist_id
            for track in source_tracks
        }

        candidates = (
            Track.objects
            .exclude(id__in=source_track_ids)
            .exclude(artist_id__in=source_artist_ids)
            .select_related(
                "artist",
                "album",
            )
            .prefetch_related(
                "track_tags__tag",
            )
        )

        candidate_components = []

        for candidate in candidates:
            components = self._calculate_session_components(
                source_tracks,
                candidate,
            )

            candidate_components.append({
                "track": candidate,
                "components": components,
            })

        return candidate_components


    def _rank_cached_candidates(
        self,
        candidate_components,
        weights,
        limit=20,
    ):
        """
        Rank pre-calculated candidate components using the supplied
        experimental weighting configuration.
        """

        scored_candidates = []

        for item in candidate_components:
            score = self._calculate_experimental_score(
                item["components"],
                weights,
            )

            scored_candidates.append({
                "track": item["track"],
                "score": score,
                "components": item["components"],
            })

        scored_candidates.sort(
            key=lambda item: item["score"],
            reverse=True,
        )

        return scored_candidates[:limit]


    def handle(self, *args, **options):
        # Validate the experimental definitions before doing any expensive work.
        self._validate_configurations()

        # Load the frozen participant session-track export and reconstruct the
        # temporary session contexts that were actually used during evaluation.
        participant_rows, participant_session_ids = (
            self._load_participant_session_rows()
        )
        participant_track_ids = self._validate_participant_track_ids(
            participant_rows
        )
        participant_sessions = self._build_participant_sessions(
            participant_rows
        )

        session_sizes = [
            len(tracks)
            for tracks in participant_sessions.values()
        ]

        self.stdout.write(
            f"Reconstructed {len(participant_sessions)} participant "
            f"session contexts."
        )
        self.stdout.write(
            f"Participant session sizes: "
            f"min={min(session_sizes)}, "
            f"max={max(session_sizes)}, "
            f"total={sum(session_sizes)}."
        )
        self.stdout.write(
            f"Loaded {len(participant_rows)} selected tracks "
            f"across {len(participant_session_ids)} participant sessions."
        )
        self.stdout.write(
            f"Validated {len(participant_track_ids)} unique participant "
            f"track IDs against the local catalogue."
        )

        # Load the three controlled examples used for transparent sanity checks.
        seed_tracks = self._load_illustrative_seeds()

        self.stdout.write(
            self.style.SUCCESS(
                "NextTrack recommender evaluation command ready."
            )
        )
        self.stdout.write("\nIllustrative seed tracks:")

        for track in seed_tracks:
            self.stdout.write(
                f"  {track.id}: "
                f"{track.artist.artist_name} - "
                f"{track.track_name}"
            )

        # Sanity check the final weighting against a known development example.
        john_mayer = seed_tracks[0]
        self.stdout.write(
            "\nJohn Mayer sanity check - final weighting:"
        )

        results = self._rank_candidates(
            john_mayer,
            EXPERIMENT_CONFIGURATIONS["final"],
            limit=20,
        )

        for position, result in enumerate(results, start=1):
            track = result["track"]
            self.stdout.write(
                f"  {position:>2}. "
                f"{track.artist.artist_name} - "
                f"{track.track_name} "
                f"({result['score']:.4f})"
            )

        # Compare the same seed against a simple equal-weight baseline.
        self.stdout.write(
            "\nJohn Mayer comparison - equal-weight baseline:"
        )
        baseline_results = self._rank_candidates(
            john_mayer,
            EXPERIMENT_CONFIGURATIONS["equal_weight"],
            limit=20,
        )

        for position, result in enumerate(baseline_results, start=1):
            track = result["track"]
            self.stdout.write(
                f"  {position:>2}. "
                f"{track.artist.artist_name} - "
                f"{track.track_name} "
                f"({result['score']:.4f})"
            )

        overlap = self._calculate_overlap(
            results,
            baseline_results,
        )
        self.stdout.write("\nJohn Mayer Top-20 overlap:")
        self.stdout.write(
            f"  Shared tracks: "
            f"{overlap['shared_count']}/{overlap['total']} "
            f"({overlap['percentage']:.1f}%)"
        )

        # Use the same five comparison conditions throughout the experiment.
        comparison_names = [
            "equal_weight",
            "no_tags",
            "no_tempo",
            "no_loudness",
            "no_key_mode",
        ]

        # Run the alternatives over all three illustrative seed examples.
        self.stdout.write(
            "\nFinal configuration comparison for all illustrative seeds:"
        )

        for seed_track in seed_tracks:
            final_results = self._rank_candidates(
                seed_track,
                EXPERIMENT_CONFIGURATIONS["final"],
                limit=20,
            )
            self.stdout.write(
                f"\n  {seed_track.artist.artist_name} - "
                f"{seed_track.track_name}"
            )

            for configuration_name in comparison_names:
                comparison_results = self._rank_candidates(
                    seed_track,
                    EXPERIMENT_CONFIGURATIONS[configuration_name],
                    limit=20,
                )
                overlap = self._calculate_overlap(
                    final_results,
                    comparison_results,
                )
                self.stdout.write(
                    f"    {configuration_name:<12} "
                    f"{overlap['shared_count']}/{overlap['total']} "
                    f"({overlap['percentage']:.1f}%)"
                )

        # Validate that the multi-track session path reduces exactly to the
        # single-track path when the session contains one selected track.
        single_track_session = next(
            tracks
            for tracks in participant_sessions.values()
            if len(tracks) == 1
        )
        single_source_track = single_track_session[0]

        single_seed_results = self._rank_candidates(
            single_source_track,
            EXPERIMENT_CONFIGURATIONS["final"],
            limit=20,
        )
        single_session_results = self._rank_session_candidates(
            single_track_session,
            EXPERIMENT_CONFIGURATIONS["final"],
            limit=20,
        )
        single_session_overlap = self._calculate_overlap(
            single_seed_results,
            single_session_results,
        )

        same_order = [
            result["track"].id
            for result in single_seed_results
        ] == [
            result["track"].id
            for result in single_session_results
        ]

        self.stdout.write("\nSingle-track session validation:")
        self.stdout.write(
            f"  Seed: {single_source_track.artist.artist_name} - "
            f"{single_source_track.track_name}"
        )
        self.stdout.write(
            f"  Top-20 overlap: "
            f"{single_session_overlap['shared_count']}/"
            f"{single_session_overlap['total']} "
            f"({single_session_overlap['percentage']:.1f}%)"
        )
        self.stdout.write(
            f"  Identical ranking order: {same_order}"
        )

        # Validate the cached implementation before using it for the full
        # participant-session experiment. Caching changes efficiency only.
        cached_components = self._calculate_session_candidate_components(
            single_track_session
        )
        cached_results = self._rank_cached_candidates(
            cached_components,
            EXPERIMENT_CONFIGURATIONS["final"],
            limit=20,
        )
        cached_overlap = self._calculate_overlap(
            single_session_results,
            cached_results,
        )

        cached_same_order = [
            result["track"].id
            for result in single_session_results
        ] == [
            result["track"].id
            for result in cached_results
        ]

        self.stdout.write("\nCached-ranking validation:")
        self.stdout.write(
            f"  Top-20 overlap: "
            f"{cached_overlap['shared_count']}/"
            f"{cached_overlap['total']} "
            f"({cached_overlap['percentage']:.1f}%)"
        )
        self.stdout.write(
            f"  Identical ranking order: {cached_same_order}"
        )

        # Main ablation experiment. Component similarities are calculated once
        # per participant session and reused across all weighting configurations.
        participant_overlaps = {
            name: []
            for name in comparison_names
        }
        participant_session_results = []

        self.stdout.write(
            "\nParticipant-session Top-20 comparison:"
        )

        for session_id, source_tracks in participant_sessions.items():
            candidate_components = (
                self._calculate_session_candidate_components(
                    source_tracks
                )
            )
            final_results = self._rank_cached_candidates(
                candidate_components,
                EXPERIMENT_CONFIGURATIONS["final"],
                limit=20,
            )

            # Artist count is a simple Top-20 diversity indicator. It measures
            # artist variety, not overall recommendation quality.
            final_unique_artists = len({
                result["track"].artist_id
                for result in final_results
            })

            for configuration_name in comparison_names:
                comparison_results = self._rank_cached_candidates(
                    candidate_components,
                    EXPERIMENT_CONFIGURATIONS[configuration_name],
                    limit=20,
                )
                comparison_unique_artists = len({
                    result["track"].artist_id
                    for result in comparison_results
                })
                overlap = self._calculate_overlap(
                    final_results,
                    comparison_results,
                )

                participant_overlaps[configuration_name].append(
                    overlap["percentage"]
                )

                participant_session_results.append({
                    "session_id": session_id,
                    "session_size": len(source_tracks),
                    "configuration": configuration_name,
                    "top_20_shared": overlap["shared_count"],
                    "top_20_overlap_percentage": round(
                        overlap["percentage"],
                        1,
                    ),
                    "final_unique_artists_top_20": final_unique_artists,
                    "comparison_unique_artists_top_20": (
                        comparison_unique_artists
                    ),
                })

        self.stdout.write(
            f"  Sessions evaluated: {len(participant_sessions)}"
        )

        for configuration_name in comparison_names:
            percentages = participant_overlaps[
                configuration_name
            ]
            mean_percentage = (
                sum(percentages) / len(percentages)
            )
            self.stdout.write(
                f"  {configuration_name:<12} "
                f"mean overlap: {mean_percentage:.1f}%"
            )

        # Preserve per-session observations for descriptive statistics and
        # report tables. With 23 sessions and 5 comparisons this is 115 rows.
        output_path = (
            Path("/app/evaluation_data")
            / "participant_session_ablation_results.csv"
        )

        with output_path.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as csv_file:
            fieldnames = [
                "session_id",
                "session_size",
                "configuration",
                "top_20_shared",
                "top_20_overlap_percentage",
                "final_unique_artists_top_20",
                "comparison_unique_artists_top_20",
            ]
            writer = csv.DictWriter(
                csv_file,
                fieldnames=fieldnames,
            )
            writer.writeheader()
            writer.writerows(participant_session_results)

        self.stdout.write(
            f"\nSaved participant-session results to: "
            f"{output_path}"
        )
        self.stdout.write(
            f"Rows written: "
            f"{len(participant_session_results)}"
        )