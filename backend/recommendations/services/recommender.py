
"""
recommender.py

Contains the main NextTrack recommendation engine.

Recommendations are generated from the tracks the user has selected
during the current session.

Each candidate track is compared against every track already in the
session. The similarity scores are then averaged to create a single
session-based recommendation score.

This allows recommendations to become more representative of the
current session as additional tracks are added, without relying on a
persistent user profile.
"""


from recommendations.models import Track, RecommendationResult

from recommendations.services.similarity import (
    calculate_tag_similarity,
    calculate_tempo_similarity,
    calculate_loudness_similarity,
    calculate_key_mode_similarity,
    calculate_combined_similarity,
)

from recommendations.services.tag_filter import is_musical_term


def _get_track_tags(track):
    """
    Return the usable weighted musical tags for a track.

    TrackTag records are converted into the format expected by
    calculate_tag_similarity():

        [
            {"term": "rock", "weight": 1.0},
            {"term": "alternative rock", "weight": 0.85}
        ]

    The tag filter is applied again here as a safeguard so that
    non-musical descriptors do not influence recommendation scores.
    """

    filtered_tags = []

    # ------------------------------------------------------------
    # track.track_tags accesses the TrackTag relationship.
    #
    # The related Tag object contains the tag name and TrackTag
    # contains the MSD weight.
    # ------------------------------------------------------------
    for track_tag in track.track_tags.all():

        tag_name = track_tag.tag.name

        # Ignore terms that are not part of NextTrack's curated
        # musical vocabulary.
        if not is_musical_term(tag_name):
            continue

        filtered_tags.append({
            "term": tag_name.lower().strip(),
            "weight": float(track_tag.weight),
        })

    return filtered_tags


def _compare_tracks(source_track, candidate_track):
    """
    Compare two tracks using all available similarity functions.

    Returns both the final weighted similarity score and the
    individual component scores.

    Keeping the individual scores allows the recommender to generate
    explanations for why a track was recommended.
    """

    # Get filtered weighted tag profiles for both tracks.
    source_tags = _get_track_tags(source_track)
    candidate_tags = _get_track_tags(candidate_track)

    # ------------------------------------------------------------
    # Calculate each individual similarity component.
    # ------------------------------------------------------------
    tag_similarity = calculate_tag_similarity(
        source_tags,
        candidate_tags,
    )

    tempo_similarity = calculate_tempo_similarity(
        source_track.tempo,
        candidate_track.tempo,
    )

    loudness_similarity = calculate_loudness_similarity(
        source_track.loudness,
        candidate_track.loudness,
    )

    key_mode_similarity = calculate_key_mode_similarity(
        source_track.key,
        source_track.mode,
        candidate_track.key,
        candidate_track.mode,
    )

    # ------------------------------------------------------------
    # Combine the individual similarity values using the weighting
    # defined in similarity.py.
    # ------------------------------------------------------------
    combined_similarity = calculate_combined_similarity(
        tag_similarity=tag_similarity,
        tempo_similarity=tempo_similarity,
        loudness_similarity=loudness_similarity,
        key_mode_similarity=key_mode_similarity,
    )

    return {
        "combined": combined_similarity,
        "tags": tag_similarity,
        "tempo": tempo_similarity,
        "loudness": loudness_similarity,
        "key_mode": key_mode_similarity,
    }


def _average_scores(comparisons):
    """
    Average similarity values across every track in the session.

    Example:

        Candidate vs session track 1 = 0.80
        Candidate vs session track 2 = 0.60

        Session similarity = 0.70

    The same averaging is also performed for each individual
    similarity component so explanations can describe the candidate's
    overall relationship to the session.
    """

    if not comparisons:
        return {
            "combined": 0.0,
            "tags": 0.0,
            "tempo": 0.0,
            "loudness": 0.0,
            "key_mode": 0.0,
        }

    comparison_count = len(comparisons)

    return {
        "combined": sum(
            item["combined"]
            for item in comparisons
        ) / comparison_count,

        "tags": sum(
            item["tags"]
            for item in comparisons
        ) / comparison_count,

        "tempo": sum(
            item["tempo"]
            for item in comparisons
        ) / comparison_count,

        "loudness": sum(
            item["loudness"]
            for item in comparisons
        ) / comparison_count,

        "key_mode": sum(
            item["key_mode"]
            for item in comparisons
        ) / comparison_count,
    }


def _build_reason(average_scores):
    """
    Build a human-readable explanation for a recommendation.

    The explanation is based directly on the same similarity values
    used to calculate the recommendation score.

    This keeps the recommendation process transparent and
    explainable.
    """

    reasons = []

    # Musical style / tag similarity.
    if average_scores["tags"] >= 0.70:
        reasons.append("strong musical style match")

    elif average_scores["tags"] >= 0.40:
        reasons.append("similar musical style")

    # Tempo similarity.
    if average_scores["tempo"] >= 0.80:
        reasons.append("closely matched tempo")

    elif average_scores["tempo"] >= 0.60:
        reasons.append("similar tempo")

    # Loudness similarity.
    if average_scores["loudness"] >= 0.80:
        reasons.append("closely matched loudness")

    elif average_scores["loudness"] >= 0.60:
        reasons.append("similar loudness")

    # Key and mode play a smaller role, so only mention them when
    # there is a reasonably strong match.
    if average_scores["key_mode"] >= 0.75:
        reasons.append("compatible key and mode")

    # If none of the components pass the explanation thresholds,
    # still provide a useful fallback explanation.
    if not reasons:
        return "best overall match for the current session"

    return ", ".join(reasons)


def recommend_track_for_session(session, limit=20):
    """
    Generate ranked recommendations for a session.

    Each candidate track is compared against every user-selected
    track currently stored in the session.

    The candidate's individual comparison scores are averaged,
    producing a recommendation score representing how well the
    candidate fits the session as a whole.

    Tracks already selected by the user are excluded from the
    recommendation candidates.
    """

    # ------------------------------------------------------------
    # Load all tracks selected during this session.
    #
    # select_related() and prefetch_related() reduce unnecessary
    # database queries when accessing artists and weighted tags.
    # ------------------------------------------------------------
    session_entries = (
        session.session_tracks
        .select_related(
            "track",
            "track__artist",
            "track__album",
        )
        .prefetch_related(
            "track__track_tags__tag",
        )
        .order_by("position")
    )

    session_tracks = [
        entry.track
        for entry in session_entries
    ]

    # ------------------------------------------------------------
    # A recommendation cannot be generated without at least one
    # user-selected track.
    # ------------------------------------------------------------
    if not session_tracks:
        return []

    # Get IDs of tracks already selected during the session.
    session_track_ids = [
        track.id
        for track in session_tracks
    ]

    # ------------------------------------------------------------
    # Load candidate tracks.
    #
    # Tracks already selected by the user are excluded.
    #
    # Weighted tags are prefetched because they will be used
    # repeatedly during similarity calculations.
    # ------------------------------------------------------------
    candidate_tracks = (
        Track.objects
        .exclude(
            id__in=session_track_ids
        )
        .select_related(
            "artist",
            "album",
            "genre",
        )
        .prefetch_related(
            "track_tags__tag",
        )
    )

    scored_tracks = []

    # ------------------------------------------------------------
    # Compare every candidate against every track in the session.
    # ------------------------------------------------------------
    for candidate_track in candidate_tracks:

        comparisons = []

        for source_track in session_tracks:

            comparison = _compare_tracks(
                source_track,
                candidate_track,
            )

            comparisons.append(comparison)

        # --------------------------------------------------------
        # Average the candidate's scores across the whole session.
        # --------------------------------------------------------
        average_scores = _average_scores(
            comparisons
        )

        # Build an explanation from the averaged component scores.
        reason = _build_reason(
            average_scores
        )

        scored_tracks.append({
            "track": candidate_track,
            "score": average_scores["combined"],
            "reason": reason,

            # Keep component scores available for debugging and
            # evaluation even though RecommendationResult currently
            # stores only the combined score and explanation.
            "components": {
                "tags": average_scores["tags"],
                "tempo": average_scores["tempo"],
                "loudness": average_scores["loudness"],
                "key_mode": average_scores["key_mode"],
            },
        })

    # ------------------------------------------------------------
    # Return an empty list if there are no candidate tracks.
    # ------------------------------------------------------------
    if not scored_tracks:
        return []

    # ------------------------------------------------------------
    # Sort candidates by overall session similarity.
    #
    # Highest-scoring tracks appear first.
    # ------------------------------------------------------------
    scored_tracks.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    # Limit the number of recommendations returned.
    top_results = scored_tracks[:limit]

    # ------------------------------------------------------------
    # Recommendations are recalculated whenever the session context
    # changes.
    #
    # Remove the previous ranking for this session before storing the
    # newly calculated results.
    # ------------------------------------------------------------
    session.recommendation_results.all().delete()

    # Store the current ranked recommendation results.
    for item in top_results:

        RecommendationResult.objects.create(
            session=session,
            track=item["track"],
            score=item["score"],
            reason=item["reason"],
        )

    return top_results