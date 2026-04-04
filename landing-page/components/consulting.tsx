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
      { threshold: 0.2 }
    );
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  return (
    <section ref={ref} className="py-32 px-6">
      <div
        className={`max-w-3xl mx-auto ${visible ? "animate-fade-in" : "opacity-0"}`}
      >
        <h2 className="text-3xl md:text-5xl font-bold tracking-tight mb-8">
          We don&apos;t just sell you software.
        </h2>

        <div className="space-y-6 text-lg text-silver leading-relaxed">
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
          <p className="text-white font-medium">
            We make your company agentic-first. Then you run it.
          </p>
        </div>
      </div>
    </section>
  );
}
