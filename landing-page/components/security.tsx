"use client";

import { useEffect, useRef, useState } from "react";

const features = [
  { label: "Bring your own cloud", detail: "GCP, AWS, or Azure" },
  { label: "Data never leaves your infra", detail: "Your VPC, your rules" },
  { label: "Keys in your secret manager", detail: "Zero external access" },
  { label: "No vendor lock-in", detail: "Leave anytime, keep everything" },
];

export default function Security() {
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
    <section id="security" ref={ref} className="py-24 md:py-40 px-6 md:px-12 bg-navy-mid scroll-mt-14">
      <div className="max-w-6xl mx-auto">
        <div
          className={`grid md:grid-cols-[1.2fr_1fr] gap-16 md:gap-24 items-start ${
            visible ? "animate-fade-up" : "opacity-0"
          }`}
        >
          <div>
            <h2 className="font-display text-3xl md:text-5xl font-bold tracking-[-0.02em] leading-[1.1] mb-6">
              Your cloud. Your data.
              <br />
              Your keys.
            </h2>
            <p className="text-silver text-[16px] leading-relaxed max-w-md">
              Security-first architecture from day one. No data residency
              surprises. No compromises.
            </p>
          </div>

          <div className="space-y-0">
            {features.map((f, i) => (
              <div
                key={f.label}
                className={`flex justify-between items-baseline py-5 ${
                  i < features.length - 1 ? "border-b border-border" : ""
                }`}
              >
                <span className="text-heading font-medium text-[15px]">
                  {f.label}
                </span>
                <span className="text-silver text-sm">{f.detail}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
