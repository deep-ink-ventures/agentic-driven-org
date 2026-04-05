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
      { threshold: 0.15 }
    );
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  return (
    <section ref={ref} className="py-24 md:py-40 px-6 md:px-12 bg-navy-mid">
      <div className="max-w-6xl mx-auto">
        <div
          className={`grid md:grid-cols-[1fr_1.2fr] gap-16 md:gap-24 items-start ${
            visible ? "animate-fade-up" : "opacity-0"
          }`}
        >
          <div>
            <h2 className="font-display text-3xl md:text-5xl font-bold tracking-[-0.02em] leading-[1.1]">
              An agentic stack
              <br />
              you actually own.
            </h2>
          </div>

          <div className="space-y-6 text-[16px] text-silver leading-relaxed">
            <p>
              AgentDriven is a full agentic AI platform. Departments staffed by
              AI agents. Configurable workflows that adapt to your business
              logic. Automated actions across your entire operation.
            </p>
            <p>
              It runs on your cloud. You control the infrastructure, the data,
              and the agents. No black boxes. No mystery APIs. Every decision is
              traceable, every workflow is yours to modify.
            </p>
            <p className="text-heading font-medium text-[17px]">
              This isn&apos;t another SaaS you subscribe to. It&apos;s
              infrastructure you own.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
