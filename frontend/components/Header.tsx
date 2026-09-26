"use client";

import React from "react";
import Image from "next/image";
import logo4 from "./assets/logo4.png";



type Props = {
  accessible: boolean;
  onToggleAccessible: () => void;
};

export default function Header({
  accessible,
  onToggleAccessible,
}: Props) {

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

      <div className="headerRule" />
    </header>
  );
}

