export type Track = {
  id: number;
  track_name: string;
  artwork_url?: string | null;
  artist: string;
  album: string | null;
  genre: string | null;
};

export type Recommendation = Track & {
  tempo: number | null;
  energy: number | null;
  mood: string | null;
  score: number;
  reason: string;
};