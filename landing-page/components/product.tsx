"use client";

import { useEffect, useRef, useState } from "react";

export default function Product() {
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
          An agentic stack you actually{" "}
          <span className="bg-gradient-to-r from-violet to-violet-light bg-clip-text text-transparent">
            own.
          </span>
        </h2>

        <div className="space-y-6 text-lg text-silver leading-relaxed">
          <p>
            AgentDriven is a full agentic AI platform. Departments staffed by AI
            agents. Configurable workflows that adapt to your business logic.
            Automated actions across your entire operation.
          </p>
          <p>
            It runs on your cloud. You control the infrastructure, the data, and
            the agents. No black boxes. No mystery APIs. Every decision is
            traceable, every workflow is yours to modify.
          </p>
          <p className="text-white font-medium">
            This isn&apos;t another SaaS you subscribe to. It&apos;s infrastructure you
            own.
          </p>
        </div>
      </div>
    </section>
  );
}
