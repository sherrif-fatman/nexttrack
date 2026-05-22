# useful commands docker compose run --rm backend python manage.py test
# Test to check that the recommender API is available

# from rest_framework.test import APITestCase


# class RecommendTrackAPITest(APITestCase):
#     def test_recommend_track_returns_mock_result(self):
#         response = self.client.post(
#             "/api/recommend/",
#             {
#                 "tracks": ["Song A", "Song B"],
#                 "preferences": {"mood": "focused"},
#             },
#             format="json",
#         )

#         self.assertEqual(response.status_code, 200)
#         self.assertIn("recommended_track", response.data)
#         self.assertEqual(response.data["recommended_track"]["title"], "Midnight City")

from rest_framework.test import APITestCase

from recommendations.models import (
    Artist,
    Genre,
    Album,
    Track,
    Session,
    RecommendationResult,
)


# =========================================================
# RECOMMENDATION API TESTS
#
# These tests check that the API endpoint correctly creates
# a session, runs the recommender, and returns a real result.
# =========================================================
class RecommendTrackAPITest(APITestCase):

    # =====================================================
    # SETUP TEST DATA
    # Runs before each test
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
        # Track submitted by the user
        # This should be excluded from recommendation.
        # -------------------------------------------------
        self.input_track = Track.objects.create(
            track_name="Input Track",
            artist=self.artist,
            album=self.album,
            genre=self.genre,
            tempo=120,
            energy=8,
            mood="focused"
        )

        # -------------------------------------------------
        # Best recommendation candidate
        # This should be returned by the API.
        # -------------------------------------------------
        self.recommended_track = Track.objects.create(
            track_name="Kerala",
            artist=self.artist,
            album=self.album,
            genre=self.genre,
            tempo=118,
            energy=7,
            mood="focused"
        )

    # =====================================================
    # TEST: API RETURNS SUCCESSFUL RECOMMENDATION
    # =====================================================
    def test_recommend_track_returns_real_recommendation(self):

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

        self.assertEqual(response.status_code, 200)

        self.assertIn("session_id", response.data)
        self.assertIn("recommended_track", response.data)

        self.assertEqual(
            response.data["recommended_track"]["track_name"],
            "Kerala"
        )

        self.assertEqual(
            response.data["recommended_track"]["artist"],
            "Bonobo"
        )

        self.assertEqual(
            response.data["recommended_track"]["genre"],
            "Electronic"
        )

    # =====================================================
    # TEST: SESSION IS CREATED
    # =====================================================
    def test_api_creates_session(self):

        self.client.post(
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

        self.assertEqual(Session.objects.count(), 1)

    # =====================================================
    # TEST: RECOMMENDATION RESULT IS SAVED
    # =====================================================
    def test_api_saves_recommendation_result(self):

        self.client.post(
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
            RecommendationResult.objects.count(),
            1
        )

        saved_result = RecommendationResult.objects.first()

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
                "preferences": {
                    "genre": "Electronic",
                    "mood": "focused",
                    "energy": 8,
                    "tempo": 120,
                },
            },
            format="json"
        )

        self.assertEqual(response.status_code, 400)

        self.assertIn("error", response.data)