# docker compose run --rm backend python manage.py shell <<'PY'
# from recommendations.models import Track

# track_ids = list(
#     Track.objects
#     .order_by('id')
#     .values_list('id', flat=True)
# )

# if not track_ids:
#     print('No tracks found.')
#     raise SystemExit

# positions = [
#     0,
#     len(track_ids) // 10,
#     len(track_ids) // 5,
#     len(track_ids) * 3 // 10,
#     len(track_ids) * 2 // 5,
#     len(track_ids) // 2,
#     len(track_ids) * 3 // 5,
#     len(track_ids) * 7 // 10,
#     len(track_ids) * 4 // 5,
#     len(track_ids) - 1,
# ]

# selected_ids = [track_ids[position] for position in positions]

# tracks = (
#     Track.objects
#     .filter(id__in=selected_ids)
#     .select_related('artist', 'album')
#     .prefetch_related('track_tags__tag')
#     .order_by('id')
# )

# for track in tracks:
#     print()
#     print('=' * 70)
#     print(f'{track.track_name} — {track.artist.artist_name}')
#     print(f'MSD ID: {track.msd_track_id}')
#     print(f'Album: {track.album.album_name if track.album else None}')
#     print(f'Tempo: {track.tempo}')
#     print(f'Loudness: {track.loudness}')
#     print(f'Key: {track.key}')
#     print(f'Mode: {track.mode}')
#     print(f'Familiarity: {track.familiarity}')
#     print(f'Popularity: {track.popularity}')
#     print(f'Year: {track.release_year}')

#     tags = track.track_tags.all().order_by('-weight')[:5]

#     print('Top tags:')
#     for item in tags:
#         print(f'  {item.tag.name}: {item.weight:.3f}')
# PY