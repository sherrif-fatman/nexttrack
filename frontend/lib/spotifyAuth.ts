const clientId =
  process.env.NEXT_PUBLIC_SPOTIFY_CLIENT_ID!;

const redirectUri =
  process.env.NEXT_PUBLIC_SPOTIFY_REDIRECT_URI!;

const scopes = [
  "streaming",
  "user-read-private",
  "user-read-email",
  "user-modify-playback-state",
];

function generateRandomString(length: number) {
  const possible =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";

  const values = crypto.getRandomValues(
    new Uint8Array(length)
  );

  return values.reduce(
    (acc, x) => acc + possible[x % possible.length],
    ""
  );
}

async function sha256(plain: string) {
  const encoder = new TextEncoder();
  const data = encoder.encode(plain);

  return window.crypto.subtle.digest(
    "SHA-256",
    data
  );
}

function base64UrlEncode(input: ArrayBuffer) {
  return btoa(
    String.fromCharCode(
      ...new Uint8Array(input)
    )
  )
    .replace(/=/g, "")
    .replace(/\+/g, "-")
    .replace(/\//g, "_");
}

export async function loginWithSpotify() {
  console.log("loginWithSpotify started");

  const codeVerifier =
    generateRandomString(64);

  localStorage.setItem(
    "spotify_code_verifier",
    codeVerifier
  );

  const hashed =
    await sha256(codeVerifier);

  const codeChallenge =
    base64UrlEncode(hashed);

  const state =
    generateRandomString(16);

  localStorage.setItem(
    "spotify_auth_state",
    state
  );

  const params =
    new URLSearchParams({
      client_id: clientId,
      response_type: "code",
      redirect_uri: redirectUri,
      scope: scopes.join(" "),
      code_challenge_method: "S256",
      code_challenge: codeChallenge,
      state,
    });

  const authUrl =
    `https://accounts.spotify.com/authorize?${params.toString()}`;

  window.location.href = authUrl;
}

export async function refreshSpotifyAccessToken() {
  const refreshToken =
    localStorage.getItem(
      "spotify_refresh_token"
    );

  if (!refreshToken) {
    throw new Error(
      "No Spotify refresh token is available."
    );
  }

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
        grant_type: "refresh_token",
        refresh_token: refreshToken,
      }),
    }
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      data.error_description ||
        data.error ||
        "Unable to refresh Spotify access token."
    );
  }

  localStorage.setItem(
    "spotify_access_token",
    data.access_token
  );

  localStorage.setItem(
    "spotify_token_expires_at",
    String(
      Date.now() +
        data.expires_in * 1000
    )
  );

  if (data.refresh_token) {
    localStorage.setItem(
      "spotify_refresh_token",
      data.refresh_token
    );
  }

  return data.access_token as string;
}