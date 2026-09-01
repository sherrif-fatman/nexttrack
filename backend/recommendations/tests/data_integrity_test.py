# docker compose run --rm backend python manage.py shell -c "
# from django.db.models import Count, Q
# from recommendations.models import Track, TrackTag

# total = Track.objects.count()

# print('=== TRACK INTEGRITY ===')
# print('Total tracks:', total)
# print('With MSD ID:', Track.objects.exclude(msd_track_id__isnull=True).exclude(msd_track_id='').count())
# print('With tempo:', Track.objects.exclude(tempo__isnull=True).count())
# print('With loudness:', Track.objects.exclude(loudness__isnull=True).count())
# print('With key:', Track.objects.exclude(key__isnull=True).count())
# print('With mode:', Track.objects.exclude(mode__isnull=True).count())
# print('With duration:', Track.objects.exclude(duration_seconds__isnull=True).count())
# print('With familiarity:', Track.objects.exclude(familiarity__isnull=True).count())
# print('With popularity:', Track.objects.exclude(popularity__isnull=True).count())
# print('With release year:', Track.objects.exclude(release_year__isnull=True).count())

# with_tags = (
#     Track.objects
#     .annotate(tag_count=Count('track_tags'))
#     .filter(tag_count__gt=0)
#     .count()
# )

# print('With at least one tag:', with_tags)
# print('TrackTag rows:', TrackTag.objects.count())

# print()
# print('=== POTENTIAL PROBLEMS ===')
# print('Tempo <= 0:', Track.objects.filter(tempo__lte=0).count())
# print('Key outside 0-11:', Track.objects.filter(Q(key__lt=0) | Q(key__gt=11)).count())
# print('Mode outside 0-1:', Track.objects.filter(Q(mode__lt=0) | Q(mode__gt=1)).count())
# print('Tracks with no tags:', total - with_tags)
# "