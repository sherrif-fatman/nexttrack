
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

@api_view(["POST"])
def recommend_track(request):


#Get request data from frontend

    track_ids = request.data.get("track_ids", [])
    preferences = request.data.get("preferences", {})


#Create a new recommendation session
    
    session = Session.objects.create(
        genre_pref=preferences.get("genre", ""),
        mood_pref=preferences.get("mood", ""),
        energy_pref=preferences.get("energy"),
        tempo_pref=preferences.get("tempo"),
    )


#Attach selected tracks to the session
    
    for index, track_id in enumerate(track_ids, start=1):

        try:
            track = Track.objects.get(id=track_id)

            SessionTrack.objects.create(
                session=session,
                track=track,
                position=index
            )

        except Track.DoesNotExist:

            
            #Return error if selected track does not exist
            
            return Response(
                {
                    "error": f"Track with id {track_id} does not exist"
                },
                status=status.HTTP_400_BAD_REQUEST
            )


#Run recommendation engine
#Returns the highest scoring recommended track.

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

@api_view(["POST"])
def submit_feedback(request):


# Get feedback data from frontend request

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


#Validate session
    
    try:
        session = Session.objects.get(id=session_id)

    except Session.DoesNotExist:

        return Response(
            {
                "error": "Session does not exist"
            },
            status=status.HTTP_400_BAD_REQUEST
        )


#Create feedback record

    feedback = PrototypeFeedback.objects.create(
        session=session,
        recommendation_relevance=recommendation_relevance,
        explanation_clarity=explanation_clarity,
        interface_ease_of_use=interface_ease_of_use,
        search_clarity=search_clarity,
        comments=comments,
    )


#Return success response

    return Response(
        {
            "message": "Feedback submitted successfully",
            "feedback_id": feedback.id
        },
        status=status.HTTP_201_CREATED
    )


#TRACK SEARCH API

@api_view(["GET"])
def search_tracks(request):


#Get search query from URL parameter
  
    query = request.GET.get("q", "").strip()

    
#Return empty array if query is blank

    if not query:
        return Response([])

#Search tracks using partial matching
#i contains performs case-insensitive matching.
    tracks = Track.objects.filter(
        Q(track_name__icontains=query) |
        Q(artist__artist_name__icontains=query) |
        Q(album__album_name__icontains=query)
    ).select_related(
        "artist",
        "album",
        "genre"
    )[:20]

    
#Build JSON response list
    
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


#Return matching tracks to frontend
    return Response(results)
