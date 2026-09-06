import "./globals.css";

export const metadata = {
  title: "NextTrack",
  description: "Session-based music recommendations without persistent user profiling",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
