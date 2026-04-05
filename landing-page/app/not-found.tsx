import Link from "next/link";

export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center px-6 md:px-12">
      <div className="max-w-xl mx-auto">
        <p className="text-sm font-medium tracking-[0.2em] uppercase text-copper mb-6 opacity-80">
          404
        </p>
        <h1 className="font-display text-4xl md:text-6xl font-normal tracking-[-0.02em] leading-[0.95] mb-6">
          Page not found.
        </h1>
        <p className="text-stone text-lg mb-10 leading-relaxed">
          The page you&apos;re looking for doesn&apos;t exist or has been moved.
        </p>
        <Link
          href="/"
          className="inline-flex items-center gap-3 bg-gold hover:bg-gold-hover text-ink font-semibold px-8 py-4 rounded-lg text-base transition-all duration-300 hover:translate-y-[-1px] hover:shadow-[0_8px_30px_rgba(212,168,83,0.25)] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-copper"
        >
          Back to home
        </Link>
      </div>
    </div>
  );
}
