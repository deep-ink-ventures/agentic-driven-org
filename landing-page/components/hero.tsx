"use client";

export default function Hero() {
  return (
    <section className="relative min-h-screen flex items-end overflow-hidden pb-24 md:pb-32">
      {/* Subtle radial glow — not a gradient wash */}
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse 80% 60% at 70% 20%, rgba(124, 106, 239, 0.12) 0%, transparent 60%), radial-gradient(ellipse 50% 50% at 20% 80%, rgba(245, 158, 11, 0.05) 0%, transparent 50%)",
        }}
      />

      {/* Grain texture overlay */}
      <div
        className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage:
            "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E\")",
        }}
      />

      <div className="relative z-10 max-w-6xl mx-auto px-6 md:px-12 w-full">
        <div className="max-w-3xl">
          <p className="text-sm font-medium tracking-[0.2em] uppercase text-violet mb-6 opacity-80">
            Agentic AI Infrastructure & Consulting
          </p>

          <h1 className="font-display text-5xl sm:text-6xl md:text-8xl font-bold tracking-[-0.03em] leading-[0.95] mb-8">
            Your company,
            <br />
            run by agents.
          </h1>

          <p className="text-lg md:text-xl text-silver max-w-xl mb-12 leading-relaxed">
            We build agentic AI infrastructure and embed it into your
            organization. Autonomous agents that run departments, execute
            workflows, and make decisions — on your cloud.
          </p>

          <a
            href="#waitlist"
            className="group inline-flex items-center gap-3 bg-amber hover:bg-amber-hover text-navy font-semibold px-8 py-4 rounded-lg text-base transition-all duration-300 hover:translate-y-[-1px] hover:shadow-[0_8px_30px_rgba(245,158,11,0.25)]"
          >
            Get early access
            <svg
              className="w-4 h-4 transition-transform duration-300 group-hover:translate-x-1"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2.5}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M17.25 8.25L21 12m0 0l-3.75 3.75M21 12H3" />
            </svg>
          </a>
        </div>
      </div>

      {/* Bottom fade */}
      <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-navy to-transparent" />
    </section>
  );
}
