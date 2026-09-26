
"""
recommender.py

Contains the main NextTrack recommendation engine.

Recommendations are generated from the tracks the user has selected
during the current session.

Each candidate track is compared against every track already in the
session. The similarity scores are then averaged to create a single
session-based recommendation score.

Optional user-controlled refinements can then influence the ranking
using style, tempo and intensity preferences.

The session context remains the primary recommendation signal.
Refinements provide a smaller secondary influence and do not require
a persistent user profile.
"""


from recommendations.models import Track, RecommendationResult

from recommendations.services.similarity import (
    calculate_tag_similarity,
    calculate_tempo_similarity,
    calculate_loudness_similarity,
    calculate_key_mode_similarity,
    calculate_combined_similarity,
)

from recommendations.services.tag_filter import (
    is_musical_term,
    normalise_term,
)


# =========================================================
# REFINEMENT WEIGHTS
#
# The normal session-based recommendation score remains the
# main influence on ranking.
#
# Optional user refinements can contribute a maximum of 0.18
# to the final score:
#
# Style     = 0.08
# Tempo     = 0.05
# Intensity = 0.05
# =========================================================
STYLE_REFINEMENT_WEIGHT = 0.08
TEMPO_REFINEMENT_WEIGHT = 0.05
INTENSITY_REFINEMENT_WEIGHT = 0.05


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

    for track_tag in track.track_tags.all():

        tag_name = track_tag.tag.name

        if not is_musical_term(tag_name):
            continue

        filtered_tags.append({
            "term": normalise_term(tag_name),
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
    # Combine the normal session similarity values.
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


def _get_session_average_tempo(session_tracks):
    """
    Return the average valid tempo for the current session.

    Invalid, missing or zero tempo values are ignored.
    """

    tempos = [
        float(track.tempo)
        for track in session_tracks
        if track.tempo is not None and float(track.tempo) > 0
    ]

    if not tempos:
        return None

    return sum(tempos) / len(tempos)


def _get_session_average_loudness(session_tracks):
    """
    Return the average valid loudness for the current session.

    Loudness is stored internally in decibels.
    """

    loudness_values = [
        float(track.loudness)
        for track in session_tracks
        if track.loudness is not None
    ]

    if not loudness_values:
        return None

    return sum(loudness_values) / len(loudness_values)


def _calculate_style_preference(candidate_track, style):
    """
    Calculate how strongly a candidate matches the selected style.

    The style control is mapped to NextTrack's curated musical tags
    rather than relying on the sparse MSD genre field.

    Returns a value between 0.0 and 1.0.
    """

    if not style:
        return 0.0

    normalised_style = normalise_term(style)

    if not normalised_style:
        return 0.0

    candidate_tags = _get_track_tags(
        candidate_track
    )

    matching_weights = [
        tag["weight"]
        for tag in candidate_tags
        if tag["term"] == normalised_style
    ]

    if not matching_weights:
        return 0.0

    # TrackTag weights normally fall between 0 and 1.
    # Clamp defensively so the refinement cannot exceed its
    # intended maximum contribution.
    return min(
        max(max(matching_weights), 0.0),
        1.0,
    )


def _calculate_tempo_preference(
    candidate_track,
    session_average_tempo,
    preference,
):
    """
    Calculate the candidate's match to the selected tempo refinement.

    The preference is relative to the current session:

        slower  -> target approximately 20 BPM below session average
        similar -> target session average
        faster  -> target approximately 20 BPM above session average

    This avoids asking users to understand or enter exact BPM values.
    """

    if (
        session_average_tempo is None
        or candidate_track.tempo is None
    ):
        return 0.0

    preference = str(
        preference or ""
    ).lower().strip()

    if preference == "slower":
        target_tempo = max(
            session_average_tempo - 20.0,
            1.0,
        )

    elif preference == "similar":
        target_tempo = session_average_tempo

    elif preference == "faster":
        target_tempo = (
            session_average_tempo + 20.0
        )

    else:
        return 0.0

    return calculate_tempo_similarity(
        target_tempo,
        candidate_track.tempo,
    )


def _calculate_intensity_preference(
    candidate_track,
    session_average_loudness,
    preference,
):
    """
    Calculate the candidate's match to the selected intensity.

    The user-facing term is 'Intensity', but the calculation uses
    the MSD loudness value internally.

        softer   -> target approximately 6 dB below session average
        similar  -> target session average
        stronger -> target approximately 6 dB above session average
    """

    if (
        session_average_loudness is None
        or candidate_track.loudness is None
    ):
        return 0.0

    preference = str(
        preference or ""
    ).lower().strip()

    if preference == "softer":
        target_loudness = (
            session_average_loudness - 6.0
        )

    elif preference == "similar":
        target_loudness = (
            session_average_loudness
        )

    elif preference == "stronger":
        target_loudness = (
            session_average_loudness + 6.0
        )

    else:
        return 0.0

    return calculate_loudness_similarity(
        target_loudness,
        candidate_track.loudness,
    )


def _calculate_refinement(
    candidate_track,
    session_tracks,
    preferences,
):
    """
    Calculate the optional user-controlled refinement contribution.

    The original session similarity remains the main score.

    Refinements can contribute at most 0.18:

        style     0.08
        tempo     0.05
        intensity 0.05

    Returns both the refinement bonus and its component values so
    they remain inspectable for testing and evaluation.
    """

    preferences = preferences or {}

    # Support "style" as the intended API field.
    #
    # "genre" is retained as a backwards-compatible fallback for
    # earlier API requests.
    style = (
        preferences.get("style")
        or preferences.get("genre")
    )

    tempo_preference = preferences.get(
        "tempo"
    )

    intensity_preference = preferences.get(
        "intensity"
    )

    session_average_tempo = (
        _get_session_average_tempo(
            session_tracks
        )
    )

    session_average_loudness = (
        _get_session_average_loudness(
            session_tracks
        )
    )

    style_score = (
        _calculate_style_preference(
            candidate_track,
            style,
        )
    )

    tempo_score = (
        _calculate_tempo_preference(
            candidate_track,
            session_average_tempo,
            tempo_preference,
        )
    )

    intensity_score = (
        _calculate_intensity_preference(
            candidate_track,
            session_average_loudness,
            intensity_preference,
        )
    )

    bonus = (
        style_score
        * STYLE_REFINEMENT_WEIGHT

        + tempo_score
        * TEMPO_REFINEMENT_WEIGHT

        + intensity_score
        * INTENSITY_REFINEMENT_WEIGHT
    )

    return {
        "bonus": bonus,
        "style": style_score,
        "tempo": tempo_score,
        "intensity": intensity_score,
    }


def _build_reason(
    average_scores,
    refinement=None,
    preferences=None,
):
    """
    Build a human-readable explanation for a recommendation.

    The explanation uses both the normal session similarity values
    and any explicit refinements that materially influenced the
    candidate's ranking.
    """

    reasons = []

    preferences = preferences or {}
    refinement = refinement or {}

    # ------------------------------------------------------------
    # Normal session similarity explanation.
    # ------------------------------------------------------------
    if average_scores["tags"] >= 0.70:
        reasons.append(
            "strong musical style match"
        )

    elif average_scores["tags"] >= 0.40:
        reasons.append(
            "similar musical style"
        )

    if average_scores["tempo"] >= 0.80:
        reasons.append(
            "closely matched tempo"
        )

    elif average_scores["tempo"] >= 0.60:
        reasons.append(
            "similar tempo"
        )

    if average_scores["loudness"] >= 0.80:
        reasons.append(
            "closely matched intensity"
        )

    elif average_scores["loudness"] >= 0.60:
        reasons.append(
            "similar intensity"
        )

    if average_scores["key_mode"] >= 0.75:
        reasons.append(
            "compatible key and mode"
        )

    # ------------------------------------------------------------
    # Explicit refinement explanations.
    #
    # Only mention a refinement when the candidate responds
    # reasonably strongly to that preference.
    # ------------------------------------------------------------
    style = (
        preferences.get("style")
        or preferences.get("genre")
    )

    if (
        style
        and refinement.get("style", 0.0) >= 0.50
    ):
        reasons.append(
            f"matches your {style} style preference"
        )

    tempo_preference = preferences.get(
        "tempo"
    )

    if (
        tempo_preference
        in {"slower", "similar", "faster"}
        and refinement.get("tempo", 0.0) >= 0.75
    ):
        reasons.append(
            f"fits your {tempo_preference} tempo preference"
        )

    intensity_preference = preferences.get(
        "intensity"
    )

    if (
        intensity_preference
        in {"softer", "similar", "stronger"}
        and refinement.get(
            "intensity",
            0.0,
        ) >= 0.75
    ):
        reasons.append(
            f"fits your {intensity_preference} intensity preference"
        )

    if not reasons:
        return (
            "best overall match for the current session"
        )

    return ", ".join(reasons)


def recommend_track_for_session(
    session,
    limit=60,
    preferences=None,
):
    """
    Generate ranked recommendations for a session.

    Each candidate track is compared against every user-selected
    track currently stored in the session.

    The candidate's comparison scores are averaged to produce the
    main session-based recommendation score.

    Optional style, tempo and intensity refinements can provide a
    smaller secondary influence on ranking.

    Tracks already selected by the user, and tracks by artists
    already represented in the session, are excluded from the
    recommendation candidates.

    This reduces trivial same-artist recommendations and encourages
    greater artist-level diversity.
    """

    preferences = preferences or {}

    # ------------------------------------------------------------
    # Load the tracks selected during this session.
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

    # A recommendation cannot be generated without at least one
    # user-selected track.
    if not session_tracks:
        return []

    # ------------------------------------------------------------
    # Exclude exact session tracks.
    # ------------------------------------------------------------
    session_track_ids = [
        track.id
        for track in session_tracks
    ]

    # ------------------------------------------------------------
    # Exclude artists already represented in the session.
    # ------------------------------------------------------------
    session_artist_ids = [
        track.artist_id
        for track in session_tracks
    ]

    # ------------------------------------------------------------
    # Load recommendation candidates.
    # ------------------------------------------------------------
    candidate_tracks = (
        Track.objects
        .exclude(
            id__in=session_track_ids
        )
        .exclude(
            artist_id__in=session_artist_ids
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

            comparisons.append(
                comparison
            )

        average_scores = _average_scores(
            comparisons
        )

        # --------------------------------------------------------
        # Calculate optional explicit refinement contribution.
        # --------------------------------------------------------
        refinement = _calculate_refinement(
            candidate_track,
            session_tracks,
            preferences,
        )

        # --------------------------------------------------------
        # Session similarity remains the main score.
        #
        # Refinement can add at most 0.18. Clamp the final score
        # so it remains within the familiar 0–1 range.
        # --------------------------------------------------------
        final_score = min(
            average_scores["combined"]
            + refinement["bonus"],
            1.0,
        )

        reason = _build_reason(
            average_scores,
            refinement=refinement,
            preferences=preferences,
        )

        scored_tracks.append({
            "track": candidate_track,
            "score": final_score,
            "reason": reason,

            # Keep detailed values available for inspection,
            # automated testing and evaluation.
            "components": {
                "tags": average_scores["tags"],
                "tempo": average_scores["tempo"],
                "loudness": average_scores["loudness"],
                "key_mode": average_scores["key_mode"],
                "base_score": average_scores[
                    "combined"
                ],
                "refinement_bonus": refinement[
                    "bonus"
                ],
                "style_preference": refinement[
                    "style"
                ],
                "tempo_preference": refinement[
                    "tempo"
                ],
                "intensity_preference": refinement[
                    "intensity"
                ],
            },
        })

    if not scored_tracks:
        return []

    # ------------------------------------------------------------
    # Rank by final session + refinement score.
    # ------------------------------------------------------------
    scored_tracks.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    top_results = scored_tracks[:limit]

    # ------------------------------------------------------------
    # Replace the previous recommendation ranking for this session.
    # ------------------------------------------------------------
    session.recommendation_results.all().delete()

    for item in top_results:

        RecommendationResult.objects.create(
            session=session,
            track=item["track"],
            score=item["score"],
            reason=item["reason"],
        )

    return top_results