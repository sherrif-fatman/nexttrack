export type Recommendation = {
  id: number;
  artist: string;
  track: string;
  album: string;
  score: number;
  reason: string;
};

export const mockRecommendations: Recommendation[] = [
  { id: 1, artist: "George Nooks", track: "No One Knows", album: "Giving Thanks", score: 0.91, reason: "Strong musical style match, closely matched tempo and loudness" },
  { id: 2, artist: "Pinchers", track: "Don't Do That", album: "Hotter", score: 0.88, reason: "Strong musical style match and closely matched tempo" },
  { id: 3, artist: "Tyrone Taylor", track: "I'm A Believer", album: "Cottage in Negril", score: 0.87, reason: "Strong musical style match with similar loudness" },
  { id: 4, artist: "Carlton Livingston", track: "Slow Down", album: "Retrospect", score: 0.84, reason: "Strong musical style match and closely matched tempo" },
  { id: 5, artist: "Warrior King", track: "Breath Of Fresh Air", album: "Hold The Faith", score: 0.83, reason: "Strong style match with compatible key and mode" },
  { id: 6, artist: "Anthony Cruz", track: "Make It Up", album: "Fight With All Your Might", score: 0.82, reason: "Strong musical style match with close tempo" },
  { id: 7, artist: "Jack Johnson", track: "Fall Line", album: "On and On", score: 0.79, reason: "Similar style with closely matched loudness" },
  { id: 8, artist: "Fat Joe", track: "My FoFo", album: "All or Nothing", score: 0.78, reason: "Strong style match with compatible key and mode" },
  { id: 9, artist: "Lil Wayne", track: "Fly Talkin'", album: "Tha Carter", score: 0.77, reason: "Strong style match and closely matched tempo" },
  { id: 10, artist: "Beyoncé", track: "Be With You", album: "Dangerously in Love", score: 0.74, reason: "Similar musical style and compatible key and mode" },
];
