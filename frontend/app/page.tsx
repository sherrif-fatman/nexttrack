"use client";

import { useState } from "react";

type RecommendationResult = {
  session_id: number;
  recommended_track: {
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
};

export default function Home() {
  const [trackId, setTrackId] = useState("1");
  const [genre, setGenre] = useState("Electronic");
  const [mood, setMood] = useState("focused");
  const [energy, setEnergy] = useState("8");
  const [tempo, setTempo] = useState("120");

  const [result, setResult] = useState<RecommendationResult | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response = await fetch("http://localhost:8000/api/recommend/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          track_ids: [Number(trackId)],
          preferences: {
            genre,
            mood,
            energy: Number(energy),
            tempo: Number(tempo),
          },
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        setError(data.error || "Something went wrong");
        return;
      }

      setResult(data);
    } catch {
      setError("Could not connect to the backend API.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-white text-blue-900 p-8">
      <section className="mx-auto max-w-2xl">
        <h1 className="text-4xl font-bold mb-2">NextTrack</h1>

        <p className="text-blue mb-8">
          Prototype session-based music recommendation interface.
        </p>

        <form
          onSubmit={handleSubmit}
          className="bg-white border border-blue-900 rounded-2xl p-6 space-y-5"
        >
          <div>
            <label className="block mb-2 text-sm font-medium">Track ID</label>
            <input
              value={trackId}
              onChange={(event) => setTrackId(event.target.value)}
              className="w-full rounded-lg bg-white border border-blue-900 p-3"
              type="number"
              min="1"
            />
          </div>

          <div>
            <label className="block mb-2 text-sm font-medium">Genre</label>
            <input
              value={genre}
              onChange={(event) => setGenre(event.target.value)}
              className="w-full rounded-lg bg-white border border-blue-900 p-3"
            />
          </div>

          <div>
            <label className="block mb-2 text-sm font-medium">Mood</label>
            <input
              value={mood}
              onChange={(event) => setMood(event.target.value)}
              className="w-full rounded-lg  bg-white border border-blue-900 p-3"
            />
          </div>

          <div>
            <label className="block mb-2 text-sm font-medium">Energy</label>
            <input
              value={energy}
              onChange={(event) => setEnergy(event.target.value)}
              className="w-full rounded-lg  bg-white border border-blue-900 p-3"
              type="number"
              min="1"
              max="10"
            />
          </div>

          <div>
            <label className="block mb-2 text-sm font-medium">Tempo</label>
            <input
              value={tempo}
              onChange={(event) => setTempo(event.target.value)}
              className="w-full rounded-lg bg-white border border-blue-900 p-3"
              type="number"
              min="1"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-white border border-blue-900 p-3 font-semibold"
          >
            {loading ? "Finding recommendation..." : "Recommend Track"}
          </button>
        </form>

        {error && (
          <div className="mt-6 rounded-xl border border-red-700 bg-red-950 p-4">
            {error}
          </div>
        )}

        {result && (
          <div className="mt-6 rounded-2xl border border-blue-900 bg-white p-6">
            <h2 className="text-2xl font-bold mb-4">Recommended Track</h2>

            <p className="text-xl font-semibold">
              {result.recommended_track.track_name}
            </p>

            <p className="text-blue-900">
              {result.recommended_track.artist}
              {result.recommended_track.album &&
                ` — ${result.recommended_track.album}`}
            </p>

            <div className="mt-4 space-y-1 text-sm text-blue-900">
              <p>Genre: {result.recommended_track.genre}</p>
              <p>Mood: {result.recommended_track.mood}</p>
              <p>Energy: {result.recommended_track.energy}</p>
              <p>Tempo: {result.recommended_track.tempo}</p>
              <p>Score: {result.recommended_track.score}</p>
            </div>

            <p className="mt-4 text-blue-900">
              Reason: {result.recommended_track.reason}
            </p>
          </div>
        )}
      </section>
    </main>
  );
}
