"use client";

import React from "react";
import Image from "next/image";
import logo4 from "./assets/logo4.png";
import { loginWithSpotify } from "@/lib/spotifyAuth";

import {
  initialiseSpotifyPlayer,
} from "@/lib/spotifyPlayer";


type Props = {
  accessible: boolean;
  onToggleAccessible: () => void;
};

export default function Header({
  accessible,
  onToggleAccessible,
}: Props) {
  async function handleSpotifyConnect() {
    console.log("Connect Spotify clicked");
    await loginWithSpotify();
  }

  return (
    <header className="siteHeader">
      <Image
        src={logo4}
        alt="NextTrack"
        className="siteLogo"
        priority
      />

      <button
        className="accessibilityButton"
        onClick={onToggleAccessible}
        aria-pressed={accessible}
      >
        {accessible ? "Standard view" : "Accessibility"}
      </button>

      {/* <button
        type="button"
        className="secondaryButton"
        onClick={handleSpotifyConnect}
      >
        Connect Spotify
      </button>

      <button
  type="button"
  className="secondaryButton"
  onClick={async () => {
    try {
      const deviceId =
        await initialiseSpotifyPlayer();

      console.log(
        "NextTrack Spotify device:",
        deviceId
      );
    } catch (error) {
      console.error(
        "Spotify player failed:",
        error
      );
    }
  }}
>
  Start Spotify Player
</button> */}

      <div className="headerRule" />
    </header>
  );
}

