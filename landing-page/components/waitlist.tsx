"use client";

import { FormEvent, useEffect, useRef, useState } from "react";

export default function Waitlist() {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) setVisible(true);
      },
      { threshold: 0.2 }
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
    <section id="waitlist" ref={ref} className="py-32 px-6">
      <div
        className={`max-w-xl mx-auto text-center ${visible ? "animate-fade-in" : "opacity-0"}`}
      >
        <h2 className="text-3xl md:text-5xl font-bold tracking-tight mb-4">
          Currently invite-only.
        </h2>
        <p className="text-lg text-silver mb-10">
          Due to high demand, we&apos;re onboarding clients in batches. Join the
          waitlist and we&apos;ll reach out when your spot opens.
        </p>

        {status === "success" ? (
          <div className="bg-navy-card backdrop-blur-sm border border-violet/30 rounded-xl p-8">
            <p className="text-xl text-white font-medium">
              You&apos;re on the list. We&apos;ll be in touch.
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-4">
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="your@email.com"
              required
              className="flex-1 bg-navy-light border border-silver/20 rounded-lg px-6 py-4 text-white placeholder:text-silver/50 focus:outline-none focus:border-violet focus:shadow-[0_0_20px_rgba(99,102,241,0.3)] transition-all duration-200"
            />
            <button
              type="submit"
              disabled={status === "loading"}
              className="bg-amber hover:bg-amber-hover disabled:opacity-50 text-navy font-semibold px-8 py-4 rounded-lg text-lg transition-all duration-200 hover:scale-105 whitespace-nowrap"
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
