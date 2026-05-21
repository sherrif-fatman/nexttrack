# useful commands docker compose run --rm backend python manage.py test
# Test to check that the recommender API is available

from rest_framework.test import APITestCase


class RecommendTrackAPITest(APITestCase):
    def test_recommend_track_returns_mock_result(self):
        response = self.client.post(
            "/api/recommend/",
            {
                "tracks": ["Song A", "Song B"],
                "preferences": {"mood": "focused"},
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("recommended_track", response.data)
        self.assertEqual(response.data["recommended_track"]["title"], "Midnight City")