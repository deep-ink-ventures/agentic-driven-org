"use client";

import { FormEvent, useEffect, useRef, useState } from "react";

export default function Waitlist() {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<
    "idle" | "loading" | "success" | "error"
  >("idle");
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) setVisible(true);
      },
      { threshold: 0.15 }
    );
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setStatus("loading");
    setErrorMessage("");

    const res = await fetch("/api/waitlist", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });

    const data = await res.json();

    if (data.success) {
      setStatus("success");
      setEmail("");
    } else {
      setStatus("error");
      setErrorMessage(data.error || "Something went wrong.");
    }
  }

  return (
    <section id="waitlist" ref={ref} className="py-24 md:py-40 px-6 md:px-12 bg-navy-mid scroll-mt-14">
      <div
        className={`max-w-2xl mx-auto ${
          visible ? "animate-fade-up" : "opacity-0"
        }`}
      >
        <p className="text-sm font-medium tracking-[0.2em] uppercase text-amber/80 mb-6">
          Limited availability
        </p>

        <h2 className="font-display text-3xl md:text-5xl font-bold tracking-[-0.02em] leading-[1.1] mb-4">
          Currently invite-only.
        </h2>

        <p className="text-[16px] text-silver mb-12 max-w-lg leading-relaxed">
          We&apos;re onboarding clients in batches to ensure deep, focused
          engagements. Join the waitlist and we&apos;ll reach out when your spot
          opens.
        </p>

        {status === "success" ? (
          <div className="py-6 border-t border-violet/20">
            <p className="text-lg text-heading font-display font-medium">
              You&apos;re on the list. We&apos;ll be in touch.
            </p>
          </div>
        ) : (
          <form
            onSubmit={handleSubmit}
            className="flex flex-col sm:flex-row gap-3"
          >
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="your@email.com"
              required
              className="flex-1 bg-navy border border-border rounded-lg px-5 py-3.5 text-primary text-[15px] placeholder:text-secondary/40 focus:outline-none focus:border-violet/50 transition-colors duration-200"
            />
            <button
              type="submit"
              disabled={status === "loading"}
              className="bg-amber hover:bg-amber-hover disabled:opacity-50 text-navy font-semibold px-7 py-3.5 rounded-lg text-[15px] transition-all duration-200 hover:translate-y-[-1px] whitespace-nowrap"
            >
              {status === "loading" ? "Joining..." : "Join the waitlist"}
            </button>
          </form>
        )}

        {status === "error" && (
          <p className="mt-4 text-red-400 text-sm">{errorMessage}</p>
        )}
      </div>
    </section>
  );
}
