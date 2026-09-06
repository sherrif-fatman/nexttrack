import {
  refreshSpotifyAccessToken,
} from "@/lib/spotifyAuth";

declare global {
  interface Window {
    Spotify: any;
    onSpotifyWebPlaybackSDKReady: () => void;
  }
}

let spotifyPlayer: any = null;
let spotifyDeviceId: string | null = null;

async function getValidAccessToken() {
  const token = localStorage.getItem(
    "spotify_access_token"
  );

  const expiresAt = Number(
    localStorage.getItem(
      "spotify_token_expires_at"
    )
  );

  if (
    token &&
    expiresAt &&
    Date.now() < expiresAt - 60_000
  ) {
    return token;
  }

  return refreshSpotifyAccessToken();
}

export function initialiseSpotifyPlayer(): Promise<string> {
  if (spotifyDeviceId) {
    return Promise.resolve(
      spotifyDeviceId
    );
  }

  return new Promise((resolve, reject) => {
    function createPlayer() {
      if (spotifyPlayer) {
        return;
      }

      spotifyPlayer =
        new window.Spotify.Player({
          name: "NextTrack",
          getOAuthToken: async (
            callback: (token: string) => void
          ) => {
            try {
              const token =
                await getValidAccessToken();

              callback(token);
            } catch (error) {
              console.error(
                "Unable to provide Spotify token:",
                error
              );
            }
          },
          volume: 0.5,
        });

      spotifyPlayer.addListener(
        "ready",
        ({
          device_id,
        }: {
          device_id: string;
        }) => {
          console.log(
            "Spotify player ready:",
            device_id
          );

          spotifyDeviceId =
            device_id;

          resolve(device_id);
        }
      );

      spotifyPlayer.addListener(
        "not_ready",
        ({
          device_id,
        }: {
          device_id: string;
        }) => {
          console.log(
            "Spotify player offline:",
            device_id
          );

          spotifyDeviceId = null;
        }
      );

      spotifyPlayer.addListener(
        "initialization_error",
        ({
          message,
        }: {
          message: string;
        }) => {
          console.error(
            "Spotify initialization error:",
            message
          );

          reject(
            new Error(message)
          );
        }
      );

      spotifyPlayer.addListener(
        "authentication_error",
        ({
          message,
        }: {
          message: string;
        }) => {
          console.error(
            "Spotify authentication error:",
            message
          );

          reject(
            new Error(message)
          );
        }
      );

      spotifyPlayer.addListener(
        "account_error",
        ({
          message,
        }: {
          message: string;
        }) => {
          console.error(
            "Spotify account error:",
            message
          );

          reject(
            new Error(message)
          );
        }
      );

      spotifyPlayer.connect();
    }

    if (window.Spotify) {
      createPlayer();
      return;
    }

    window.onSpotifyWebPlaybackSDKReady =
      createPlayer;

    const existingScript =
      document.querySelector(
        'script[src="https://sdk.scdn.co/spotify-player.js"]'
      );

    if (!existingScript) {
      const script =
        document.createElement(
          "script"
        );

      script.src =
        "https://sdk.scdn.co/spotify-player.js";

      script.async = true;

      document.body.appendChild(
        script
      );
    }
  });
}

export async function playSpotifyUri(
  uri: string
) {
  const deviceId =
    await initialiseSpotifyPlayer();

  const token =
    localStorage.getItem(
      "spotify_access_token"
    );

  if (!token) {
    throw new Error(
      "Spotify is not connected."
    );
  }

  let response = await fetch(
    `https://api.spotify.com/v1/me/player/play?device_id=${encodeURIComponent(
      deviceId
    )}`,
    {
      method: "PUT",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type":
          "application/json",
      },
      body: JSON.stringify({
        uris: [uri],
      }),
    }
  );

  if (response.status === 401) {
    const refreshedToken =
      await refreshSpotifyAccessToken();

    response = await fetch(
      `https://api.spotify.com/v1/me/player/play?device_id=${encodeURIComponent(
        deviceId
      )}`,
      {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${refreshedToken}`,
          "Content-Type":
            "application/json",
        },
        body: JSON.stringify({
          uris: [uri],
        }),
      }
    );
  }

  if (!response.ok) {
    const errorText =
      await response.text();

    console.error(
      "Spotify playback failed:",
      response.status,
      errorText
    );

    throw new Error(
      `Unable to start Spotify playback (${response.status}).`
    );
  }
}

export async function pauseSpotifyPlayback() {
  if (!spotifyPlayer) {
    return;
  }

  try {
    await spotifyPlayer.pause();

    console.log("Spotify playback paused.");
  } catch (error) {
    console.error(
      "Unable to pause Spotify playback:",
      error
    );

    throw error;
  }
}