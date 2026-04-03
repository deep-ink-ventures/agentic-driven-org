const PROJECT_NAME = process.env.NEXT_PUBLIC_PROJECT_NAME || "AgentDriven";

export function BrandHeading({ className = "" }: { className?: string }) {
  return (
    <h1 className={`font-serif tracking-tight ${className}`}>
      <span className="text-accent-gold font-bold">{PROJECT_NAME}</span>
      <span className="text-text-secondary"> is an </span>
      <span className="text-text-primary">agent</span>
      <span className="text-text-secondary"> driven org</span>
    </h1>
  );
}

export function BrandLogo({ className = "" }: { className?: string }) {
  return (
    <span className={`font-serif tracking-tight ${className}`}>
      <span className="text-accent-gold font-bold">{PROJECT_NAME}</span>
      <span className="text-text-secondary"> is an </span>
      <span className="text-text-primary">agent</span>
      <span className="text-text-secondary"> driven org</span>
    </span>
  );
}
