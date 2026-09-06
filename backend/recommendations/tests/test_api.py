# =========================================================
# RECOMMENDATION API TESTS
#
# These tests check that the API endpoint correctly:
# - creates a session
# - accepts selected track IDs
# - runs the recommender
# - returns ranked recommendations
# - excludes tracks and artists already used in the session
# - saves recommendation results
# - rejects invalid track IDs
# - reuses an existing session for refinement
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
    SessionTrack,
    RecommendationResult,
)


class RecommendTrackAPITest(APITestCase):

    # =====================================================
    # SETUP TEST DATA
    # =====================================================
    def setUp(self):

        # -------------------------------------------------
        # Create artists.
        #
        # The input track and recommendation candidates use
        # different artists. This reflects the recommender's
        # artist-exclusion rule, which prevents artists
        # already represented in the session from appearing
        # in the recommendation candidates.
        # -------------------------------------------------
        self.input_artist = Artist.objects.create(
            artist_name="Input Artist"
        )

        self.recommended_artist = Artist.objects.create(
            artist_name="Recommended Artist"
        )

        self.poor_match_artist = Artist.objects.create(
            artist_name="Poor Match Artist"
        )

        # -------------------------------------------------
        # Create genre.
        # -------------------------------------------------
        self.genre = Genre.objects.create(
            genre="Electronic"
        )

        # -------------------------------------------------
        # Create albums.
        # -------------------------------------------------
        self.input_album = Album.objects.create(
            album_name="Input Album",
            artist=self.input_artist
        )

        self.recommended_album = Album.objects.create(
            album_name="Recommended Album",
            artist=self.recommended_artist
        )

        self.poor_match_album = Album.objects.create(
            album_name="Poor Match Album",
            artist=self.poor_match_artist
        )

        # -------------------------------------------------
        # Create musical tags used by the recommender.
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
        #
        # This track and other tracks by the same artist
        # should be excluded from recommendations.
        # -------------------------------------------------
        self.input_track = Track.objects.create(
            track_name="Input Track",
            artist=self.input_artist,
            album=self.input_album,
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
        # Another track by the input artist.
        #
        # This deliberately looks like a strong match but
        # should be excluded because its artist is already
        # represented in the session.
        # -------------------------------------------------
        self.same_artist_track = Track.objects.create(
            track_name="Same Artist Track",
            artist=self.input_artist,
            album=self.input_album,
            genre=self.genre,
            tempo=119,
            loudness=-10.5,
            key=5,
            mode=1,
        )

        TrackTag.objects.create(
            track=self.same_artist_track,
            tag=self.electronic_tag,
            weight=1.0,
            source="test"
        )

        TrackTag.objects.create(
            track=self.same_artist_track,
            tag=self.ambient_tag,
            weight=0.7,
            source="test"
        )

        # -------------------------------------------------
        # Best eligible recommendation candidate.
        #
        # Similar tags and audio metadata, but from a
        # different artist.
        # -------------------------------------------------
        self.recommended_track = Track.objects.create(
            track_name="Kerala",
            artist=self.recommended_artist,
            album=self.recommended_album,
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
        #
        # Different acoustic values and no matching tags.
        # -------------------------------------------------
        self.poor_match_track = Track.objects.create(
            track_name="Different Track",
            artist=self.poor_match_artist,
            album=self.poor_match_album,
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
                "track_ids": [
                    self.input_track.id
                ],
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
        # Check response structure.
        # -------------------------------------------------
        self.assertIn(
            "session_id",
            response.data
        )

        self.assertIn(
            "recommendations",
            response.data
        )

        recommendations = response.data[
            "recommendations"
        ]

        self.assertTrue(recommendations)

        # -------------------------------------------------
        # Best eligible candidate should appear first.
        # -------------------------------------------------
        first_result = recommendations[0]

        self.assertEqual(
            first_result["track_name"],
            "Kerala"
        )

        self.assertEqual(
            first_result["artist"],
            "Recommended Artist"
        )

        self.assertEqual(
            first_result["genre"],
            "Electronic"
        )

        # -------------------------------------------------
        # Recommendation should expose score and reason.
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
                "track_ids": [
                    self.input_track.id
                ],
                "preferences": {},
            },
            format="json"
        )

        recommendations = response.data[
            "recommendations"
        ]

        recommended_ids = [
            item["id"]
            for item in recommendations
        ]

        self.assertNotIn(
            self.input_track.id,
            recommended_ids
        )

    # =====================================================
    # TEST: SESSION ARTIST IS NOT RETURNED
    # =====================================================
    def test_api_excludes_tracks_by_session_artist(self):

        response = self.client.post(
            "/api/recommend/",
            {
                "track_ids": [
                    self.input_track.id
                ],
                "preferences": {},
            },
            format="json"
        )

        self.assertEqual(
            response.status_code,
            200
        )

        recommendations = response.data[
            "recommendations"
        ]

        recommended_ids = [
            item["id"]
            for item in recommendations
        ]

        # The exact input track must not be returned.
        self.assertNotIn(
            self.input_track.id,
            recommended_ids
        )

        # Another track by the same artist must also not
        # be returned.
        self.assertNotIn(
            self.same_artist_track.id,
            recommended_ids
        )

        # A suitable track by another artist should remain
        # eligible.
        self.assertIn(
            self.recommended_track.id,
            recommended_ids
        )

    # =====================================================
    # TEST: SESSION IS CREATED
    # =====================================================
    def test_api_creates_session(self):

        self.client.post(
            "/api/recommend/",
            {
                "track_ids": [
                    self.input_track.id
                ],
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
                "track_ids": [
                    self.input_track.id
                ],
                "preferences": {},
            },
            format="json"
        )

        recommendations = response.data[
            "recommendations"
        ]

        # The number saved should match the number returned.
        self.assertEqual(
            RecommendationResult.objects.count(),
            len(recommendations)
        )

        # The highest-ranked saved result should be the
        # strongest eligible candidate.
        saved_result = (
            RecommendationResult.objects
            .order_by("-score")
            .first()
        )

        self.assertIsNotNone(
            saved_result
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

    # =====================================================
    # TEST: EXISTING SESSION CAN BE REFINED
    # =====================================================
    def test_existing_session_can_be_refined(self):

        # -------------------------------------------------
        # First request creates the session.
        # -------------------------------------------------
        first_response = self.client.post(
            "/api/recommend/",
            {
                "track_ids": [
                    self.input_track.id
                ],
                "preferences": {},
            },
            format="json"
        )

        self.assertEqual(
            first_response.status_code,
            200
        )

        session_id = first_response.data[
            "session_id"
        ]

        # -------------------------------------------------
        # Second request reuses the same session and adds
        # another user-selected track.
        # -------------------------------------------------
        second_response = self.client.post(
            "/api/recommend/",
            {
                "track_ids": [
                    self.poor_match_track.id
                ],
                "session_id": session_id,
                "preferences": {},
            },
            format="json"
        )

        self.assertEqual(
            second_response.status_code,
            200
        )

        # The API should keep the same session.
        self.assertEqual(
            second_response.data[
                "session_id"
            ],
            session_id
        )

        # Only one session should exist.
        self.assertEqual(
            Session.objects.count(),
            1
        )

        session = Session.objects.get(
            id=session_id
        )

        # Both selected tracks should now belong to the
        # same temporary session.
        self.assertEqual(
            SessionTrack.objects.filter(
                session=session
            ).count(),
            2
        )

        session_track_ids = list(
            SessionTrack.objects.filter(
                session=session
            )
            .order_by("position")
            .values_list(
                "track_id",
                flat=True
            )
        )

        self.assertEqual(
            session_track_ids,
            [
                self.input_track.id,
                self.poor_match_track.id,
            ]
        )

        # Neither user-selected track should appear in the
        # new recommendation set.
        recommended_ids = [
            item["id"]
            for item in second_response.data[
                "recommendations"
            ]
        ]

        self.assertNotIn(
            self.input_track.id,
            recommended_ids
        )

        self.assertNotIn(
            self.poor_match_track.id,
            recommended_ids
        )

        # The artists represented by the session should
        # also be excluded. The deliberately-created track
        # by the input artist therefore cannot appear.
        self.assertNotIn(
            self.same_artist_track.id,
            recommended_ids
        )