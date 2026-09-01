# docker compose run --rm backend python manage.py shell -c "
# from recommendations.models import Track

# for track in Track.objects.filter(
#     artist__artist_name__icontains='John Mayer'
# ):
#     print(track.id, '|', track.track_name, '|', track.artist.artist_name)
# "


# docker compose run --rm backend python manage.py shell <<'PY'
# from recommendations.models import Session, SessionTrack, Track
# from recommendations.services.recommender import recommend_track_for_session

# track = Track.objects.get(id=7000)

# session = Session.objects.create()

# SessionTrack.objects.create(
#     session=session,
#     track=track,
#     position=1,
# )

# results = recommend_track_for_session(
#     session=session,
#     limit=10,
# )

# print()
# print(f'Input: {track.track_name} — {track.artist.artist_name}')
# print('=' * 90)

# for index, result in enumerate(results, start=1):
#     rec = result['track']
#     components = result['components']

#     print(
#         f"{index}. {rec.track_name} — {rec.artist.artist_name}"
#     )
#     print(
#         f"   Score: {result['score']:.4f}"
#         f" | Tags: {components['tags']:.4f}"
#         f" | Tempo: {components['tempo']:.4f}"
#         f" | Loudness: {components['loudness']:.4f}"
#         f" | Key/Mode: {components['key_mode']:.4f}"
#     )
#     print(f"   Reason: {result['reason']}")
#     print()
# PY