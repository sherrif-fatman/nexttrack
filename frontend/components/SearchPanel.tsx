import { useState } from "react";
import type { Track } from "../lib/types";
import type { RecommendationPreferences } from "../app/page";
import API_BASE_URL from "../lib/api";

type Props = {
  accessible: boolean;
  sessionTracks: Track[];
  onAddTrack: (track: Track) => void;
  onRemoveTrack: (trackId: number) => void;
  onFindMusic: () => void;
  loading: boolean;
  error: string | null;
  hasRecommendations: boolean;
  preferences: RecommendationPreferences;
  onPreferencesChange: (
    preferences: RecommendationPreferences
  ) => void;
};

const STYLE_OPTIONS = [
  "",
  "rock",
  "electronic",
  "pop",
  "hip hop",
  "indie",
  "ambient",
  "jazz",
  "soul",
  "funk",
  "folk",
  "metal",
  "reggae",
];

export default function SearchPanel({
  accessible,
  sessionTracks,
  onAddTrack,
  onRemoveTrack,
  onFindMusic,
  loading,
  error,
  hasRecommendations,
  preferences,
  onPreferencesChange,
}: Props) {
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState<Track[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] =
    useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();

    const value = query.trim();

    if (!value) {
      setSearchResults([]);
      return;
    }

    setSearching(true);
    setSearchError(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/tracks/search/?q=${encodeURIComponent(
          value
        )}`
      );

      if (!response.ok) {
        throw new Error(
          "Unable to search the track catalogue."
        );
      }

      const data: Track[] =
        await response.json();

      setSearchResults(data);
    } catch (err) {
      console.error(err);

      setSearchError(
        err instanceof Error
          ? err.message
          : "Unable to search the track catalogue."
      );
    } finally {
      setSearching(false);
    }
  }

  function selectTrack(track: Track) {
    onAddTrack(track);

    setQuery("");
    setSearchResults([]);
  }

  function updateStyle(style: string) {
    onPreferencesChange({
      ...preferences,
      style,
    });
  }

  function updateTempo(
    tempo: RecommendationPreferences["tempo"]
  ) {
    onPreferencesChange({
      ...preferences,
      tempo,
    });
  }

  function updateIntensity(
    intensity: RecommendationPreferences["intensity"]
  ) {
    onPreferencesChange({
      ...preferences,
      intensity,
    });
  }

  function clearRefinements() {
    onPreferencesChange({
      style: "",
      tempo: "",
      intensity: "",
    });
  }

  const hasActiveRefinements =
    preferences.style !== "" ||
    preferences.tempo !== "" ||
    preferences.intensity !== "";

  return (
    <aside
      className={`searchPanel ${
        accessible
          ? "searchPanelAccessible"
          : ""
      }`}
      aria-label="Build your session"
    >
      <p className="introText">
        <strong>1. Search for music.</strong>{" "}
        Search for a song or artist, then add up to 5 tracks to your session. You can further refine the recommendation by style, tempo and intensity.
      </p>

      <form
        onSubmit={submit}
        className="searchForm"
      >
        <label
          htmlFor="track-search"
          className="srOnly"
        >
          Search for a song or artist
        </label>

        <input
          id="track-search"
          value={query}
          onChange={(e) =>
            setQuery(e.target.value)
          }
          placeholder="Song or artist"
        />

        <button
          type="submit"
          className="primaryButton"
          disabled={searching}
        >
          {searching
            ? "Searching..."
            : "Search"}
        </button>
      </form>

      {searchError && (
        <p
          role="alert"
          className="errorMessage"
        >
          {searchError}
        </p>
      )}

      {searchResults.length > 0 && (
        <div className="searchResults">
          <h2>Search results</h2>

          <ul>
            {searchResults.map((track) => (
              <li
                key={track.id}
                className="searchResult"
              >
                <div>
                  <strong>
                    {track.track_name}
                  </strong>

                  <span>
                    {track.artist}
                  </span>

                  {track.album && (
                    <small>
                      {track.album}
                    </small>
                  )}
                </div>

                <button
                  type="button"
                  className="secondaryButton"
                  onClick={() =>
                    selectTrack(track)
                  }
                  disabled={
                    sessionTracks.length >= 5 ||
                    sessionTracks.some(
                      (item) =>
                        item.id === track.id
                    )
                  }
                >
                  {sessionTracks.some(
                    (item) =>
                      item.id === track.id
                  )
                    ? "Added to session"
                  : "Add"}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
      <p className="smallNote">
        <strong>2. Choose your tracks.</strong>{" "}
        Add at least one track from the results. Your selected tracks
        will appear below. Click ADD to add a track to the Recommender (You can ADD up to five different tracks/ artists) Then click Find Music for your recommendations.
      </p>
      <div
        className="sessionList"
        aria-live="polite"
      >
        <div className="sessionHeading">
          <h2>Current session</h2>

          <span className="sessionCount">
            {sessionTracks.length}/5 tracks
          </span>
        </div>

        {sessionTracks.length === 0 ? (
          <p className="muted">
            No tracks selected yet.
          </p>
        ) : (
          <ol>
            {sessionTracks.map((track) => (
              <li key={track.id}>
                <div>
                  <strong>
                    {track.track_name}
                  </strong>

                  <span>
                    {" "}
                    — {track.artist}
                  </span>
                </div>

                <button
                  type="button"
                  onClick={() =>
                    onRemoveTrack(track.id)
                  }
                  aria-label={`Remove ${track.track_name} by ${track.artist}`}
                >
                  ×
                </button>
              </li>
            ))}
          </ol>
        )}
      </div>

      {!hasRecommendations && (
        <div className="panelActions">
            <button
              className="primaryButton"
              type="button"
              onClick={onFindMusic}
              disabled={loading || sessionTracks.length === 0}
            >
              {loading ? "Finding music..." : "3. Find music"}
            </button>
        </div>
      )}

      <div className="refinementPanel">
        <div className="refinementHeading">
          <div>
            <h2>Refine recommendations</h2>

            <p className="smallNote">
              Optional preferences influence the current
              recommendation ranking only.
            </p>
          </div>

          {hasActiveRefinements && (
            <button
              type="button"
              className="textButton"
              onClick={clearRefinements}
            >
              Clear
            </button>
          )}
        </div>

        <div className="refinementGroup">
          <label htmlFor="style-preference">
            Style
          </label>

          <select
            id="style-preference"
            value={preferences.style}
            onChange={(e) =>
              updateStyle(e.target.value)
            }
          >
            {STYLE_OPTIONS.map((style) => (
              <option
                key={style || "any"}
                value={style}
              >
                {style
                  ? style
                      .split(" ")
                      .map(
                        (word) =>
                          word
                            .charAt(0)
                            .toUpperCase() +
                          word.slice(1)
                      )
                      .join(" ")
                  : "Any style"}
              </option>
            ))}
          </select>
        </div>

        <fieldset className="refinementGroup">
          <legend>Tempo</legend>

          <div
            className="refinementOptions"
            role="group"
            aria-label="Tempo preference"
          >
            {[
              ["", "Any"],
              ["slower", "Slower"],
              ["similar", "Similar"],
              ["faster", "Faster"],
            ].map(([value, label]) => (
              <button
                key={label}
                type="button"
                className={
                  preferences.tempo === value
                    ? "refinementOption refinementOptionActive"
                    : "refinementOption"
                }
                onClick={() =>
                  updateTempo(
                    value as RecommendationPreferences["tempo"]
                  )
                }
                aria-pressed={
                  preferences.tempo === value
                }
              >
                {label}
              </button>
            ))}
          </div>
        </fieldset>

        <fieldset className="refinementGroup">
          <legend>Intensity</legend>

          <div
            className="refinementOptions"
            role="group"
            aria-label="Intensity preference"
          >
            {[
              ["", "Any"],
              ["softer", "Softer"],
              ["similar", "Similar"],
              ["stronger", "Stronger"],
            ].map(([value, label]) => (
              <button
                key={label}
                type="button"
                className={
                  preferences.intensity === value
                    ? "refinementOption refinementOptionActive"
                    : "refinementOption"
                }
                onClick={() =>
                  updateIntensity(
                    value as RecommendationPreferences["intensity"]
                  )
                }
                aria-pressed={
                  preferences.intensity === value
                }
              >
                {label}
              </button>
            ))}
          </div>
        </fieldset>
      </div>

      {hasRecommendations && (
        <div className="panelActions">
          <button
            className="primaryButton"
            type="button"
            onClick={onFindMusic}
            disabled={
              loading ||
              sessionTracks.length === 0
            }
          >
            {loading
              ? "Refining..."
              : "Refine recommendations"}
          </button>
        </div>
      )}

      {error && (
        <p
          role="alert"
          className="errorMessage"
        >
          {error}
        </p>
      )}
    </aside>
  );
}
