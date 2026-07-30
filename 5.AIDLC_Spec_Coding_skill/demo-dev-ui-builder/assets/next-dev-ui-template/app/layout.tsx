import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Demo Dev UI",
  description: "Developer testing and monitoring console"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
