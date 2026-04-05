import type { Metadata } from "next";
import { Source_Serif_4, Inter } from "next/font/google";
import "./globals.css";

const sourceSerif = Source_Serif_4({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-display",
  weight: ["400", "600", "700"],
});

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-body",
});

export const metadata: Metadata = {
  title: "Frontier — The Agent Driven Organization",
  description:
    "Deploy autonomous AI agents on your own cloud. Frontier builds the agentic stack and integrates it into your business. Currently invite-only.",
  openGraph: {
    title: "Frontier — The Agent Driven Organization",
    description:
      "Deploy autonomous AI agents on your own cloud. Frontier builds the agentic stack and integrates it into your business.",
    url: "https://agentdriven.org",
    siteName: "Frontier",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${sourceSerif.variable} ${inter.variable}`}>
      <body className="antialiased font-[family-name:var(--font-body)]">{children}</body>
    </html>
  );
}
