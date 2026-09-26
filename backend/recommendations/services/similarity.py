"""
similarity.py

Similarity functions used by the NextTrack recommendation engine.

The functions in this module calculate individual similarity scores
between tracks.

Keeping these calculations separate from recommender.py makes the
recommendation logic easier to test, explain and adjust.

The weighted Jaccard formulation used for artist-term similarity follows
the weighted-set definition described by Manasse, McSherry and Talwar
(2010), using summed element-wise minima over summed maxima.

Reference:
Manasse, M., McSherry, F. and Talwar, K. (2010).
Consistent Weighted Sampling. Microsoft Research Technical Report
MSR-TR-2010-73.
"""


def calculate_tag_similarity(source_tags, candidate_tags):
    """
    Calculate weighted similarity between two sets of artist tags.

    Each tag should be represented as a dictionary containing:

        {
            "term": "rock",
            "weight": 0.95
        }

    Similarity is based on shared musical terms.

    For each shared term, the smaller of the two weights is used.
    This prevents a tag from contributing more similarity than the
    weaker track association supports.

    The shared weight is then divided by the total weight across both
    tracks using a weighted Jaccard-style calculation.

    Result:
        0.0 = no musical terms in common
        1.0 = identical weighted tag profiles
    """

    # ------------------------------------------------------------
    # Return zero if either track has no usable tags.
    #
    # Without tags there is no meaningful tag similarity to compare.
    # ------------------------------------------------------------
    if not source_tags or not candidate_tags:
        return 0.0

    # ------------------------------------------------------------
    # Convert each list of dictionaries into a lookup dictionary.
    #
    # Example:
    #
    # [
    #     {"term": "rock", "weight": 1.0},
    #     {"term": "indie", "weight": 0.8}
    # ]
    #
    # becomes:
    #
    # {
    #     "rock": 1.0,
    #     "indie": 0.8
    # }
    #
    # This makes comparing matching terms much easier.
    # ------------------------------------------------------------
    source_lookup = {
        item["term"]: float(item["weight"])
        for item in source_tags
    }

    candidate_lookup = {
        item["term"]: float(item["weight"])
        for item in candidate_tags
    }

    # ------------------------------------------------------------
    # Find every unique term appearing in either track.
    # ------------------------------------------------------------
    all_terms = set(source_lookup) | set(candidate_lookup)

    # Running totals used for the weighted similarity calculation.
    shared_weight = 0.0
    total_weight = 0.0

    # ------------------------------------------------------------
    # Compare the two tracks term by term.
    #
    # For a shared term:
    # - min() contributes to the overlap
    # - max() contributes to the total possible similarity
    #
    # Example:
    #
    # Track A rock weight = 1.0
    # Track B rock weight = 0.8
    #
    # Shared contribution = 0.8
    # Total contribution  = 1.0
    #
    # If a term only exists on one track, the shared contribution
    # is zero but it still contributes to the total.
    # ------------------------------------------------------------
    for term in all_terms:

        source_weight = source_lookup.get(term, 0.0)
        candidate_weight = candidate_lookup.get(term, 0.0)

        shared_weight += min(
            source_weight,
            candidate_weight
        )

        total_weight += max(
            source_weight,
            candidate_weight
        )

    # Prevent division by zero if all supplied weights are zero.
    if total_weight == 0:
        return 0.0

    # ------------------------------------------------------------
    # Weighted Jaccard similarity.
    #
    # The result naturally falls between 0 and 1.
    # ------------------------------------------------------------
    similarity = shared_weight / total_weight

    return similarity

def calculate_tempo_similarity(source_tempo, candidate_tempo):
    """
    Calculate similarity between two track tempos.

    Tempo is measured in beats per minute (BPM).

    Tracks with very similar tempos should receive a score close to 1,
    while tracks with very different tempos should receive a score
    closer to 0.

    Result:
        0.0 = very different tempo
        1.0 = identical tempo
    """

    # ------------------------------------------------------------
    # If either tempo value is missing, there is no meaningful
    # comparison to make.
    # ------------------------------------------------------------
    if source_tempo is None or candidate_tempo is None:
        return 0.0

    # Convert values to floats in case they come from Decimal,
    # NumPy, or database numeric types.
    source_tempo = float(source_tempo)
    candidate_tempo = float(candidate_tempo)

    # ------------------------------------------------------------
    # A tempo of zero in the MSD represents an unusable value rather
    # than a meaningful musical tempo, so it should not contribute
    # to similarity.
    # ------------------------------------------------------------
    if source_tempo <= 0 or candidate_tempo <= 0:
        return 0.0

    # Calculate the absolute difference in BPM.
    tempo_difference = abs(
        source_tempo - candidate_tempo
    )

    # ------------------------------------------------------------
    # Treat differences of 100 BPM or more as completely dissimilar.
    #
    # Below that threshold, similarity decreases linearly.
    #
    # Examples:
    #
    # 0 BPM difference   -> 1.00
    # 10 BPM difference  -> 0.90
    # 25 BPM difference  -> 0.75
    # 50 BPM difference  -> 0.50
    # 100 BPM difference -> 0.00
    # ------------------------------------------------------------
    maximum_difference = 100.0

    similarity = 1.0 - (
        tempo_difference / maximum_difference
    )

    # Ensure the returned value never falls below zero.
    similarity = max(
        0.0,
        similarity
    )

    return similarity

def calculate_loudness_similarity(source_loudness, candidate_loudness):
    """
    Calculate similarity between two track loudness values.

    MSD loudness values are measured in decibels (dB) and are
    typically negative numbers.

    Tracks with similar loudness values should receive a score close
    to 1, while tracks with very different loudness values should
    receive a score closer to 0.

    Result:
        0.0 = very different loudness
        1.0 = identical loudness
    """

    # ------------------------------------------------------------
    # If either loudness value is missing, there is no meaningful
    # comparison to make.
    # ------------------------------------------------------------
    if source_loudness is None or candidate_loudness is None:
        return 0.0

    # Convert values to floats in case they come from Decimal,
    # NumPy, or database numeric types.
    source_loudness = float(source_loudness)
    candidate_loudness = float(candidate_loudness)

    # Calculate the absolute difference in decibels.
    loudness_difference = abs(
        source_loudness - candidate_loudness
    )

    # ------------------------------------------------------------
    # Treat differences of 20 dB or more as completely dissimilar.
    #
    # Below that threshold, similarity decreases linearly.
    #
    # Examples:
    #
    # 0 dB difference   -> 1.00
    # 2 dB difference   -> 0.90
    # 5 dB difference   -> 0.75
    # 10 dB difference  -> 0.50
    # 20 dB difference  -> 0.00
    # ------------------------------------------------------------
    maximum_difference = 20.0

    similarity = 1.0 - (
        loudness_difference / maximum_difference
    )

    # Ensure the returned value never falls below zero.
    similarity = max(
        0.0,
        similarity
    )

    return similarity

def calculate_key_mode_similarity(
    source_key,
    source_mode,
    candidate_key,
    candidate_mode
):
    """
    Calculate similarity between two tracks based on musical key
    and mode.

    MSD key values use integers from 0 to 11, representing the
    twelve pitch classes.

    MSD mode values are:
        0 = minor
        1 = major

    This function gives:
        1.0  = same key and same mode
        0.75 = same key but different mode
        0.50 = different key but same mode
        0.0  = different key and different mode

    Key/mode similarity will later be given a smaller overall weight
    than tags, tempo and loudness.
    """

    # ------------------------------------------------------------
    # If any value is missing, we cannot make a complete
    # key/mode comparison.
    # ------------------------------------------------------------
    if (
        source_key is None
        or source_mode is None
        or candidate_key is None
        or candidate_mode is None
    ):
        return 0.0

    # Convert values to integers so comparisons remain consistent.
    source_key = int(source_key)
    source_mode = int(source_mode)
    candidate_key = int(candidate_key)
    candidate_mode = int(candidate_mode)

    # ------------------------------------------------------------
    # IMPORTANT:
    #
    # key = 0 and mode = 0 are both valid MSD values.
    #
    # Therefore we must NOT treat zero as missing data.
    # ------------------------------------------------------------

    same_key = source_key == candidate_key
    same_mode = source_mode == candidate_mode

    # Same key and same mode gives the strongest match.
    if same_key and same_mode:
        return 1.0

    # Same key but different major/minor mode.
    if same_key:
        return 0.75

    # Different key but same major/minor mode.
    if same_mode:
        return 0.50

    # Neither key nor mode matches.
    return 0.0

def calculate_combined_similarity(
    tag_similarity,
    tempo_similarity,
    loudness_similarity,
    key_mode_similarity
):
    """
    Combine individual similarity scores into one final score.

    Each individual similarity value should be between 0.0 and 1.0.

    The current weighting gives the greatest importance to musical
    genre/style tags, while tempo, loudness and key/mode provide
    additional refinement.

    Weighting:
        tags        = 50%
        tempo       = 20%
        loudness    = 20%
        key / mode  = 10%

    Result:
        0.0 = very weak overall similarity
        1.0 = maximum overall similarity
    """

    # ------------------------------------------------------------
    # Weight values used by the recommendation algorithm.
    #
    # Keeping these values explicit makes the recommendation logic
    # transparent and easy to adjust during evaluation.
    # ------------------------------------------------------------
    tag_weight = 0.50
    tempo_weight = 0.20
    loudness_weight = 0.20
    key_mode_weight = 0.10

    # ------------------------------------------------------------
    # Multiply each similarity score by its corresponding weight.
    # ------------------------------------------------------------
    weighted_tag_score = (
        float(tag_similarity) * tag_weight
    )

    weighted_tempo_score = (
        float(tempo_similarity) * tempo_weight
    )

    weighted_loudness_score = (
        float(loudness_similarity) * loudness_weight
    )

    weighted_key_mode_score = (
        float(key_mode_similarity) * key_mode_weight
    )

    # ------------------------------------------------------------
    # Add the weighted components together.
    #
    # Because the weights total 1.0, the combined result will also
    # remain between 0.0 and 1.0.
    # ------------------------------------------------------------
    combined_score = (
        weighted_tag_score
        + weighted_tempo_score
        + weighted_loudness_score
        + weighted_key_mode_score
    )

    return combined_score