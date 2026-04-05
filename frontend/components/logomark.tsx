export default function Logomark({ size = 22, className = "" }: { size?: number; className?: string }) {
  const sw = size <= 20 ? 3 : size <= 32 ? 2.5 : 2;

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 40 40"
      fill="none"
      className={className}
      aria-hidden="true"
    >
      <path d="M4 20 H14" stroke="currentColor" strokeWidth={sw} strokeLinecap="round" />
      <circle cx="14" cy="20" r={sw} fill="currentColor" />
      <path d="M14 20 C20 20, 22 10, 28 10 L36 10" stroke="currentColor" strokeWidth={sw} strokeLinecap="round" />
      <path d="M14 20 H36" stroke="currentColor" strokeWidth={sw} strokeLinecap="round" />
      <path d="M14 20 C20 20, 22 30, 28 30 L36 30" stroke="currentColor" strokeWidth={sw} strokeLinecap="round" />
      <circle cx="36" cy="10" r={sw * 0.7} fill="currentColor" opacity="0.5" />
      <circle cx="36" cy="20" r={sw * 0.7} fill="currentColor" opacity="0.5" />
      <circle cx="36" cy="30" r={sw * 0.7} fill="currentColor" opacity="0.5" />
    </svg>
  );
}
