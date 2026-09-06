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
# - exclude artists already represented in the session
# - rank candidate tracks by similarity
# - use multiple session tracks as temporary context
# - apply optional style, tempo and intensity refinements
# - save the current recommendation results
# - return an empty list when no candidates exist
# =========================================================
class RecommenderLogicTest(TestCase):

    # =====================================================
    # SETUP TEST DATA
    # =====================================================
    def setUp(self):

        # -------------------------------------------------
        # Session artist.
        # -------------------------------------------------
        self.artist = Artist.objects.create(
            artist_name="Test Artist"
        )

        # -------------------------------------------------
        # Candidate artists.
        # -------------------------------------------------
        self.best_match_artist = Artist.objects.create(
            artist_name="Best Match Artist"
        )

        self.poor_match_artist = Artist.objects.create(
            artist_name="Poor Match Artist"
        )

        # -------------------------------------------------
        # Genres.
        # -------------------------------------------------
        self.electronic = Genre.objects.create(
            genre="Electronic"
        )

        self.rock = Genre.objects.create(
            genre="Rock"
        )

        # -------------------------------------------------
        # Albums.
        # -------------------------------------------------
        self.album = Album.objects.create(
            album_name="Test Album",
            artist=self.artist
        )

        self.best_match_album = Album.objects.create(
            album_name="Best Match Album",
            artist=self.best_match_artist
        )

        self.poor_match_album = Album.objects.create(
            album_name="Poor Match Album",
            artist=self.poor_match_artist
        )

        # -------------------------------------------------
        # Musical tags.
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

        self.electronic_tag = Tag.objects.create(
            name="electronic",
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
        # Second session track.
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
        # -------------------------------------------------
        self.best_track = Track.objects.create(
            track_name="Best Match Track",
            artist=self.best_match_artist,
            album=self.best_match_album,
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
        # -------------------------------------------------
        self.poor_match_track = Track.objects.create(
            track_name="Poor Match Track",
            artist=self.poor_match_artist,
            album=self.poor_match_album,
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
    # HELPER: CREATE A REFINEMENT TEST CANDIDATE
    # =====================================================
    def _create_refinement_candidate(
        self,
        artist_name,
        track_name,
        tempo=120,
        loudness=-10,
        tags=None,
    ):
        """
        Create an eligible recommendation candidate for
        refinement-specific tests.

        Each candidate receives its own artist and album so
        the session-artist exclusion rule does not interfere
        with the refinement being tested.
        """

        candidate_artist = Artist.objects.create(
            artist_name=artist_name
        )

        candidate_album = Album.objects.create(
            album_name=f"{track_name} Album",
            artist=candidate_artist
        )

        candidate_track = Track.objects.create(
            track_name=track_name,
            artist=candidate_artist,
            album=candidate_album,
            genre=self.rock,
            tempo=tempo,
            loudness=loudness,
            key=5,
            mode=1,
        )

        for tag, weight in tags or []:
            TrackTag.objects.create(
                track=candidate_track,
                tag=tag,
                weight=weight,
                source="test"
            )

        return candidate_track

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

        self.assertTrue(results)

        self.assertEqual(
            results[0]["track"],
            self.best_track
        )

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

        results = recommend_track_for_session(
            session
        )

        recommended_tracks = [
            item["track"]
            for item in results
        ]

        self.assertNotIn(
            self.session_track_one,
            recommended_tracks
        )

    # =====================================================
    # TEST: TRACKS BY SESSION ARTISTS ARE EXCLUDED
    # =====================================================
    def test_recommender_excludes_tracks_by_session_artist(self):

        same_artist_track = Track.objects.create(
            track_name="Same Artist Track",
            artist=self.artist,
            album=self.album,
            genre=self.rock,
            tempo=121,
            loudness=-10,
            key=5,
            mode=1,
        )

        TrackTag.objects.create(
            track=same_artist_track,
            tag=self.rock_tag,
            weight=1.0,
            source="test"
        )

        TrackTag.objects.create(
            track=same_artist_track,
            tag=self.indie_tag,
            weight=0.8,
            source="test"
        )

        session = Session.objects.create()

        SessionTrack.objects.create(
            session=session,
            track=self.session_track_one,
            position=1
        )

        results = recommend_track_for_session(
            session
        )

        recommended_tracks = [
            item["track"]
            for item in results
        ]

        self.assertNotIn(
            same_artist_track,
            recommended_tracks
        )

        self.assertIn(
            self.best_track,
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

        self.assertEqual(
            results[0]["track"],
            self.best_track
        )

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
    # TEST: STYLE REFINEMENT INFLUENCES RANKING
    # =====================================================
    def test_style_refinement_influences_ranking(self):
        """
        Two candidates have otherwise similar characteristics.

        The electronic candidate should receive a style bonus
        when the user explicitly selects "electronic".
        """

        session = Session.objects.create()

        SessionTrack.objects.create(
            session=session,
            track=self.session_track_one,
            position=1
        )

        neutral_candidate = (
            self._create_refinement_candidate(
                artist_name="Neutral Style Artist",
                track_name="Neutral Style Track",
                tempo=120,
                loudness=-10,
                tags=[
                    (
                        self.rock_tag,
                        0.8,
                    ),
                ],
            )
        )

        electronic_candidate = (
            self._create_refinement_candidate(
                artist_name="Electronic Style Artist",
                track_name="Electronic Style Track",
                tempo=120,
                loudness=-10,
                tags=[
                    (
                        self.rock_tag,
                        0.8,
                    ),
                    (
                        self.electronic_tag,
                        1.0,
                    ),
                ],
            )
        )

        results = recommend_track_for_session(
            session,
            limit=10,
            preferences={
                "style": "electronic"
            },
        )

        result_by_track = {
            item["track"]: item
            for item in results
        }

        # Both candidates should be present.
        self.assertIn(
            neutral_candidate,
            result_by_track
        )

        self.assertIn(
            electronic_candidate,
            result_by_track
        )

        # The selected style should give the electronic
        # candidate a positive refinement contribution.
        self.assertGreater(
            result_by_track[
                electronic_candidate
            ]["components"][
                "style_preference"
            ],
            result_by_track[
                neutral_candidate
            ]["components"][
                "style_preference"
            ],
        )

        self.assertGreater(
            result_by_track[
                electronic_candidate
            ]["components"][
                "refinement_bonus"
            ],
            result_by_track[
                neutral_candidate
            ]["components"][
                "refinement_bonus"
            ],
        )

        # The style-matching candidate should receive the
        # higher final score.
        self.assertGreater(
            result_by_track[
                electronic_candidate
            ]["score"],
            result_by_track[
                neutral_candidate
            ]["score"],
        )

    # =====================================================
    # TEST: FASTER TEMPO REFINEMENT INFLUENCES RANKING
    # =====================================================
    def test_faster_tempo_refinement_influences_ranking(self):
        """
        The session track is 120 BPM.

        The candidates are positioned equally around that
        session tempo:

            100 BPM = 20 BPM slower
            140 BPM = 20 BPM faster

        Their normal tempo similarity to the session is
        therefore equal.

        Selecting "faster" should favour the 140 BPM track.
        """

        session = Session.objects.create()

        SessionTrack.objects.create(
            session=session,
            track=self.session_track_one,
            position=1
        )

        slower_candidate = (
            self._create_refinement_candidate(
                artist_name="Slower Candidate Artist",
                track_name="Slower Candidate",
                tempo=100,
                loudness=-10,
                tags=[
                    (
                        self.rock_tag,
                        0.8,
                    ),
                ],
            )
        )

        faster_candidate = (
            self._create_refinement_candidate(
                artist_name="Faster Candidate Artist",
                track_name="Faster Candidate",
                tempo=140,
                loudness=-10,
                tags=[
                    (
                        self.rock_tag,
                        0.8,
                    ),
                ],
            )
        )

        results = recommend_track_for_session(
            session,
            limit=10,
            preferences={
                "tempo": "faster"
            },
        )

        result_by_track = {
            item["track"]: item
            for item in results
        }

        self.assertIn(
            slower_candidate,
            result_by_track
        )

        self.assertIn(
            faster_candidate,
            result_by_track
        )

        # Their base scores should be equal because they
        # are equally distant from the session tempo and
        # otherwise have the same metadata.
        self.assertAlmostEqual(
            result_by_track[
                slower_candidate
            ]["components"]["base_score"],
            result_by_track[
                faster_candidate
            ]["components"]["base_score"],
            places=6,
        )

        # The faster preference should then break the tie.
        self.assertGreater(
            result_by_track[
                faster_candidate
            ]["components"][
                "tempo_preference"
            ],
            result_by_track[
                slower_candidate
            ]["components"][
                "tempo_preference"
            ],
        )

        self.assertGreater(
            result_by_track[
                faster_candidate
            ]["score"],
            result_by_track[
                slower_candidate
            ]["score"],
        )

    # =====================================================
    # TEST: STRONGER INTENSITY REFINEMENT INFLUENCES RANKING
    # =====================================================
    def test_stronger_intensity_refinement_influences_ranking(self):
        """
        The session track has loudness -10 dB.

        The candidates are positioned equally around that
        value:

            -16 dB = softer
             -4 dB = stronger

        Their normal loudness similarity to the session is
        therefore equal.

        Selecting "stronger" should favour the -4 dB track.
        """

        session = Session.objects.create()

        SessionTrack.objects.create(
            session=session,
            track=self.session_track_one,
            position=1
        )

        softer_candidate = (
            self._create_refinement_candidate(
                artist_name="Softer Candidate Artist",
                track_name="Softer Candidate",
                tempo=120,
                loudness=-16,
                tags=[
                    (
                        self.rock_tag,
                        0.8,
                    ),
                ],
            )
        )

        stronger_candidate = (
            self._create_refinement_candidate(
                artist_name="Stronger Candidate Artist",
                track_name="Stronger Candidate",
                tempo=120,
                loudness=-4,
                tags=[
                    (
                        self.rock_tag,
                        0.8,
                    ),
                ],
            )
        )

        results = recommend_track_for_session(
            session,
            limit=10,
            preferences={
                "intensity": "stronger"
            },
        )

        result_by_track = {
            item["track"]: item
            for item in results
        }

        self.assertIn(
            softer_candidate,
            result_by_track
        )

        self.assertIn(
            stronger_candidate,
            result_by_track
        )

        # Their normal scores should be equal before the
        # explicit intensity preference is applied.
        self.assertAlmostEqual(
            result_by_track[
                softer_candidate
            ]["components"]["base_score"],
            result_by_track[
                stronger_candidate
            ]["components"]["base_score"],
            places=6,
        )

        # The stronger preference should break the tie.
        self.assertGreater(
            result_by_track[
                stronger_candidate
            ]["components"][
                "intensity_preference"
            ],
            result_by_track[
                softer_candidate
            ]["components"][
                "intensity_preference"
            ],
        )

        self.assertGreater(
            result_by_track[
                stronger_candidate
            ]["score"],
            result_by_track[
                softer_candidate
            ]["score"],
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

        self.assertEqual(
            RecommendationResult.objects.filter(
                session=session
            ).count(),
            len(results)
        )

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

        SessionTrack.objects.create(
            session=session,
            track=self.session_track_two,
            position=2
        )

        second_results = recommend_track_for_session(
            session,
            limit=2
        )

        self.assertEqual(
            RecommendationResult.objects.filter(
                session=session
            ).count(),
            len(second_results)
        )

        self.assertTrue(first_results)
        self.assertTrue(second_results)

    # =====================================================
    # TEST: EMPTY LIST IF NO CANDIDATES EXIST
    # =====================================================
    def test_recommender_returns_empty_list_when_no_candidates_exist(self):

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

        results = recommend_track_for_session(
            session
        )

        self.assertEqual(
            results,
            []
        )

    # =====================================================
    # TEST: EMPTY LIST IF SESSION HAS NO TRACKS
    # =====================================================
    def test_recommender_returns_empty_list_for_empty_session(self):

        session = Session.objects.create()

        results = recommend_track_for_session(
            session
        )

        self.assertEqual(
            results,
            []
        )