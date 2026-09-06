
from django.db.models import Q

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import (
    Track,
    Session,
    SessionTrack,
    PrototypeFeedback,
)

from .services.recommender import recommend_track_for_session


# =========================================================
# RECOMMENDATION PREFERENCE OPTIONS
#
# These are optional, user-controlled refinements.
#
# They influence only the current recommendation request and
# do not require a persistent user profile.
# =========================================================

VALID_TEMPO_PREFERENCES = {
    "slower",
    "similar",
    "faster",
}

VALID_INTENSITY_PREFERENCES = {
    "softer",
    "similar",
    "stronger",
}


def _normalise_preferences(preferences):
    """
    Validate and normalise optional recommendation refinements.

    Supported preferences:

        style:
            Musical style selected by the frontend.

        tempo:
            slower
            similar
            faster

        intensity:
            softer
            similar
            stronger

    Empty values are ignored.

    The older "genre" key is accepted as a fallback while the
    frontend is migrated to the new "style" terminology.

    Legacy numeric tempo values are ignored rather than rejected.
    Earlier versions of the prototype used exact BPM values such
    as 120. The current interface instead uses relative choices
    such as "slower", "similar" and "faster".
    """

    if not isinstance(preferences, dict):
        return None, (
            "preferences must be an object"
        )

    normalised = {}

    # =====================================================
    # STYLE
    # =====================================================

    style = (
        preferences.get("style")
        or preferences.get("genre")
        or ""
    )

    if style:
        style = str(style).strip()

        if style:
            normalised["style"] = style

    # =====================================================
    # TEMPO
    # =====================================================

    tempo = preferences.get("tempo")

    # -----------------------------------------------------
    # Only string values belong to the new refinement API.
    #
    # Legacy versions of NextTrack sent exact numeric BPM
    # values such as 120. Those values are deliberately
    # ignored for backwards compatibility.
    # -----------------------------------------------------

    if isinstance(tempo, str):

        tempo = tempo.lower().strip()

        if tempo:

            if (
                tempo
                not in VALID_TEMPO_PREFERENCES
            ):
                return None, (
                    "tempo preference must be "
                    "'slower', 'similar', or 'faster'"
                )

            normalised["tempo"] = tempo

    # =====================================================
    # INTENSITY
    # =====================================================

    intensity = preferences.get(
        "intensity"
    )

    if intensity:

        intensity = str(
            intensity
        ).lower().strip()

        if (
            intensity
            not in VALID_INTENSITY_PREFERENCES
        ):
            return None, (
                "intensity preference must be "
                "'softer', 'similar', or 'stronger'"
            )

        normalised["intensity"] = (
            intensity
        )

    return normalised, None


# =========================================================
# RECOMMENDATION API
# =========================================================

@api_view(["POST"])
def recommend_track(request):

    # =====================================================
    # GET REQUEST DATA
    # =====================================================

    track_ids = request.data.get(
        "track_ids",
        []
    )

    raw_preferences = request.data.get(
        "preferences",
        {}
    )

    session_id = request.data.get(
        "session_id"
    )

    # =====================================================
    # VALIDATE REQUEST
    # =====================================================

    if not track_ids:
        return Response(
            {
                "error":
                    "At least one track_id is required"
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # -----------------------------------------------------
    # Validate optional recommendation refinements.
    # -----------------------------------------------------

    preferences, preference_error = (
        _normalise_preferences(
            raw_preferences
        )
    )

    if preference_error:
        return Response(
            {
                "error": preference_error
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # =====================================================
    # CREATE OR REUSE SESSION
    # =====================================================

    if session_id:

        try:
            session = Session.objects.get(
                id=session_id
            )

        except Session.DoesNotExist:
            return Response(
                {
                    "error":
                        "Session does not exist"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

    else:

        # -------------------------------------------------
        # User refinements are temporary inputs to the
        # recommender rather than a persistent preference
        # profile.
        # -------------------------------------------------

        session = Session.objects.create()

    # =====================================================
    # ATTACH SELECTED TRACKS TO SESSION
    # =====================================================

    for track_id in track_ids:

        try:
            track = Track.objects.get(
                id=track_id
            )

        except Track.DoesNotExist:

            return Response(
                {
                    "error":
                        f"Track with id "
                        f"{track_id} does not exist"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # -------------------------------------------------
        # Do not add the same track to a session twice.
        # -------------------------------------------------

        already_added = (
            SessionTrack.objects.filter(
                session=session,
                track=track
            ).exists()
        )

        if not already_added:

            next_position = (
                session.session_tracks.count()
                + 1
            )

            SessionTrack.objects.create(
                session=session,
                track=track,
                position=next_position
            )

    # =====================================================
    # RUN RECOMMENDATION ENGINE
    # =====================================================

    recommendation_items = (
        recommend_track_for_session(
            session=session,
            limit=60,
            preferences=preferences,
        )
    )

    # =====================================================
    # BUILD RESPONSE
    # =====================================================

    recommendations = []

    for item in recommendation_items:

        track = item["track"]

        recommendations.append({
            "id":
                track.id,

            "track_name":
                track.track_name,

            "artist":
                track.artist.artist_name,

            "album": (
                track.album.album_name
                if track.album
                else None
            ),

            "artwork_url": (
                track.album.cover_thumbnail_url
                if (
                    track.album
                    and track.album.cover_thumbnail_url
                )
                else None
            ),

            "genre": (
                track.genre.genre
                if track.genre
                else None
            ),

            "tempo":
                track.tempo,

            "energy":
                track.energy,

            "mood":
                track.mood,

            "score":
                item["score"],

            "reason":
                item["reason"],
        })

    return Response(
        {
            "session_id":
                session.id,

            "recommendations":
                recommendations,
        },
        status=status.HTTP_200_OK
    )


# =========================================================
# FEEDBACK API
# =========================================================

@api_view(["POST"])
def submit_feedback(request):

    # =====================================================
    # GET FEEDBACK DATA
    # =====================================================

    session_id = request.data.get(
        "session_id"
    )

    recommendation_relevance = (
        request.data.get(
            "recommendation_relevance"
        )
    )

    explanation_clarity = (
        request.data.get(
            "explanation_clarity"
        )
    )

    interface_ease_of_use = (
        request.data.get(
            "interface_ease_of_use"
        )
    )

    search_clarity = (
        request.data.get(
            "search_clarity"
        )
    )

    comments = request.data.get(
    "comments",
    ""
    )

    consent_given = request.data.get(
        "consent_given",
        False
    )

    if consent_given is not True:
        return Response(
            {
                "error":
                    "Consent is required before feedback can be submitted"
            },
            status=status.HTTP_400_BAD_REQUEST
    )

# =====================================================
# VALIDATE SESSION
# =====================================================

    try:
        session = Session.objects.get(
            id=session_id
        )

    except Session.DoesNotExist:

        return Response(
            {
                "error":
                    "Session does not exist"
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # =====================================================
    # CREATE FEEDBACK RECORD
    # =====================================================

    feedback = (
        PrototypeFeedback.objects.create(
            session=session,

            recommendation_relevance=(
                recommendation_relevance
            ),

            explanation_clarity=(
                explanation_clarity
            ),

            interface_ease_of_use=(
                interface_ease_of_use
            ),

            search_clarity=(
                search_clarity
            ),

            comments=comments,
            
            consent_given=consent_given,
        )
    )

    return Response(
        {
            "message":
                "Feedback submitted successfully",

            "feedback_id":
                feedback.id,
        },
        status=status.HTTP_201_CREATED
    )


# =========================================================
# TRACK SEARCH API
# =========================================================

@api_view(["GET"])
def search_tracks(request):

    # =====================================================
    # GET SEARCH QUERY
    # =====================================================

    query = request.GET.get(
        "q",
        ""
    ).strip()

    if not query:
        return Response([])

    # =====================================================
    # SEARCH TRACKS
    # =====================================================

    tracks = (
        Track.objects.filter(
            Q(
                track_name__icontains=query
            )
            |
            Q(
                artist__artist_name__icontains=query
            )
            |
            Q(
                album__album_name__icontains=query
            )
        )
        .select_related(
            "artist",
            "album",
            "genre"
        )[:20]
    )

    # =====================================================
    # BUILD RESPONSE
    # =====================================================

    results = []

    for track in tracks:

        results.append({
            "id":
                track.id,

            "track_name":
                track.track_name,

            "artist":
                track.artist.artist_name,

            "album": (
                track.album.album_name
                if track.album
                else None
            ),

            "genre": (
                track.genre.genre
                if track.genre
                else None
            ),
        })

    return Response(
        results
    )
