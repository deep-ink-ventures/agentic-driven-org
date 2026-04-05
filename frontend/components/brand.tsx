import Logomark from "@/components/logomark";

const PROJECT_NAME = process.env.NEXT_PUBLIC_PROJECT_NAME || "AgentDriven";

export function BrandHeading({ className = "" }: { className?: string }) {
  return (
    <h1 className={`font-serif tracking-tight ${className}`}>
      <span className="text-text-heading font-bold">{PROJECT_NAME}</span>
      <span className="text-text-secondary"> as </span>
      <span className="text-text-primary">agent</span>
      <span className="text-text-secondary"> driven org</span>
    </h1>
  );
}

export function BrandLogo({ className = "", compact = false }: { className?: string; compact?: boolean }) {
  if (compact) {
    return (
      <span className={`font-serif tracking-tight inline-flex items-center gap-2 ${className}`}>
        <Logomark size={20} className="text-accent-violet" />
        <span className="text-text-heading font-bold">{PROJECT_NAME}</span>
      </span>
    );
  }
  return (
    <span className={`font-serif tracking-tight inline-flex items-center gap-2.5 ${className}`}>
      <Logomark size={22} className="text-accent-violet" />
      <span>
        <span className="text-text-heading font-bold">{PROJECT_NAME}</span>
        <span className="text-text-secondary"> as </span>
        <span className="text-text-primary">agent</span>
        <span className="text-text-secondary"> driven org</span>
      </span>
    </span>
  );
}

export function BrandIcon({ size = 22, className = "" }: { size?: number; className?: string }) {
  return <Logomark size={size} className={`text-accent-violet ${className}`} />;
}
