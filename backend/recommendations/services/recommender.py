
#recommender service
#Contains the recommendation engine logic used by the API.

from recommendations.models import Track, RecommendationResult

def recommend_track_for_session(session, limit=20):

#Get IDs of tracks already used in this session.  
#These should NOT be recommended back to the user.
    session_track_ids = session.session_tracks.values_list(
        "track_id",
        flat=True
    )

   
#Get candidate tracks for recommendation. 
#Exclude tracks already entered by the user.
    candidate_tracks = Track.objects.exclude(
        id__in=session_track_ids
    )

#List used to store scored recommendation results.
    scored_tracks = []

    
#Score each candidate track.

    for track in candidate_tracks:

        score = 0
        reasons = []

        
#Genre matching
#Exact genre matches are strongly weighted.
        
        if session.genre_pref and track.genre:

            if track.genre.genre.lower() == session.genre_pref.lower():

                score += 3
                reasons.append("genre matched")

#Mood matching
#Exact mood matches are strongly weighted.
        if session.mood_pref and track.mood:

            if track.mood.lower() == session.mood_pref.lower():

                score += 2
                reasons.append("mood matched")

#Energy similarity matching

        if session.energy_pref is not None and track.energy is not None:

            energy_difference = abs(
                session.energy_pref - track.energy
            )

        
#Perfect energy match
            
            if energy_difference == 0:

                score += 2
                reasons.append("energy exactly matched")

            
#Close energy match

            elif energy_difference <= 2:

                score += 2
                reasons.append("energy was similar")

      
#Tempo similarity matching
#Smaller BPM differences produce better matches.
        if session.tempo_pref is not None and track.tempo is not None:

            tempo_difference = abs(
                session.tempo_pref - track.tempo
            )

#Very close BPM match
          
            if tempo_difference <= 5:

                score += 3
                reasons.append("tempo closely matched")

            
#Moderately similar BPM
            elif tempo_difference <= 15:

                score += 2
                reasons.append("tempo was similar")

        
#Store scored result
        scored_tracks.append({
            "track": track,
            "score": score,
            "reason": (
                ", ".join(reasons)
                or "best available match"
            )
        })


#Return empty list if no tracks exist.
    if not scored_tracks:
        return []

#Sort tracks by score in descending order.
#Highest scoring tracks appear first.
   
    scored_tracks = sorted(
        scored_tracks,
        key=lambda item: item["score"],
        reverse=True
    )

#Limit number of recommendations returned.
 
    top_results = scored_tracks[:limit]

   
#Store recommendation results in database.
    for item in top_results:

        RecommendationResult.objects.create(
            session=session,
            track=item["track"],
            score=item["score"],
            reason=item["reason"]
        )

#Return ranked recommendation results.
    return top_results