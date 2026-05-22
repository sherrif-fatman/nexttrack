from django.test import TestCase

from recommendations.models import (
    Artist,
    Genre,
    Album,
    Track,
    Session,
    SessionTrack,
    RecommendationResult,
)

from recommendations.services.recommender import recommend_track_for_session


# =========================================================
# RECOMMENDER LOGIC TESTS
#
# These tests check the recommendation engine directly,
# without going through the API.
# =========================================================
class RecommenderLogicTest(TestCase):

    # =====================================================
    # SETUP TEST DATA
    #
    # Runs before each test method.
    # =====================================================
    def setUp(self):

        # -------------------------------------------------
        # Create artists
        # -------------------------------------------------
        self.artist = Artist.objects.create(
            artist_name="Test Artist"
        )

        # -------------------------------------------------
        # Create genres
        # -------------------------------------------------
        self.electronic = Genre.objects.create(
            genre="Electronic"
        )

        self.rock = Genre.objects.create(
            genre="Rock"
        )

        # -------------------------------------------------
        # Create album
        # -------------------------------------------------
        self.album = Album.objects.create(
            album_name="Test Album",
            artist=self.artist
        )

        # -------------------------------------------------
        # Track already used in the session
        # This should NOT be recommended again.
        # -------------------------------------------------
        self.used_track = Track.objects.create(
            track_name="Used Track",
            artist=self.artist,
            album=self.album,
            genre=self.electronic,
            tempo=120,
            energy=8,
            mood="focused"
        )

        # -------------------------------------------------
        # Best matching candidate track
        # This should be recommended.
        # -------------------------------------------------
        self.best_track = Track.objects.create(
            track_name="Best Match Track",
            artist=self.artist,
            album=self.album,
            genre=self.electronic,
            tempo=122,
            energy=8,
            mood="focused"
        )

        # -------------------------------------------------
        # Poorer candidate track
        # This should score lower.
        # -------------------------------------------------
        self.poor_match_track = Track.objects.create(
            track_name="Poor Match Track",
            artist=self.artist,
            album=self.album,
            genre=self.rock,
            tempo=90,
            energy=3,
            mood="sad"
        )

    # =====================================================
    # TEST: BEST MATCH IS RETURNED
    # =====================================================
    def test_recommender_returns_best_matching_track(self):

        # -------------------------------------------------
        # Create a recommendation session with preferences
        # -------------------------------------------------
        session = Session.objects.create(
            genre_pref="Electronic",
            energy_pref=8,
            mood_pref="focused",
            tempo_pref=120
        )

        # -------------------------------------------------
        # Add a track that has already been used
        # -------------------------------------------------
        SessionTrack.objects.create(
            session=session,
            track=self.used_track,
            position=1
        )

        # -------------------------------------------------
        # Run recommender
        # -------------------------------------------------
        result = recommend_track_for_session(session)

        # -------------------------------------------------
        # Check best matching track is returned
        # -------------------------------------------------
        self.assertEqual(result, self.best_track)

    # =====================================================
    # TEST: USED TRACK IS NOT RECOMMENDED AGAIN
    # =====================================================
    def test_recommender_excludes_tracks_already_in_session(self):

        session = Session.objects.create(
            genre_pref="Electronic",
            energy_pref=8,
            mood_pref="focused",
            tempo_pref=120
        )

        SessionTrack.objects.create(
            session=session,
            track=self.used_track,
            position=1
        )

        result = recommend_track_for_session(session)

        self.assertNotEqual(result, self.used_track)

    # =====================================================
    # TEST: RECOMMENDATION RESULT IS SAVED
    # =====================================================
    def test_recommendation_result_is_saved(self):

        session = Session.objects.create(
            genre_pref="Electronic",
            energy_pref=8,
            mood_pref="focused",
            tempo_pref=120
        )

        SessionTrack.objects.create(
            session=session,
            track=self.used_track,
            position=1
        )

        recommend_track_for_session(session)

        self.assertEqual(
            RecommendationResult.objects.count(),
            1
        )

        saved_result = RecommendationResult.objects.first()

        self.assertEqual(
            saved_result.track,
            self.best_track
        )

    # =====================================================
    # TEST: RETURNS NONE IF NO CANDIDATE TRACKS EXIST
    # =====================================================
    def test_recommender_returns_none_when_no_candidates_exist(self):

        session = Session.objects.create(
            genre_pref="Electronic",
            energy_pref=8,
            mood_pref="focused",
            tempo_pref=120
        )

        # Add every track to the session,
        # leaving no candidates available.
        SessionTrack.objects.create(
            session=session,
            track=self.used_track,
            position=1
        )

        SessionTrack.objects.create(
            session=session,
            track=self.best_track,
            position=2
        )

        SessionTrack.objects.create(
            session=session,
            track=self.poor_match_track,
            position=3
        )

        result = recommend_track_for_session(session)

        self.assertIsNone(result)