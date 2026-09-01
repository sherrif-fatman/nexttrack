from django.test import TestCase

from recommendations.models import (
    Artist,
    Genre,
    Album,
    Track,
    Tag,
    TrackTag,
    Session,
    SessionTrack,
    RecommendationResult,
)

from recommendations.services.recommender import (
    recommend_track_for_session,
)


# =========================================================
# RECOMMENDER LOGIC TESTS
#
# These tests check the recommendation engine directly,
# without going through the API.
#
# The recommender should:
# - exclude tracks already selected in the session
# - rank candidate tracks by similarity
# - use multiple session tracks as temporary context
# - save the current recommendation results
# - return an empty list when no candidates exist
# =========================================================
class RecommenderLogicTest(TestCase):

    # =====================================================
    # SETUP TEST DATA
    #
    # Runs before each test method.
    # =====================================================
    def setUp(self):

        # -------------------------------------------------
        # Create artist
        # -------------------------------------------------
        self.artist = Artist.objects.create(
            artist_name="Test Artist"
        )

        # -------------------------------------------------
        # Create genres
        #
        # Genre is not directly used by the new similarity
        # calculation, but it remains part of the catalogue
        # model and API output.
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
        # Create musical tags
        # -------------------------------------------------
        self.rock_tag = Tag.objects.create(
            name="rock",
            category="genre"
        )

        self.indie_tag = Tag.objects.create(
            name="indie",
            category="genre"
        )

        self.ambient_tag = Tag.objects.create(
            name="ambient",
            category="genre"
        )

        # -------------------------------------------------
        # First track selected by the user.
        # -------------------------------------------------
        self.session_track_one = Track.objects.create(
            track_name="Session Track One",
            artist=self.artist,
            album=self.album,
            genre=self.rock,
            tempo=120,
            loudness=-10,
            key=5,
            mode=1,
        )

        TrackTag.objects.create(
            track=self.session_track_one,
            tag=self.rock_tag,
            weight=1.0,
            source="test"
        )

        TrackTag.objects.create(
            track=self.session_track_one,
            tag=self.indie_tag,
            weight=0.8,
            source="test"
        )

        # -------------------------------------------------
        # Second track selected by the user.
        #
        # This is deliberately similar to track one so the
        # session represents a fairly consistent musical
        # preference.
        # -------------------------------------------------
        self.session_track_two = Track.objects.create(
            track_name="Session Track Two",
            artist=self.artist,
            album=self.album,
            genre=self.rock,
            tempo=124,
            loudness=-11,
            key=5,
            mode=1,
        )

        TrackTag.objects.create(
            track=self.session_track_two,
            tag=self.rock_tag,
            weight=0.9,
            source="test"
        )

        TrackTag.objects.create(
            track=self.session_track_two,
            tag=self.indie_tag,
            weight=0.7,
            source="test"
        )

        # -------------------------------------------------
        # Strong candidate.
        #
        # Similar tags, tempo, loudness, key and mode.
        # This should rank highly.
        # -------------------------------------------------
        self.best_track = Track.objects.create(
            track_name="Best Match Track",
            artist=self.artist,
            album=self.album,
            genre=self.rock,
            tempo=122,
            loudness=-10.5,
            key=5,
            mode=1,
        )

        TrackTag.objects.create(
            track=self.best_track,
            tag=self.rock_tag,
            weight=0.95,
            source="test"
        )

        TrackTag.objects.create(
            track=self.best_track,
            tag=self.indie_tag,
            weight=0.75,
            source="test"
        )

        # -------------------------------------------------
        # Poorer candidate.
        #
        # Different tag profile and noticeably different
        # acoustic values.
        # -------------------------------------------------
        self.poor_match_track = Track.objects.create(
            track_name="Poor Match Track",
            artist=self.artist,
            album=self.album,
            genre=self.electronic,
            tempo=80,
            loudness=-25,
            key=9,
            mode=0,
        )

        TrackTag.objects.create(
            track=self.poor_match_track,
            tag=self.ambient_tag,
            weight=1.0,
            source="test"
        )

    # =====================================================
    # TEST: BEST MATCH IS RANKED FIRST
    # =====================================================
    def test_recommender_ranks_best_matching_track_first(self):

        session = Session.objects.create()

        SessionTrack.objects.create(
            session=session,
            track=self.session_track_one,
            position=1
        )

        results = recommend_track_for_session(
            session,
            limit=2
        )

        # At least one recommendation should be returned.
        self.assertTrue(results)

        # The strongest candidate should appear first.
        self.assertEqual(
            results[0]["track"],
            self.best_track
        )

        # The best result should have a higher score than
        # the poorer candidate.
        self.assertGreater(
            results[0]["score"],
            results[1]["score"]
        )

    # =====================================================
    # TEST: TRACKS ALREADY IN SESSION ARE EXCLUDED
    # =====================================================
    def test_recommender_excludes_tracks_already_in_session(self):

        session = Session.objects.create()

        SessionTrack.objects.create(
            session=session,
            track=self.session_track_one,
            position=1
        )

        results = recommend_track_for_session(session)

        recommended_tracks = [
            item["track"]
            for item in results
        ]

        self.assertNotIn(
            self.session_track_one,
            recommended_tracks
        )

    # =====================================================
    # TEST: MULTIPLE SESSION TRACKS ARE USED
    # =====================================================
    def test_recommender_uses_multiple_session_tracks(self):

        session = Session.objects.create()

        SessionTrack.objects.create(
            session=session,
            track=self.session_track_one,
            position=1
        )

        SessionTrack.objects.create(
            session=session,
            track=self.session_track_two,
            position=2
        )

        results = recommend_track_for_session(
            session,
            limit=2
        )

        # The candidate that is similar to both tracks should
        # still rank first.
        self.assertEqual(
            results[0]["track"],
            self.best_track
        )

        # The recommendation should contain the component
        # scores used to build the final result.
        self.assertIn(
            "components",
            results[0]
        )

        self.assertIn(
            "tags",
            results[0]["components"]
        )

        self.assertIn(
            "tempo",
            results[0]["components"]
        )

        self.assertIn(
            "loudness",
            results[0]["components"]
        )

        self.assertIn(
            "key_mode",
            results[0]["components"]
        )

    # =====================================================
    # TEST: RECOMMENDATION RESULTS ARE SAVED
    # =====================================================
    def test_recommendation_results_are_saved(self):

        session = Session.objects.create()

        SessionTrack.objects.create(
            session=session,
            track=self.session_track_one,
            position=1
        )

        results = recommend_track_for_session(
            session,
            limit=2
        )

        # The database should contain the same number of
        # recommendation results returned by the recommender.
        self.assertEqual(
            RecommendationResult.objects.filter(
                session=session
            ).count(),
            len(results)
        )

        # The highest-ranked result should also be stored.
        saved_result = (
            RecommendationResult.objects
            .filter(session=session)
            .order_by("-score")
            .first()
        )

        self.assertEqual(
            saved_result.track,
            self.best_track
        )

    # =====================================================
    # TEST: PREVIOUS RESULTS ARE REPLACED
    # =====================================================
    def test_previous_recommendations_are_replaced(self):

        session = Session.objects.create()

        SessionTrack.objects.create(
            session=session,
            track=self.session_track_one,
            position=1
        )

        # Generate the first recommendation set.
        first_results = recommend_track_for_session(
            session,
            limit=1
        )

        self.assertEqual(
            RecommendationResult.objects.filter(
                session=session
            ).count(),
            1
        )

        # Add another user-selected track.
        SessionTrack.objects.create(
            session=session,
            track=self.session_track_two,
            position=2
        )

        # Generate recommendations again using the updated
        # temporary session context.
        second_results = recommend_track_for_session(
            session,
            limit=2
        )

        # Old results should have been removed and replaced
        # with the current ranking.
        self.assertEqual(
            RecommendationResult.objects.filter(
                session=session
            ).count(),
            len(second_results)
        )

        # We should still have a valid recommendation list.
        self.assertTrue(first_results)
        self.assertTrue(second_results)

    # =====================================================
    # TEST: EMPTY LIST IF NO CANDIDATES EXIST
    # =====================================================
    def test_recommender_returns_empty_list_when_no_candidates_exist(self):

        session = Session.objects.create()

        # Add every available track to the session so there
        # are no remaining recommendation candidates.
        SessionTrack.objects.create(
            session=session,
            track=self.session_track_one,
            position=1
        )

        SessionTrack.objects.create(
            session=session,
            track=self.session_track_two,
            position=2
        )

        SessionTrack.objects.create(
            session=session,
            track=self.best_track,
            position=3
        )

        SessionTrack.objects.create(
            session=session,
            track=self.poor_match_track,
            position=4
        )

        results = recommend_track_for_session(session)

        self.assertEqual(
            results,
            []
        )

    # =====================================================
    # TEST: EMPTY LIST IF SESSION HAS NO TRACKS
    # =====================================================
    def test_recommender_returns_empty_list_for_empty_session(self):

        session = Session.objects.create()

        results = recommend_track_for_session(session)

        self.assertEqual(
            results,
            []
        )