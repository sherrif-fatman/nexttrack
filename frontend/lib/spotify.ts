import {
  refreshSpotifyAccessToken,
} from "@/lib/spotifyAuth";

type SpotifyTrackMatch = {
  id: string;
  uri: string;
  name: string;
  artist: string;
};

async function searchSpotify(
  query: string,
  token: string
) {
  return fetch(
    `https://api.spotify.com/v1/search?q=${encodeURIComponent(
      query
    )}&type=track&limit=10`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );
}

function normalise(value: string) {
  return value
    .toLowerCase()
    .replace(/[^\w\s]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

export async function findSpotifyTrack(
  trackName: string,
  artistName: string
): Promise<SpotifyTrackMatch | null> {
  let token = localStorage.getItem(
    "spotify_access_token"
  );

  if (!token) {
    throw new Error(
      "Spotify is not connected."
    );
  }

  // First try: precise Spotify field search
  let response = await searchSpotify(
    `track:"${trackName}" artist:"${artistName}"`,
    token
  );

  if (response.status === 401) {
    console.log(
      "Spotify token expired. Refreshing..."
    );

    token =
      await refreshSpotifyAccessToken();

    response = await searchSpotify(
      `track:"${trackName}" artist:"${artistName}"`,
      token
    );
  }

  if (!response.ok) {
    const errorText =
      await response.text();

    console.error(
      "Spotify search failed:",
      response.status,
      errorText
    );

    throw new Error(
      `Unable to search Spotify (${response.status}).`
    );
  }

  let data = await response.json();
  let items = data.tracks?.items ?? [];

  // If the strict query gives nothing,
  // fall back to a broader text search.
  if (items.length === 0) {
    response = await searchSpotify(
      `${trackName} ${artistName}`,
      token
    );

    if (!response.ok) {
      return null;
    }

    data = await response.json();
    items = data.tracks?.items ?? [];
  }

  if (items.length === 0) {
    return null;
  }

  const normalisedTrack =
    normalise(trackName);

  const normalisedArtist =
    normalise(artistName);

  const bestMatch = items.find(
    (item: any) => {
      const spotifyTitle =
        normalise(item.name ?? "");

      const artistMatches =
        item.artists?.some(
          (artist: any) =>
            normalise(
              artist.name ?? ""
            ) === normalisedArtist
        );

      return (
        spotifyTitle ===
          normalisedTrack &&
        artistMatches
      );
    }
  );

  // Prefer same artist even if Spotify's
  // title has extra text such as "Remastered".
  const sameArtistMatch =
    items.find((item: any) =>
      item.artists?.some(
        (artist: any) =>
          normalise(
            artist.name ?? ""
          ) === normalisedArtist
      )
    );

  const selected =
    bestMatch ??
    sameArtistMatch ??
    items[0];

  return {
    id: selected.id,
    uri: selected.uri,
    name: selected.name,
    artist:
      selected.artists?.[0]?.name ??
      "",
  };
}