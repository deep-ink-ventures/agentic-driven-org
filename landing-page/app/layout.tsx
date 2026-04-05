import type { Metadata } from "next";
import { DM_Sans, Inter } from "next/font/google";
import "./globals.css";

const dmSans = DM_Sans({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-display",
  weight: ["400", "500", "700"],
});

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-body",
});

export const metadata: Metadata = {
  title: "AgentDriven — Agentic AI Infrastructure & Consulting",
  description:
    "Deploy autonomous AI agents on your own cloud. AgentDriven builds the agentic stack and integrates it into your business. Currently invite-only.",
  openGraph: {
    title: "AgentDriven — Agentic AI Infrastructure & Consulting",
    description:
      "Deploy autonomous AI agents on your own cloud. AgentDriven builds the agentic stack and integrates it into your business.",
    url: "https://agentdriven.org",
    siteName: "AgentDriven",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${dmSans.variable} ${inter.variable}`}>
      <body className="antialiased font-[family-name:var(--font-body)]">{children}</body>
    </html>
  );
}
