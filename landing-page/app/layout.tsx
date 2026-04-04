import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
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
    <html lang="en" className={inter.className}>
      <body className="antialiased">{children}</body>
    </html>
  );
}
