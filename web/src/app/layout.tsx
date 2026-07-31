import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "CodeAtlas | Repository intelligence",
  description:
    "Explore repository architecture, ask source-cited questions, and understand change impact before editing code.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
