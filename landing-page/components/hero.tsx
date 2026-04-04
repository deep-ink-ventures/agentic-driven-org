"use client";

export default function Hero() {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden">
      {/* Animated gradient background */}
      <div
        className="absolute inset-0 animate-gradient-shift"
        style={{
          background:
            "linear-gradient(135deg, #0a0e1a 0%, #1e1b4b 25%, #312e81 50%, #1e1b4b 75%, #0a0e1a 100%)",
          backgroundSize: "400% 400%",
        }}
      />

      {/* Gradient overlay for depth */}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-navy" />

      <div className="relative z-10 max-w-4xl mx-auto px-6 text-center">
        <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6">
          Your company,{" "}
          <span className="bg-gradient-to-r from-violet to-violet-light bg-clip-text text-transparent">
            run by agents.
          </span>
        </h1>

        <p className="text-lg md:text-xl text-silver max-w-2xl mx-auto mb-10 leading-relaxed">
          AgentDriven builds agentic AI infrastructure and embeds it into your
          organization. Autonomous agents that handle departments, execute
          workflows, and make decisions — deployed on your own cloud.
        </p>

        <a
          href="#waitlist"
          className="inline-block bg-amber hover:bg-amber-hover text-navy font-semibold px-8 py-4 rounded-lg text-lg transition-all duration-200 hover:scale-105"
        >
          Get early access
        </a>
      </div>
    </section>
  );
}
