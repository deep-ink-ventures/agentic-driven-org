"use client";

import { useEffect, useRef, useState } from "react";

export default function Consulting() {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

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

  return (
    <section ref={ref} className="py-24 md:py-40 px-6 md:px-12">
      <div className="max-w-6xl mx-auto">
        <div
          className={`max-w-2xl ${visible ? "animate-fade-up" : "opacity-0"}`}
        >
          <h2 className="font-display text-3xl md:text-5xl font-bold tracking-[-0.02em] leading-[1.1] mb-10">
            We don&apos;t just sell
            <br />
            you software.
          </h2>

          <div className="space-y-6 text-[16px] text-silver leading-relaxed">
            <p>
              Most AI consultancies give you a slide deck and a proof of concept.
              We deploy production systems.
            </p>
            <p>
              AgentDriven consultants embed in your organization. We map your
              operations, configure agentic workflows, and ship working
              infrastructure. Focused engagements, technical depth, measurable
              outcomes.
            </p>
          </div>

          <p className="mt-10 text-white font-display font-medium text-xl leading-snug">
            We make your company agentic-first.
            <br />
            <span className="text-silver">Then you run it.</span>
          </p>
        </div>
      </div>
    </section>
  );
}
