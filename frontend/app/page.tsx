"use client";

import { useState } from "react";
import Header from "../components/Header";
import SearchPanel from "../components/SearchPanel";
import Recommendations from "../components/Recommendations";
import type { Track, Recommendation } from "../lib/types";
import FeedbackPanel from "../components/FeedbackPanel";
import API_BASE_URL from "../lib/api";

export type RecommendationPreferences = {
  style: string;
  tempo: "" | "slower" | "similar" | "faster";
  intensity: "" | "softer" | "similar" | "stronger";
};

export default function Home() {
  const [accessible, setAccessible] = useState(false);

  const [sessionTracks, setSessionTracks] = useState<Track[]>([]);
  const [recommendations, setRecommendations] =
    useState<Recommendation[]>([]);

  const [sessionId, setSessionId] = useState<number | null>(null);
  const [ratings, setRatings] = useState<Record<number, number>>({});

  const [preferences, setPreferences] =
    useState<RecommendationPreferences>({
      style: "",
      tempo: "",
      intensity: "",
    });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function addTrack(track: Track) {
    setSessionTracks((current) => {
      if (current.some((item) => item.id === track.id)) {
        return current;
      }

      if (current.length >= 5) {
        return current;
      }

      return [...current, track];
    });
  }

  function removeTrack(trackId: number) {
    setSessionTracks((current) =>
      current.filter((track) => track.id !== trackId)
    );

    // Removing a track changes the session context.
    // Start a fresh recommendation session next time.
    setSessionId(null);
    setRecommendations([]);
    setRatings({});
    setError(null);
  }

  function rateRecommendation(
    trackId: number,
    rating: number
  ) {
    setRatings((current) => ({
      ...current,
      [trackId]: rating,
    }));
  }

  function updatePreferences(
    nextPreferences: RecommendationPreferences
  ) {
    setPreferences(nextPreferences);
  }

  async function findMusic() {
    if (sessionTracks.length === 0) {
      setError("Add at least one track to your session first.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/recommend/`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            track_ids: sessionTracks.map(
              (track) => track.id
            ),
            session_id: sessionId,
            preferences: {
              style: preferences.style,
              tempo: preferences.tempo,
              intensity: preferences.intensity,
            },
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error ||
            "Unable to generate recommendations."
        );
      }

      setSessionId(data.session_id);
      setRecommendations(data.recommendations);
      setRatings({});


    } catch (err) {
      console.error(err);

      setError(
        err instanceof Error
          ? err.message
          : "Unable to contact the NextTrack backend."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      className={
        accessible
          ? "appShell accessibilityMode"
          : "appShell"
      }
    >
      <Header
        accessible={accessible}
        onToggleAccessible={() =>
          setAccessible((value) => !value)
        }
      />

      <div className="pageLayout">
        <SearchPanel
          accessible={accessible}
          sessionTracks={sessionTracks}
          onAddTrack={addTrack}
          onRemoveTrack={removeTrack}
          onFindMusic={findMusic}
          loading={loading}
          error={error}
          hasRecommendations={
            recommendations.length > 0
          }
          preferences={preferences}
          onPreferencesChange={updatePreferences}
        />

        <div>
          {recommendations.length > 0 && (
            <div className="feedbackShortcut">
              <a
                href="#feedback"
                className="secondaryButton"
              >
                Leave feedback ↓
              </a>
            </div>
          )}

          <Recommendations
            accessible={accessible}
            sessionTracks={sessionTracks}
            recommendations={recommendations}
            loading={loading}
            ratings={ratings}
            onRateRecommendation={
              rateRecommendation
            }
          />

          {recommendations.length > 0 && (
            <FeedbackPanel
              sessionId={sessionId}
              ratings={ratings}
            />
          )}
        </div>
      </div>
    </div>
  );
}
