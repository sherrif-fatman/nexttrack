"use client";

import { useState } from "react";
import API_BASE_URL from "../lib/api";

type Props = {
  sessionId: number | null;
  ratings: Record<number, number>;
};

export default function FeedbackPanel({
  sessionId,
  ratings,
}: Props) {
  const [explanationClarity, setExplanationClarity] = useState(0);
  const [interfaceEase, setInterfaceEase] = useState(0);
  const [searchClarity, setSearchClarity] = useState(0);
  const [comments, setComments] = useState("");
  const [consentGiven, setConsentGiven] = useState(false);

  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const ratingValues = Object.values(ratings);

  const averageRelevance =
    ratingValues.length > 0
      ? ratingValues.reduce((total, value) => total + value, 0) /
        ratingValues.length
      : null;

  async function submitFeedback(e: React.FormEvent) {
    e.preventDefault();

    if (!sessionId) {
      setError("Generate recommendations before submitting feedback.");
      return;
    }

    if (
      averageRelevance === null ||
      explanationClarity === 0 ||
      interfaceEase === 0 ||
      searchClarity === 0
    ) {
      setError(
        "Please rate at least one recommended track above, then complete all three feedback questions."
      );
      return;
    }

    if (!consentGiven) {
      setError(
        "Please confirm that you consent to your feedback being used for project evaluation."
      );
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/feedback/`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            session_id: sessionId,
            recommendation_relevance: averageRelevance,
            explanation_clarity: explanationClarity,
            interface_ease_of_use: interfaceEase,
            search_clarity: searchClarity,
            comments: comments.trim(),
            consent_given: consentGiven,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error || "Unable to submit feedback."
        );
      }

      setSubmitted(true);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to submit feedback."
      );
    } finally {
      setSubmitting(false);
    }
  }

  if (!sessionId) {
    return null;
  }

  if (submitted) {
    return (
      <section id="feedback" className="feedbackPanel">
        <h2>Thank you</h2>
        <p>Your feedback has been recorded.</p>
      </section>
    );
  }

  return (
    <section
      id="feedback"
      className="feedbackPanel"
      aria-labelledby="feedback-heading"
    >
      <h2 id="feedback-heading">
        How was this session?
      </h2>

      <p className="muted">
        <strong>
          Please rate some of the recommended tracks above. Before filling in the feedback otherwise you won't be able to submit your response.
        </strong>{" "}
      </p>
      <p className="muted">
        How relevant were they to the music you selected? Rate each
        track from 1 (not relevant) to 5 (very relevant).
      </p>

      <form onSubmit={submitFeedback}>
        <div className="feedbackGrid">
          <div className="feedbackRow feedbackSummaryRow">
            <span className="feedbackLabel">
              Average recommendation relevance
            </span>

            <span className="feedbackValue">
              {averageRelevance !== null
                ? `${averageRelevance.toFixed(1)} / 5`
                : "Rate at least one recommendation"}
            </span>
          </div>

          <FeedbackRating
            label="How clear were the reasons given for the recommendations?"
            value={explanationClarity}
            onChange={setExplanationClarity}
          />

          <FeedbackRating
            label="How easy was NextTrack to use?"
            value={interfaceEase}
            onChange={setInterfaceEase}
          />

          <FeedbackRating
            label="How easy was it to search for and select the music you wanted?"
            value={searchClarity}
            onChange={setSearchClarity}
          />
        </div>

        <label className="feedbackComments">
          <span>Comments</span>

          <textarea
            value={comments}
            onChange={(e) => setComments(e.target.value)}
            rows={4}
            placeholder="Anything you liked, disliked or found confusing?"
          />
        </label>

        <label className="feedbackConsent">
          <input
            type="checkbox"
            checked={consentGiven}
            onChange={(e) => setConsentGiven(e.target.checked)}
          />

          <span>
            I consent to my feedback being analysed and used to evaluate
            and improve NextTrack as part of this university project.
          </span>
        </label>

        <p className="muted">
          Feedback is collected for project evaluation purposes and will
          not be used to create a persistent user profile.
        </p>

        {error && (
          <p className="errorMessage" role="alert">
            {error}
          </p>
        )}

        <button
          type="submit"
          className="primaryButton"
          disabled={submitting || !consentGiven}
        >
          {submitting
            ? "Submitting..."
            : "Submit feedback"}
        </button>
      </form>
    </section>
  );
}

type FeedbackRatingProps = {
  label: string;
  value: number;
  onChange: (value: number) => void;
};

function FeedbackRating({
  label,
  value,
  onChange,
}: FeedbackRatingProps) {
  return (
    <div className="feedbackRow">
      <span className="feedbackLabel">
        {label}
      </span>

      <div className="feedbackStars">
        {[1, 2, 3, 4, 5].map((rating) => (
          <button
            key={rating}
            type="button"
            className={
              rating <= value
                ? "star selected"
                : "star"
            }
            onClick={() => onChange(rating)}
            aria-label={`${label}: ${rating} out of 5`}
            aria-pressed={rating <= value}
          >
            ★
          </button>
        ))}
      </div>

      <span className="feedbackValue">
        {value || "–"}/5
      </span>
    </div>
  );
}