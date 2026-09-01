# =========================================================
# RECOMMENDATION API TESTS
#
# These tests check that the API endpoint correctly:
# - creates a session
# - accepts selected track IDs
# - runs the recommender
# - returns ranked recommendations
# - saves recommendation results
# - rejects invalid track IDs
# =========================================================

from rest_framework.test import APITestCase

from recommendations.models import (
    Artist,
    Genre,
    Album,
    Track,
    Tag,
    TrackTag,
    Session,
    RecommendationResult,
)


class RecommendTrackAPITest(APITestCase):

    # =====================================================
    # SETUP TEST DATA
    # =====================================================
    def setUp(self):

        # -------------------------------------------------
        # Create artist
        # -------------------------------------------------
        self.artist = Artist.objects.create(
            artist_name="Bonobo"
        )

        # -------------------------------------------------
        # Create genre
        # -------------------------------------------------
        self.genre = Genre.objects.create(
            genre="Electronic"
        )

        # -------------------------------------------------
        # Create album
        # -------------------------------------------------
        self.album = Album.objects.create(
            album_name="Migration",
            artist=self.artist
        )

        # -------------------------------------------------
        # Create musical tags used by the recommender
        # -------------------------------------------------
        self.electronic_tag = Tag.objects.create(
            name="electronic",
            category="genre"
        )

        self.ambient_tag = Tag.objects.create(
            name="ambient",
            category="genre"
        )

        # -------------------------------------------------
        # Track submitted by the user.
        # This should be excluded from recommendations.
        # -------------------------------------------------
        self.input_track = Track.objects.create(
            track_name="Input Track",
            artist=self.artist,
            album=self.album,
            genre=self.genre,
            tempo=120,
            loudness=-10,
            key=5,
            mode=1,
        )

        TrackTag.objects.create(
            track=self.input_track,
            tag=self.electronic_tag,
            weight=1.0,
            source="test"
        )

        TrackTag.objects.create(
            track=self.input_track,
            tag=self.ambient_tag,
            weight=0.7,
            source="test"
        )

        # -------------------------------------------------
        # Best recommendation candidate.
        # Similar tags and audio metadata.
        # -------------------------------------------------
        self.recommended_track = Track.objects.create(
            track_name="Kerala",
            artist=self.artist,
            album=self.album,
            genre=self.genre,
            tempo=118,
            loudness=-11,
            key=5,
            mode=1,
        )

        TrackTag.objects.create(
            track=self.recommended_track,
            tag=self.electronic_tag,
            weight=0.95,
            source="test"
        )

        TrackTag.objects.create(
            track=self.recommended_track,
            tag=self.ambient_tag,
            weight=0.65,
            source="test"
        )

        # -------------------------------------------------
        # Weaker recommendation candidate.
        # -------------------------------------------------
        self.poor_match_track = Track.objects.create(
            track_name="Different Track",
            artist=self.artist,
            album=self.album,
            genre=self.genre,
            tempo=80,
            loudness=-25,
            key=9,
            mode=0,
        )

    # =====================================================
    # TEST: API RETURNS SUCCESSFUL RECOMMENDATIONS
    # =====================================================
    def test_recommend_track_returns_real_recommendations(self):

        response = self.client.post(
            "/api/recommend/",
            {
                "track_ids": [self.input_track.id],
                "preferences": {
                    "genre": "Electronic",
                    "mood": "focused",
                    "energy": 8,
                    "tempo": 120,
                },
            },
            format="json"
        )

        self.assertEqual(
            response.status_code,
            200
        )

        # -------------------------------------------------
        # Check response structure
        # -------------------------------------------------
        self.assertIn(
            "session_id",
            response.data
        )

        self.assertIn(
            "recommendations",
            response.data
        )

        recommendations = response.data["recommendations"]

        self.assertTrue(recommendations)

        # -------------------------------------------------
        # Best candidate should appear first
        # -------------------------------------------------
        first_result = recommendations[0]

        self.assertEqual(
            first_result["track_name"],
            "Kerala"
        )

        self.assertEqual(
            first_result["artist"],
            "Bonobo"
        )

        self.assertEqual(
            first_result["genre"],
            "Electronic"
        )

        # -------------------------------------------------
        # Recommendation should expose score and reason
        # -------------------------------------------------
        self.assertIn(
            "score",
            first_result
        )

        self.assertIn(
            "reason",
            first_result
        )

    # =====================================================
    # TEST: INPUT TRACK IS NOT RETURNED
    # =====================================================
    def test_api_excludes_input_track_from_recommendations(self):

        response = self.client.post(
            "/api/recommend/",
            {
                "track_ids": [self.input_track.id],
                "preferences": {},
            },
            format="json"
        )

        recommendations = response.data["recommendations"]

        recommended_ids = [
            item["id"]
            for item in recommendations
        ]

        self.assertNotIn(
            self.input_track.id,
            recommended_ids
        )

    # =====================================================
    # TEST: SESSION IS CREATED
    # =====================================================
    def test_api_creates_session(self):

        self.client.post(
            "/api/recommend/",
            {
                "track_ids": [self.input_track.id],
                "preferences": {},
            },
            format="json"
        )

        self.assertEqual(
            Session.objects.count(),
            1
        )

    # =====================================================
    # TEST: RECOMMENDATION RESULTS ARE SAVED
    # =====================================================
    def test_api_saves_recommendation_results(self):

        response = self.client.post(
            "/api/recommend/",
            {
                "track_ids": [self.input_track.id],
                "preferences": {},
            },
            format="json"
        )

        recommendations = response.data["recommendations"]

        # The number saved should match the number returned.
        self.assertEqual(
            RecommendationResult.objects.count(),
            len(recommendations)
        )

        # The highest-ranked saved result should be Kerala.
        saved_result = (
            RecommendationResult.objects
            .order_by("-score")
            .first()
        )

        self.assertEqual(
            saved_result.track,
            self.recommended_track
        )

    # =====================================================
    # TEST: INVALID TRACK ID RETURNS 400
    # =====================================================
    def test_invalid_track_id_returns_error(self):

        response = self.client.post(
            "/api/recommend/",
            {
                "track_ids": [9999],
                "preferences": {},
            },
            format="json"
        )

        self.assertEqual(
            response.status_code,
            400
        )

        self.assertIn(
            "error",
            response.data
        )