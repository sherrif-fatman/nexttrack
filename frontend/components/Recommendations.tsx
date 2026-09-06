"use client";

import {
  useEffect,
  useMemo,
  useState,
} from "react";

import RecommendationCard from "./RecommendationCard";

import type {
  Track,
  Recommendation,
} from "../lib/types";

type Props = {
  accessible: boolean;
  sessionTracks: Track[];
  recommendations: Recommendation[];
  loading: boolean;
  ratings: Record<number, number>;
  onRateRecommendation: (
    trackId: number,
    rating: number
  ) => void;
};

const RESULTS_PER_PAGE = 20;

export default function Recommendations({
  accessible,
  sessionTracks,
  recommendations,
  loading,
  ratings,
  onRateRecommendation,
}: Props) {
  const [currentPage, setCurrentPage] =
    useState(1);

  const totalPages = Math.max(
    1,
    Math.ceil(
      recommendations.length /
        RESULTS_PER_PAGE
    )
  );

  useEffect(() => {
    setCurrentPage(1);
  }, [recommendations]);

  const visibleRecommendations =
    useMemo(() => {
      const startIndex =
        (currentPage - 1) *
        RESULTS_PER_PAGE;

      const endIndex =
        startIndex +
        RESULTS_PER_PAGE;

      return recommendations.slice(
        startIndex,
        endIndex
      );
    }, [
      recommendations,
      currentPage,
    ]);

  function scrollToRecommendations() {
    document
      .getElementById("recommendations")
      ?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
  }

  function goToPreviousPage() {
    setCurrentPage((current) =>
      Math.max(1, current - 1)
    );

    scrollToRecommendations();
  }

  function goToNextPage() {
    setCurrentPage((current) =>
      Math.min(
        totalPages,
        current + 1
      )
    );

    scrollToRecommendations();
  }

  return (
    <main
      className="recommendationsArea"
      id="recommendations"
    >
      <div className="recommendationHeader">
        <h1>Your recommendations</h1>

        <div
          className="sessionChips"
          aria-label="Current recommendation context"
        >
          {sessionTracks.map((track) => (
            <span
              className="chip"
              key={track.id}
            >
              {track.track_name}
            </span>
          ))}
        </div>
      </div>

      {loading ? (
        <p
          className="muted"
          aria-live="polite"
        >
          Building recommendations from
          your current session...
        </p>
      ) : recommendations.length === 0 ? (
        <p className="muted">
          Add a track and choose Find music
          to begin.
        </p>
      ) : (
        <div
          className={
            accessible
              ? "recommendationList"
              : "recommendationGrid"
          }
        >
          {visibleRecommendations.map(
            (recommendation) => (
              <RecommendationCard
                key={recommendation.id}
                recommendation={
                  recommendation
                }
                accessible={accessible}
                rating={
                  ratings[
                    recommendation.id
                  ] ?? 0
                }
                onRate={(rating) =>
                  onRateRecommendation(
                    recommendation.id,
                    rating
                  )
                }
              />
            )
          )}
        </div>
      )}

      {totalPages > 1 && (
        <nav
          className="pager"
          aria-label="Recommendation pages"
        >
          <button
            type="button"
            onClick={goToPreviousPage}
            disabled={currentPage === 1}
          >
            ◀ Back
          </button>

          <span
            className="pagerStatus"
            aria-live="polite"
          >
            Page {currentPage} of{" "}
            {totalPages}
          </span>

          <button
            type="button"
            onClick={goToNextPage}
            disabled={
              currentPage === totalPages
            }
          >
            Next ▶
          </button>
        </nav>
      )}
    </main>
  );
}