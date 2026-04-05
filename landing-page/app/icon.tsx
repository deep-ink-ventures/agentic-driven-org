import { ImageResponse } from "next/og";

export const size = { width: 32, height: 32 };
export const contentType = "image/png";

export default function Icon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: 32,
          height: 32,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#0d0b09",
          borderRadius: 6,
        }}
      >
        <svg
          width="24"
          height="24"
          viewBox="0 0 40 40"
          fill="none"
        >
          <path d="M4 20 H14" stroke="#c4803c" strokeWidth="3" strokeLinecap="round" />
          <circle cx="14" cy="20" r="3" fill="#c4803c" />
          <path d="M14 20 C20 20, 22 10, 28 10 L36 10" stroke="#c4803c" strokeWidth="3" strokeLinecap="round" />
          <path d="M14 20 H36" stroke="#c4803c" strokeWidth="3" strokeLinecap="round" />
          <path d="M14 20 C20 20, 22 30, 28 30 L36 30" stroke="#c4803c" strokeWidth="3" strokeLinecap="round" />
          <circle cx="36" cy="10" r="2" fill="#c4803c" opacity="0.5" />
          <circle cx="36" cy="20" r="2" fill="#c4803c" opacity="0.5" />
          <circle cx="36" cy="30" r="2" fill="#c4803c" opacity="0.5" />
        </svg>
      </div>
    ),
    { ...size }
  );
}
