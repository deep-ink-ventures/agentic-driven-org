import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "The Agent Driven Organization — Your company, run by agents.";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OGImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "flex-end",
          padding: "80px",
          backgroundColor: "#0d0b09",
          color: "#f0ebe5",
          fontFamily: "Georgia, serif",
        }}
      >
        {/* Copper accent line */}
        <div
          style={{
            width: 64,
            height: 3,
            backgroundColor: "#c4803c",
            marginBottom: 40,
            opacity: 0.6,
          }}
        />

        {/* Headline */}
        <div
          style={{
            fontSize: 72,
            lineHeight: 1,
            letterSpacing: "-0.02em",
            marginBottom: 24,
            display: "flex",
            flexDirection: "column",
          }}
        >
          <span>Your company,</span>
          <span>run by agents.</span>
        </div>

        {/* Subline */}
        <div
          style={{
            fontSize: 24,
            color: "#a39890",
            marginBottom: 48,
            maxWidth: 600,
            lineHeight: 1.5,
          }}
        >
          Agentic AI infrastructure deployed on your cloud.
          You own everything.
        </div>

        {/* Brand with logomark */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 16,
          }}
        >
          <svg width="28" height="28" viewBox="0 0 40 40" fill="none">
            <path d="M4 20 H14" stroke="#c4803c" strokeWidth="2.5" strokeLinecap="round"/>
            <circle cx="14" cy="20" r="2.5" fill="#c4803c"/>
            <path d="M14 20 C20 20, 22 10, 28 10 L36 10" stroke="#c4803c" strokeWidth="2.5" strokeLinecap="round"/>
            <path d="M14 20 H36" stroke="#c4803c" strokeWidth="2.5" strokeLinecap="round"/>
            <path d="M14 20 C20 20, 22 30, 28 30 L36 30" stroke="#c4803c" strokeWidth="2.5" strokeLinecap="round"/>
          </svg>
          <span style={{ fontSize: 22, color: "#f0ebe5", fontFamily: "Georgia, serif" }}>
            The Agent Driven Organization
          </span>
        </div>
      </div>
    ),
    { ...size }
  );
}
