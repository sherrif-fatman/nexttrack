# =========================================================
# RECOMMENDER SERVICE
#
# This file contains the recommendation engine logic.
# Keeping this separate from views.py makes the code easier
# to test, maintain, and improve later.
# =========================================================

from recommendations.models import Track, RecommendationResult


# =========================================================
# MAIN RECOMMENDATION FUNCTION
#
# Takes a Session object and returns the best matching Track.
# =========================================================
def recommend_track_for_session(session):

    # -----------------------------------------------------
    # Get track IDs already used in this session.
    # These should not be recommended again.
    # -----------------------------------------------------
    session_track_ids = session.session_tracks.values_list(
        "track_id",
        flat=True
    )

    # -----------------------------------------------------
    # Get candidate tracks.
    # Exclude tracks already entered by the user.
    # -----------------------------------------------------
    candidate_tracks = Track.objects.exclude(
        id__in=session_track_ids
    )

    best_track = None
    best_score = -1
    best_reason = ""

    # -----------------------------------------------------
    # Score each possible track.
    # -----------------------------------------------------
    for track in candidate_tracks:

        score = 0
        reasons = []

        # -------------------------------------------------
        # Genre match
        # -------------------------------------------------
        if session.genre_pref and track.genre:
            if track.genre.genre.lower() == session.genre_pref.lower():
                score += 3
                reasons.append("genre matched")

        # -------------------------------------------------
        # Mood match
        # -------------------------------------------------
        if session.mood_pref and track.mood:
            if track.mood.lower() == session.mood_pref.lower():
                score += 3
                reasons.append("mood matched")

        # -------------------------------------------------
        # Energy similarity
        #
        # Smaller difference = better match.
        # Example:
        # session energy = 8
        # track energy = 7
        # difference = 1, so this is a close match.
        # -------------------------------------------------
        if session.energy_pref is not None and track.energy is not None:
            energy_difference = abs(
                session.energy_pref - track.energy
            )

            if energy_difference == 0:
                score += 3
                reasons.append("energy exactly matched")
            elif energy_difference <= 2:
                score += 2
                reasons.append("energy was similar")

        # -------------------------------------------------
        # Tempo similarity
        #
        # Smaller BPM difference = better match.
        # -------------------------------------------------
        if session.tempo_pref is not None and track.tempo is not None:
            tempo_difference = abs(
                session.tempo_pref - track.tempo
            )

            if tempo_difference <= 5:
                score += 3
                reasons.append("tempo closely matched")
            elif tempo_difference <= 15:
                score += 2
                reasons.append("tempo was similar")

        # -------------------------------------------------
        # Popularity preference
        #
        # We do not currently store popularity on Track,
        # so this can be added later if needed.
        # -------------------------------------------------

        # -------------------------------------------------
        # Keep track of the highest scoring result.
        # -------------------------------------------------
        if score > best_score:
            best_score = score
            best_track = track
            best_reason = ", ".join(reasons) or "best available match"

    # -----------------------------------------------------
    # If no tracks exist, return None.
    # -----------------------------------------------------
    if best_track is None:
        return None

    # -----------------------------------------------------
    # Store the recommendation result in the database.
    # This lets us inspect previous recommendations later.
    # -----------------------------------------------------
    RecommendationResult.objects.create(
        session=session,
        track=best_track,
        score=best_score,
        reason=best_reason
    )

    return best_track