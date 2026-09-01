#test function used for determining similarity scores. These tests
#are run direct from the terminal prompt.


# docker compose exec -T backend python - <<'PY'
# from recommendations.services.similarity import calculate_tag_similarity

# track_a = [
#     {"term": "rock", "weight": 1.0},
#     {"term": "alternative rock", "weight": 0.9},
#     {"term": "indie", "weight": 0.7},
# ]

# track_b = [
#     {"term": "rock", "weight": 0.9},
#     {"term": "alternative rock", "weight": 0.8},
#     {"term": "folk", "weight": 0.6},
# ]

# score = calculate_tag_similarity(track_a, track_b)

# print("Tag similarity:", score)
# print("Percentage:", round(score * 100, 2), "%")
# PY

# docker compose exec -T backend python - <<'PY'
# from recommendations.services.similarity import calculate_tempo_similarity

# tests = [
#     (120, 120),
#     (120, 125),
#     (120, 130),
#     (120, 145),
#     (120, 170),
#     (120, 220),
#     (120, 240),
#     (120, 0),
#     (120, None),
# ]

# for source, candidate in tests:
#     score = calculate_tempo_similarity(source, candidate)

#     print(
#         f"{source} vs {candidate}: "
#         f"{score:.2f} ({score * 100:.0f}%)"
#     )
# PY

# docker compose exec -T backend python - <<'PY'
# from recommendations.services.similarity import calculate_loudness_similarity

# tests = [
#     (-10, -10),
#     (-10, -12),
#     (-10, -15),
#     (-10, -20),
#     (-10, -25),
#     (-10, -30),
#     (-10, None),
# ]

# for source, candidate in tests:
#     score = calculate_loudness_similarity(source, candidate)

#     print(
#         f"{source} vs {candidate}: "
#         f"{score:.2f} ({score * 100:.0f}%)"
#     )
# PY

# docker compose exec -T backend python - <<'PY'
# from recommendations.services.similarity import calculate_key_mode_similarity

# tests = [
#     # Same key, same mode
#     (0, 0, 0, 0),

#     # Same key, different mode
#     (5, 1, 5, 0),

#     # Different key, same mode
#     (5, 1, 7, 1),

#     # Different key, different mode
#     (5, 1, 7, 0),

#     # Valid zero key
#     (0, 1, 0, 1),

#     # Missing data
#     (5, 1, None, 1),
# ]

# for source_key, source_mode, candidate_key, candidate_mode in tests:

#     score = calculate_key_mode_similarity(
#         source_key,
#         source_mode,
#         candidate_key,
#         candidate_mode
#     )

#     print(
#         f"Key {source_key}/{source_mode} "
#         f"vs {candidate_key}/{candidate_mode}: "
#         f"{score:.2f} ({score * 100:.0f}%)"
#     )
# PY

# docker compose exec -T backend python - <<'PY'
# from recommendations.services.similarity import calculate_combined_similarity

# score = calculate_combined_similarity(
#     tag_similarity=0.80,
#     tempo_similarity=0.90,
#     loudness_similarity=0.75,
#     key_mode_similarity=0.50,
# )

# print("Combined similarity:", score)
# print("Percentage:", round(score * 100, 2), "%")
# PY