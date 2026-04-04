"use client";

import { useEffect, useRef, useState } from "react";

export default function Security() {
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
          Your cloud. Your data.{" "}
          <span className="bg-gradient-to-r from-violet to-violet-light bg-clip-text text-transparent">
            Your keys.
          </span>
        </h2>

        <div className="space-y-6 text-lg text-silver leading-relaxed">
          <p>
            Bring your own cloud — GCP, AWS, or Azure. Your data never touches
            our servers. API keys live in your secret manager. Agents run in your
            VPC.
          </p>
          <p className="text-white font-medium">
            No vendor lock-in. No data residency surprises. Security-first
            architecture from day one.
          </p>
        </div>
      </div>
    </section>
  );
}
