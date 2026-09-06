"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const clientId =
  process.env.NEXT_PUBLIC_SPOTIFY_CLIENT_ID!;

const redirectUri =
  process.env.NEXT_PUBLIC_SPOTIFY_REDIRECT_URI!;

export default function SpotifyCallbackPage() {
  const router = useRouter();

  const [message, setMessage] =
    useState("Connecting to Spotify...");

  useEffect(() => {
    async function exchangeCode() {
      const params =
        new URLSearchParams(window.location.search);

      const code = params.get("code");
      const returnedState = params.get("state");
      const error = params.get("error");

      if (error) {
        setMessage(`Spotify authorization failed: ${error}`);
        return;
      }

      if (!code) {
        setMessage("No authorization code was returned.");
        return;
      }

      const savedState =
        localStorage.getItem("spotify_auth_state");

      if (
        !returnedState ||
        returnedState !== savedState
      ) {
        setMessage(
          "Spotify authorization state did not match."
        );
        return;
      }

      const codeVerifier =
        localStorage.getItem(
          "spotify_code_verifier"
        );

      if (!codeVerifier) {
        setMessage(
          "Spotify code verifier could not be found."
        );
        return;
      }

      try {
        const response = await fetch(
          "https://accounts.spotify.com/api/token",
          {
            method: "POST",
            headers: {
              "Content-Type":
                "application/x-www-form-urlencoded",
            },
            body: new URLSearchParams({
              client_id: clientId,
              grant_type: "authorization_code",
              code,
              redirect_uri: redirectUri,
              code_verifier: codeVerifier,
            }),
          }
        );

        const data = await response.json();

        if (!response.ok) {
          throw new Error(
            data.error_description ||
              data.error ||
              "Spotify token exchange failed."
          );
        }

        localStorage.setItem(
          "spotify_access_token",
          data.access_token
        );

        if (data.refresh_token) {
          localStorage.setItem(
            "spotify_refresh_token",
            data.refresh_token
          );
        }

        localStorage.setItem(
          "spotify_token_expires_at",
          String(
            Date.now() +
              data.expires_in * 1000
          )
        );

        localStorage.removeItem(
          "spotify_code_verifier"
        );

        localStorage.removeItem(
          "spotify_auth_state"
        );

        setMessage("Spotify connected.");

        setTimeout(() => {
          router.push("/");
        }, 1000);
      } catch (err) {
        setMessage(
          err instanceof Error
            ? err.message
            : "Unable to connect to Spotify."
        );
      }
    }

    exchangeCode();
  }, [router]);

  return (
    <main style={{ padding: "40px" }}>
      <h1>Spotify connection</h1>
      <p>{message}</p>
    </main>
  );
}