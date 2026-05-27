# =========================================================
# IMPORTS
# =========================================================

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
# RECOMMEND TRACK API
#
# Handles recommendation requests from the frontend.
#
# Expected POST body:
#
# {
#   "track_ids": [10005],
#   "preferences": {
#     "genre": "rock",
#     "mood": "",
#     "energy": 5,
#     "tempo": null
#   }
# }
# =========================================================
@api_view(["POST"])
def recommend_track(request):

    # -----------------------------------------------------
    # Get request data from frontend
    # -----------------------------------------------------
    track_ids = request.data.get("track_ids", [])
    preferences = request.data.get("preferences", {})

    # -----------------------------------------------------
    # Create a new recommendation session
    #
    # This stores the user preferences used for the
    # recommendation request.
    # -----------------------------------------------------
    session = Session.objects.create(
        genre_pref=preferences.get("genre", ""),
        mood_pref=preferences.get("mood", ""),
        energy_pref=preferences.get("energy"),
        tempo_pref=preferences.get("tempo"),
    )

    # -----------------------------------------------------
    # Attach selected tracks to the session
    #
    # These are the tracks the user selected as input
    # for generating recommendations.
    # -----------------------------------------------------
    for index, track_id in enumerate(track_ids, start=1):

        try:
            track = Track.objects.get(id=track_id)

            SessionTrack.objects.create(
                session=session,
                track=track,
                position=index
            )

        except Track.DoesNotExist:

            # ---------------------------------------------
            # Return error if selected track does not exist
            # ---------------------------------------------
            return Response(
                {
                    "error": f"Track with id {track_id} does not exist"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

    # -----------------------------------------------------
    # Run recommendation engine
    #
    # Returns the highest scoring recommended track.
    # -----------------------------------------------------
    recommendation_items = recommend_track_for_session(
        session=session,
        limit=20
    )

    recommendations = []

    for item in recommendation_items:
        track = item["track"]

        recommendations.append({
            "id": track.id,
            "track_name": track.track_name,
            "artist": track.artist.artist_name,
            "album": track.album.album_name if track.album else None,
            "genre": track.genre.genre if track.genre else None,
            "tempo": track.tempo,
            "energy": track.energy,
            "mood": track.mood,
            "score": item["score"],
            "reason": item["reason"],
        })

    return Response(
        {
            "session_id": session.id,
            "recommendations": recommendations
        },
        status=status.HTTP_200_OK
    )

# =========================================================
# PROTOTYPE FEEDBACK API
#
# Stores user feedback from prototype evaluation.
#
# Expected POST body:
#
# {
#   "session_id": 42,
#   "recommendation_relevance": 4,
#   "explanation_clarity": 5,
#   "interface_ease_of_use": 4,
#   "search_clarity": 5,
#   "comments": "Recommendations were interesting but genre matching was weak."
# }
# =========================================================
@api_view(["POST"])
def submit_feedback(request):

    # -----------------------------------------------------
    # Get feedback data from frontend request
    # -----------------------------------------------------
    session_id = request.data.get("session_id")

    recommendation_relevance = request.data.get(
        "recommendation_relevance"
    )

    explanation_clarity = request.data.get(
        "explanation_clarity"
    )

    interface_ease_of_use = request.data.get(
        "interface_ease_of_use"
    )

    search_clarity = request.data.get(
        "search_clarity"
    )

    comments = request.data.get("comments", "")

    # -----------------------------------------------------
    # Validate session
    # -----------------------------------------------------
    try:
        session = Session.objects.get(id=session_id)

    except Session.DoesNotExist:

        return Response(
            {
                "error": "Session does not exist"
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # -----------------------------------------------------
    # Create feedback record
    # -----------------------------------------------------
    feedback = PrototypeFeedback.objects.create(
        session=session,
        recommendation_relevance=recommendation_relevance,
        explanation_clarity=explanation_clarity,
        interface_ease_of_use=interface_ease_of_use,
        search_clarity=search_clarity,
        comments=comments,
    )

    # -----------------------------------------------------
    # Return success response
    # -----------------------------------------------------
    return Response(
        {
            "message": "Feedback submitted successfully",
            "feedback_id": feedback.id
        },
        status=status.HTTP_201_CREATED
    )


    # -----------------------------------------------------
    # Handle case where no recommendation is available
    # -----------------------------------------------------
    # if recommended_track is None:

    #     return Response(
    #         {
    #             "session_id": session.id,
    #             "recommendations": []
    #         },
    #         status=status.HTTP_200_OK
    #     )

    # # -----------------------------------------------------
    # # Get stored recommendation scoring information
    # # -----------------------------------------------------
    # result = RecommendationResult.objects.filter(
    #     session=session,
    #     track=recommended_track
    # ).first()

    # # -----------------------------------------------------
    # # Format recommendation response object
    # # -----------------------------------------------------
    # recommendation = {
    #     "id": recommended_track.id,
    #     "track_name": recommended_track.track_name,
    #     "artist": recommended_track.artist.artist_name,
    #     "album": (
    #         recommended_track.album.album_name
    #         if recommended_track.album else None
    #     ),
    #     "genre": (
    #         recommended_track.genre.genre
    #         if recommended_track.genre else None
    #     ),
    #     "tempo": recommended_track.tempo,
    #     "energy": recommended_track.energy,
    #     "mood": recommended_track.mood,
    #     "score": result.score if result else None,
    #     "reason": result.reason if result else "",
    # }

    # # -----------------------------------------------------
    # # Return recommendation response to frontend
    # #
    # # recommendations is returned as an ARRAY so the
    # # frontend can later support multiple results.
    # # -----------------------------------------------------
    # return Response(
    #     {
    #         "session_id": session.id,
    #         "recommendations": [recommendation]
    #     },
    #     status=status.HTTP_200_OK
    # )


# =========================================================
# TRACK SEARCH API
#
# Allows frontend predictive searching using:
#
# - Track name
# - Artist name
# - Album name
#
# Example:
# /api/tracks/search/?q=bonobo
# =========================================================
@api_view(["GET"])
def search_tracks(request):

    # -----------------------------------------------------
    # Get search query from URL parameter
    # -----------------------------------------------------
    query = request.GET.get("q", "").strip()

    # -----------------------------------------------------
    # Return empty array if query is blank
    # -----------------------------------------------------
    if not query:
        return Response([])

    # -----------------------------------------------------
    # Search tracks using partial matching
    #
    # icontains performs case-insensitive matching.
    # -----------------------------------------------------
    tracks = Track.objects.filter(
        Q(track_name__icontains=query) |
        Q(artist__artist_name__icontains=query) |
        Q(album__album_name__icontains=query)
    ).select_related(
        "artist",
        "album",
        "genre"
    )[:20]

    # -----------------------------------------------------
    # Build JSON response list
    # -----------------------------------------------------
    results = []

    for track in tracks:

        results.append({
            "id": track.id,
            "track_name": track.track_name,
            "artist": track.artist.artist_name,
            "album": (
                track.album.album_name
                if track.album else None
            ),
            "genre": (
                track.genre.genre
                if track.genre else None
            ),
        })

    # -----------------------------------------------------
    # Return matching tracks to frontend
    # -----------------------------------------------------
    return Response(results)
