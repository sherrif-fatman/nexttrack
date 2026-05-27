"use client";

import { useState } from "react";

type Recommendation = {
  id: number;
  track_name: string;
  artist: string;
  album: string | null;
  genre: string | null;
  tempo: number | null;
  energy: number | null;
  mood: string;
  score: number | null;
  reason: string;
};

type RecommendationResult = {
  session_id: number;
  recommendations: Recommendation[];
};

type TrackSearchResult = {
  id: number;
  track_name: string;
  artist: string;
  album: string | null;
  genre: string | null;
};

export default function Home() {
  // =====================================================
  // RECOMMENDER STATE
  // =====================================================
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<TrackSearchResult[]>([]);
  const [selectedTrack, setSelectedTrack] = useState<TrackSearchResult | null>(
    null
  );

  const [genre, setGenre] = useState("");
  const [mood, setMood] = useState("");
  const [energy, setEnergy] = useState("");
  const [tempo, setTempo] = useState("");

  const [result, setResult] = useState<RecommendationResult | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // =====================================================
  // FEEDBACK STATE
  // =====================================================
  const [recommendationRelevance, setRecommendationRelevance] = useState("3");
  const [explanationClarity, setExplanationClarity] = useState("3");
  const [interfaceEaseOfUse, setInterfaceEaseOfUse] = useState("3");
  const [searchClarity, setSearchClarity] = useState("3");
  const [comments, setComments] = useState("");
  const [feedbackMessage, setFeedbackMessage] = useState("");

  // =====================================================
  // TRACK SEARCH HANDLER
  // Searches backend by track, artist or album
  // =====================================================
  async function handleTrackSearch(query: string) {
    setSearchQuery(query);
    setSelectedTrack(null);

    if (query.trim().length < 2) {
      setSearchResults([]);
      return;
    }

    try {
      const response = await fetch(
        `http://localhost:8000/api/tracks/search/?q=${encodeURIComponent(
          query
        )}`
      );

      const data = await response.json();
      setSearchResults(data);
    } catch {
      setSearchResults([]);
    }
  }

  // =====================================================
  // RECOMMENDATION SUBMIT HANDLER
  // Sends selected track and preferences to Django API
  // =====================================================
  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setError("");
    setResult(null);
    setFeedbackMessage("");

    if (!selectedTrack) {
      setError("Please search for and select a track first.");
      return;
    }

    setLoading(true);

    try {
      const response = await fetch("http://localhost:8000/api/recommend/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          track_ids: [selectedTrack.id],
          preferences: {
            genre,
            mood,
            energy: energy ? Number(energy) : null,
            tempo: tempo ? Number(tempo) : null,
          },
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        setError(data.error || "Something went wrong.");
        return;
      }

      setResult(data);
    } catch {
      setError("Could not connect to the backend API.");
    } finally {
      setLoading(false);
    }
  }

  // =====================================================
  // FEEDBACK SUBMIT HANDLER
  // Sends prototype testing feedback to Django API
  // =====================================================
  async function handleFeedbackSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setFeedbackMessage("");

    if (!result?.session_id) {
      setFeedbackMessage("Please generate recommendations before submitting feedback.");
      return;
    }

    try {
      const response = await fetch("http://localhost:8000/api/feedback/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          session_id: result.session_id,
          recommendation_relevance: Number(recommendationRelevance),
          explanation_clarity: Number(explanationClarity),
          interface_ease_of_use: Number(interfaceEaseOfUse),
          search_clarity: Number(searchClarity),
          comments,
        }),
      });

      if (!response.ok) {
        setFeedbackMessage("Feedback could not be submitted.");
        return;
      }

      setFeedbackMessage("Feedback submitted successfully.");
      setComments("");
    } catch {
      setFeedbackMessage("Could not connect to the feedback API.");
    }
  }

  return (
    <main className="min-h-screen bg-slate-100 p-8 text-blue-950">
      {/* =================================================
          TWO COLUMN PAGE LAYOUT
      ================================================== */}
      <div className="mx-auto grid max-w-7xl grid-cols-1 gap-8 lg:grid-cols-2">
        {/* =================================================
            LEFT COLUMN: TESTING + FEEDBACK
        ================================================== */}
        <section className="rounded-2xl border border-blue-900 bg-white p-6 shadow-lg">
          <h2 className="mb-4 text-2xl font-bold">Prototype Testing</h2>

          <p className="mb-4 text-sm leading-relaxed">
            Please test the music recommendation prototype by searching for
            tracks and reviewing the recommendations returned by the system.
          </p>

          <ol className="mb-6 list-decimal space-y-2 pl-5 text-sm">
            <li>Search for a track, artist or album.</li>
            <li>Select one of the search results.</li>
            <li>Optionally choose recommendation preferences.</li>
            <li>Submit the recommendation request.</li>
            <li>Review the recommendation list.</li>
            <li>Evaluate the recommendation quality.</li>
            <li>Submit feedback using the form below.</li>
          </ol>

          {/* =================================================
              FEEDBACK FORM
          ================================================== */}
          <form onSubmit={handleFeedbackSubmit} className="space-y-4">
            <h3 className="text-xl font-semibold">Submit Feedback</h3>

            <div>
              <label className="mb-2 block text-sm font-medium">
                Recommendation Relevance (1-5)
              </label>
              <input
                type="number"
                min="1"
                max="5"
                value={recommendationRelevance}
                onChange={(event) =>
                  setRecommendationRelevance(event.target.value)
                }
                className="w-full rounded-lg border border-blue-900 p-3"
              />
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium">
                Explanation Clarity (1-5)
              </label>
              <input
                type="number"
                min="1"
                max="5"
                value={explanationClarity}
                onChange={(event) => setExplanationClarity(event.target.value)}
                className="w-full rounded-lg border border-blue-900 p-3"
              />
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium">
                Interface Ease of Use (1-5)
              </label>
              <input
                type="number"
                min="1"
                max="5"
                value={interfaceEaseOfUse}
                onChange={(event) => setInterfaceEaseOfUse(event.target.value)}
                className="w-full rounded-lg border border-blue-900 p-3"
              />
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium">
                Search Clarity (1-5)
              </label>
              <input
                type="number"
                min="1"
                max="5"
                value={searchClarity}
                onChange={(event) => setSearchClarity(event.target.value)}
                className="w-full rounded-lg border border-blue-900 p-3"
              />
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium">Comments</label>
              <textarea
                rows={5}
                value={comments}
                onChange={(event) => setComments(event.target.value)}
                className="w-full rounded-lg border border-blue-900 p-3"
                placeholder="Enter any feedback about recommendation quality or usability..."
              />
            </div>

            <button
              type="submit"
              className="rounded-xl bg-blue-900 px-6 py-3 text-white hover:bg-blue-800"
            >
              Submit Feedback
            </button>

            {feedbackMessage && (
              <p className="text-sm font-medium text-blue-900">
                {feedbackMessage}
              </p>
            )}
          </form>
        </section>

        {/* =================================================
            RIGHT COLUMN: RECOMMENDER
        ================================================== */}
        <section className="rounded-2xl border border-blue-900 bg-white p-6 shadow-lg">
          <h1 className="mb-2 text-4xl font-bold">NextTrack</h1>

          <p className="mb-8 text-blue-900">
            Prototype session-based music recommendation interface.
          </p>

          {/* =================================================
              RECOMMENDER FORM
          ================================================== */}
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="mb-2 block text-sm font-medium">
                Search by track, artist or album
              </label>

              <input
                value={searchQuery}
                onChange={(event) => handleTrackSearch(event.target.value)}
                className="w-full rounded-lg border border-blue-900 p-3"
                placeholder="Example: Iron Maiden"
              />

              {searchResults.length > 0 && (
                <div className="mt-2 rounded-lg border border-blue-200 bg-white">
                  {searchResults.map((track) => (
                    <button
                      key={track.id}
                      type="button"
                      onClick={() => {
                        setSelectedTrack(track);
                        setSearchQuery(`${track.track_name} - ${track.artist}`);
                        setSearchResults([]);
                      }}
                      className="block w-full border-b border-blue-100 p-3 text-left hover:bg-blue-50"
                    >
                      <span className="font-semibold">{track.track_name}</span>
                      <span className="block text-sm text-blue-900">
                        {track.artist}
                        {track.album && ` — ${track.album}`}
                      </span>
                    </button>
                  ))}
                </div>
              )}

              {selectedTrack && (
                <p className="mt-2 text-sm text-green-700">
                  Selected: {selectedTrack.track_name} by {selectedTrack.artist}
                </p>
              )}
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium">
                Genre Preference
              </label>
              <input
                value={genre}
                onChange={(event) => setGenre(event.target.value)}
                className="w-full rounded-lg border border-blue-900 p-3"
                placeholder="Example: rock"
              />
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium">
                Mood Preference
              </label>
              <input
                value={mood}
                onChange={(event) => setMood(event.target.value)}
                className="w-full rounded-lg border border-blue-900 p-3"
                placeholder="Optional"
              />
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium">
                Energy Preference
              </label>
              <input
                type="number"
                min="1"
                max="10"
                value={energy}
                onChange={(event) => setEnergy(event.target.value)}
                className="w-full rounded-lg border border-blue-900 p-3"
                placeholder="Optional"
              />
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium">
                Tempo Preference
              </label>
              <input
                type="number"
                min="1"
                value={tempo}
                onChange={(event) => setTempo(event.target.value)}
                className="w-full rounded-lg border border-blue-900 p-3"
                placeholder="Optional"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-blue-900 p-3 font-semibold text-white hover:bg-blue-800 disabled:opacity-50"
            >
              {loading ? "Finding recommendations..." : "Recommend Tracks"}
            </button>
          </form>

          {/* =================================================
              ERROR MESSAGE
          ================================================== */}
          {error && (
            <div className="mt-6 rounded-xl border border-red-700 bg-red-100 p-4 text-red-700">
              {error}
            </div>
          )}

          {/* =================================================
              RECOMMENDATION RESULTS
          ================================================== */}
          {result && result.recommendations.length > 0 && (
            <div className="mt-6 rounded-2xl border border-blue-900 bg-white p-6">
              <h2 className="mb-4 text-2xl font-bold">Recommended Tracks</h2>

              <div className="space-y-6">
                {result.recommendations.map((track) => (
                  <div key={track.id} className="border-b border-blue-200 pb-4">
                    <p className="text-xl font-semibold">{track.track_name}</p>

                    <p className="text-blue-900">
                      {track.artist}
                      {track.album && ` — ${track.album}`}
                    </p>

                    <div className="mt-4 space-y-1 text-sm text-blue-900">
                      <p>Genre: {track.genre}</p>
                      <p>Mood: {track.mood || "Not available"}</p>
                      <p>Energy: {track.energy ?? "Not available"}</p>
                      <p>Tempo: {track.tempo ?? "Not available"}</p>
                      <p>Score: {track.score}</p>
                    </div>

                    <p className="mt-4 text-blue-900">
                      Reason: {track.reason}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
