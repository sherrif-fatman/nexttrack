"""
tag_filter.py

Helper functions for filtering Million Song Dataset artist terms.

The MSD artist_terms field contains a mixture of:
- useful musical genres and styles
- locations and nationalities
- decades
- vocalist descriptions
- other non-musical descriptors

NextTrack uses a curated allow-list to retain terms considered useful
for musical similarity. The vocabulary is a NextTrack design decision
rather than an official Million Song Dataset genre classification.

Data source:
Bertin-Mahieux, T., Ellis, D.P.W., Whitman, B. and Lamere, P. (2011).
The Million Song Dataset. Proceedings of the 12th International Society
for Music Information Retrieval Conference (ISMIR 2011).
"""


# Curated set of musical genres, subgenres and style descriptors.
#
# Only terms in this set will be kept by the recommendation system.
# Everything else is ignored.
#
# The vocabulary is intentionally restricted to terms treated as
# musically useful for NextTrack's similarity calculations.
MUSICAL_TERMS = {

    # ------------------------------------------------------------
    # Rock
    # ------------------------------------------------------------
    "rock",
    "alternative rock",
    "alternative",
    "indie",
    "indie rock",
    "classic rock",
    "hard rock",
    "progressive rock",
    "progressive",
    "psychedelic",
    "psychedelic rock",
    "instrumental rock",
    "jazz rock",
    "soft rock",
    "pop rock",
    "blues rock",

    # ------------------------------------------------------------
    # Punk / Hardcore
    # ------------------------------------------------------------
    "punk",
    "punk rock",
    "hardcore",
    "hardcore punk",
    "post-hardcore",
    "alternative punk rock",
    "screamo",
    "metalcore",
    "grindcore",
    "postcore",

    # ------------------------------------------------------------
    # Metal
    # ------------------------------------------------------------
    "metal",
    "heavy metal",
    "death metal",
    "black metal",
    "doom metal",
    "progressive metal",
    "thrash metal",
    "speed metal",
    "sludge",

    # ------------------------------------------------------------
    # Pop
    # ------------------------------------------------------------
    "pop",
    "dance pop",
    "british pop",
    "french pop",
    "latin pop",
    "pop rap",

    # ------------------------------------------------------------
    # Electronic / Dance
    # ------------------------------------------------------------
    "electronic",
    "electronica",
    "ambient",
    "downtempo",
    "house",
    "disco",
    "dance",
    "chill-out",

    # ------------------------------------------------------------
    # Hip Hop / Rap
    # ------------------------------------------------------------
    "hip hop",
    "hip-hop",
    "rap",
    "hardcore hip hop",
    "underground rap",

    # ------------------------------------------------------------
    # Jazz / Blues
    # ------------------------------------------------------------
    "jazz",
    "jazz fusion",
    "fusion",
    "nu jazz",
    "contemporary jazz",
    "blues",

    # ------------------------------------------------------------
    # Soul / Funk / Reggae
    # ------------------------------------------------------------
    "soul",
    "funk",
    "reggae",
    "rnb",

    # ------------------------------------------------------------
    # Folk / Country / Traditional
    # ------------------------------------------------------------
    "folk",
    "acoustic folk",
    "country",
    "celtic",
    "traditional",
    "world",
    "world music",
    "early music",
    "renaissance",
    "mediaeval",

    # ------------------------------------------------------------
    # Classical / Orchestral / Stage
    # ------------------------------------------------------------
    "classical",
    "modern classical",
    "orchestra",
    "orchestral pop",
    "opera",
    "soundtrack",
    "musical theater",
    "broadway",
    "waltz",

    # ------------------------------------------------------------
    # General musical characteristics
    # ------------------------------------------------------------
    "acoustic",
    "instrumental",
    "experimental",
    "singer-songwriter",
    "vocal",
}


def normalise_term(term):
    """
    Convert an artist term into a standard form.

    MSD data may contain byte strings instead of normal Python strings,
    so byte values are decoded first.

    Terms are then:
    - converted to strings
    - stripped of whitespace
    - converted to lowercase

    This makes comparisons consistent.
    """

    # Decode byte strings returned by the HDF5 dataset.
    if isinstance(term, bytes):
        term = term.decode(
            "utf-8",
            errors="ignore"
        )

    # Normalise formatting so terms can be compared reliably.
    return str(term).strip().lower()


def is_musical_term(term):
    """
    Check whether an MSD artist term is useful for recommendation.

    Returns True if the normalised term exists in the curated
    MUSICAL_TERMS vocabulary.
    """

    # Normalise the term before checking the vocabulary.
    term = normalise_term(term)

    # Only terms in the allow-list are accepted.
    return term in MUSICAL_TERMS


def filter_artist_terms(terms, weights=None):
    """
    Filter MSD artist terms so that only useful musical terms remain.

    Parameters
    ----------
    terms:
        Iterable containing MSD artist terms.

    weights:
        Optional iterable containing the corresponding
        artist_terms_weight values.

    If weights are not provided:
        A simple list of accepted musical terms is returned.

    Example:

        [
            "rock",
            "indie",
            "ambient"
        ]

    If weights are provided:
        A list of dictionaries is returned containing both
        the term and its MSD weight.

    Example:

        [
            {"term": "rock", "weight": 0.95},
            {"term": "indie", "weight": 0.82}
        ]
    """

    # ------------------------------------------------------------
    # Case 1:
    # No weights supplied.
    #
    # Simply return the terms that exist in the curated vocabulary.
    # ------------------------------------------------------------
    if weights is None:

        return [
            normalise_term(term)
            for term in terms
            if is_musical_term(term)
        ]

    # List used to store accepted terms and their weights.
    filtered = []

    # ------------------------------------------------------------
    # Terms and weights correspond by position in the MSD arrays.
    #
    # zip() lets us process both values together.
    # ------------------------------------------------------------
    for term, weight in zip(terms, weights):

        # Convert the term into a consistent lowercase string.
        term = normalise_term(term)

        # Ignore anything that is not part of our musical vocabulary.
        if term not in MUSICAL_TERMS:
            continue

        # Keep the musical term and its MSD-provided weight.
        filtered.append({
            "term": term,
            "weight": float(weight),
        })

    # ------------------------------------------------------------
    # Sort the accepted terms so the strongest MSD descriptors
    # appear first.
    #
    # Example:
    #
    # progressive metal  1.00
    # death metal        0.99
    # heavy metal        0.96
    # ------------------------------------------------------------
    filtered.sort(
        key=lambda item: item["weight"],
        reverse=True
    )

    return filtered