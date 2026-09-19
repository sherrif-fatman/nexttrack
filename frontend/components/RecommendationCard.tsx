"use client";

import { useState } from "react";

import type { Recommendation } from "../lib/types";
import Rating from "./Rating";

import { findSpotifyTrack } from "@/lib/spotify";
import { loginWithSpotify } from "@/lib/spotifyAuth";

import {
  initialiseSpotifyPlayer,
  activateSpotifyPlayer,
  playSpotifyUri,
  pauseSpotifyPlayback,
} from "@/lib/spotifyPlayer";

type Props = {
  recommendation: Recommendation;
  accessible?: boolean;
  rating: number;
  onRate: (rating: number) => void;
};

export default function RecommendationCard({
  recommendation,
  accessible = false,
  rating,
  onRate,
}: Props) {
  const [showSpotifyPrompt, setShowSpotifyPrompt] =
    useState(false);

  async function handlePlay() {
    try {
      const spotifyAccessToken =
        localStorage.getItem("spotify_access_token");

      const spotifyRefreshToken =
        localStorage.getItem("spotify_refresh_token");

      if (!spotifyAccessToken && !spotifyRefreshToken) {
        setShowSpotifyPrompt(true);
        return;
      }

      await initialiseSpotifyPlayer();
      await activateSpotifyPlayer();

      const match = await findSpotifyTrack(
        recommendation.track_name,
        recommendation.artist
      );

      if (!match) {
        console.log("No Spotify match found.");
        return;
      }

      console.log("Spotify match:", match);

      await playSpotifyUri(match.uri);

      console.log("Spotify playback started.");
    } catch (error) {
      console.error(
        "Spotify playback failed:",
        error
      );

      if (
        error instanceof Error &&
        error.message ===
          "Spotify is not connected."
      ) {
        setShowSpotifyPrompt(true);
        return;
      }
    }
  }

  async function handleSpotifyConnect() {
    setShowSpotifyPrompt(false);

    try {
      await loginWithSpotify();
    } catch (error) {
      console.error(
        "Unable to start Spotify authentication:",
        error
      );
    }
  }

  async function handlePause() {
    try {
      await pauseSpotifyPlayback();

      console.log(
        "Spotify playback paused."
      );
    } catch (error) {
      console.error(
        "Spotify pause failed:",
        error
      );
    }
  }

  return (
    <>
      <article
        className={`recommendationCard ${
          accessible
            ? "recommendationCardAccessible"
            : ""
        }`}
      >
        <div className="artwork">
          {recommendation.artwork_url ? (
            <img
              src={recommendation.artwork_url}
              alt={`${
                recommendation.album ??
                recommendation.track_name
              } cover`}
            />
          ) : (
            <span>Artwork</span>
          )}
        </div>

        <div className="recommendationMeta">
          <div className="trackHeader">
            <div className="trackIdentity">
              <h3>
                {recommendation.track_name}
              </h3>

              <p className="artistName">
                {recommendation.artist}
              </p>
            </div>

            <div
              className="playbackControls"
              aria-label={`Playback controls for ${recommendation.track_name}`}
            >
              <button
                type="button"
                className="playbackCircle"
                onClick={handlePlay}
                aria-label={`Play ${recommendation.track_name} by ${recommendation.artist}`}
                title="Play"
              >
                <span
                  className="playIcon"
                  aria-hidden="true"
                />
              </button>

              <button
                type="button"
                className="playbackCircle"
                onClick={handlePause}
                aria-label="Pause Spotify playback"
                title="Pause"
              >
                <span
                  className="pauseIcon"
                  aria-hidden="true"
                />
              </button>
            </div>
          </div>

          {recommendation.album && (
            <p className="albumName">
              {recommendation.album}
            </p>
          )}

          <p className="reason">
            {recommendation.reason}
          </p>

          <p className="score">
            Match:{" "}
            {(recommendation.score * 100).toFixed(0)}%
          </p>

          <Rating
            accessible={accessible}
            rating={rating}
            onChange={onRate}
          />
        </div>
      </article>

      {showSpotifyPrompt && (
        <div
          className="spotifyPromptBackdrop"
          role="presentation"
        >
          <div
            className="spotifyPrompt"
            role="dialog"
            aria-modal="true"
            aria-labelledby="spotifyPromptTitle"
            aria-describedby="spotifyPromptDescription"
          >
            <h2 id="spotifyPromptTitle">
              Connect to Spotify
            </h2>

            <p id="spotifyPromptDescription">
              Connect your Spotify Premium account
              to play recommendations in NextTrack.
            </p>

            <div className="spotifyPromptActions">
              <button
                type="button"
                className="primaryButton"
                onClick={handleSpotifyConnect}
              >
                Connect Spotify
              </button>

              <button
                type="button"
                className="secondaryButton"
                onClick={() =>
                  setShowSpotifyPrompt(false)
                }
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
