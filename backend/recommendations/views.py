from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import Track, Session, SessionTrack, RecommendationResult
from .services.recommender import recommend_track_for_session




# test view to check connection to API
# @api_view(["POST"])
# def recommend_track(request):
#     return Response({
#         "recommended_track": {
#             "title": "Midnight City",
#             "artist": "M83",
#             "reason": "Selected as a mock result based on your recent listening session."
#         }
#     })

# =========================================================
# API VIEWS
# Handles requests from the frontend
# =========================================================


# =========================================================
# RECOMMEND TRACK API
#
# Expected POST body:
# {
#   "track_ids": [1, 2, 3],
#   "preferences": {
#     "genre": "Electronic",
#     "mood": "focused",
#     "energy": 8,
#     "tempo": 120
#   }
# }
# =========================================================
@api_view(["POST"])
def recommend_track(request):

    # -----------------------------------------------------
    # Get data from request
    # -----------------------------------------------------
    track_ids = request.data.get("track_ids", [])
    preferences = request.data.get("preferences", {})

    # -----------------------------------------------------
    # Create a new recommendation session
    # -----------------------------------------------------
    session = Session.objects.create(
        genre_pref=preferences.get("genre", ""),
        mood_pref=preferences.get("mood", ""),
        energy_pref=preferences.get("energy"),
        tempo_pref=preferences.get("tempo"),
    )

    # -----------------------------------------------------
    # Attach input tracks to the session
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
            return Response(
                {
                    "error": f"Track with id {track_id} does not exist"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

    # -----------------------------------------------------
    # Run recommendation engine
    # -----------------------------------------------------
    recommended_track = recommend_track_for_session(session)

    # -----------------------------------------------------
    # Handle case where no recommendation is available
    # -----------------------------------------------------
    if recommended_track is None:
        return Response(
            {
                "session_id": session.id,
                "message": "No recommendation available"
            },
            status=status.HTTP_200_OK
        )

    # -----------------------------------------------------
    # Get saved recommendation result
    # -----------------------------------------------------
    result = RecommendationResult.objects.filter(
        session=session,
        track=recommended_track
    ).first()

    # -----------------------------------------------------
    # Return recommendation response
    # -----------------------------------------------------
    return Response(
        {
            "session_id": session.id,
            "recommended_track": {
                "id": recommended_track.id,
                "track_name": recommended_track.track_name,
                "artist": recommended_track.artist.artist_name,
                "album": recommended_track.album.album_name if recommended_track.album else None,
                "genre": recommended_track.genre.genre if recommended_track.genre else None,
                "tempo": recommended_track.tempo,
                "energy": recommended_track.energy,
                "mood": recommended_track.mood,
                "score": result.score if result else None,
                "reason": result.reason if result else "",
            }
        },
        status=status.HTTP_200_OK
    )
