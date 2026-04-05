"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";

export default function Quote() {
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
      <div
        className={`max-w-4xl mx-auto ${
          visible ? "animate-fade-up-slow" : "opacity-0"
        }`}
      >
        <svg
          className="w-10 h-10 text-violet/30 mb-8"
          viewBox="0 0 24 24"
          fill="currentColor"
        >
          <path d="M4.583 17.321C3.553 16.227 3 15 3 13.011c0-3.5 2.457-6.637 6.03-8.188l.893 1.378c-3.335 1.804-3.987 4.145-4.247 5.621.537-.278 1.24-.375 1.929-.311C9.591 11.69 11 13.166 11 15c0 1.933-1.567 3.5-3.5 3.5-1.079 0-2.18-.482-2.917-1.179zM14.583 17.321C13.553 16.227 13 15 13 13.011c0-3.5 2.457-6.637 6.03-8.188l.893 1.378c-3.335 1.804-3.987 4.145-4.247 5.621.537-.278 1.24-.375 1.929-.311C19.591 11.69 21 13.166 21 15c0 1.933-1.567 3.5-3.5 3.5-1.079 0-2.18-.482-2.917-1.179z" />
        </svg>

        <blockquote className="font-display text-2xl md:text-4xl font-medium text-heading leading-[1.3] tracking-[-0.01em]">
          The Agent Driven Org is the OpenClaw moment for the enterprises.
        </blockquote>

        <div className="mt-10 flex items-center gap-4">
          <Image
            src="/logos/frontiertower.jpeg"
            alt="Frontiertower"
            width={40}
            height={40}
            className="w-10 h-10 rounded-full object-cover"
          />
          <div>
            <p className="text-heading font-medium text-sm">Jakob Drzaga</p>
            <p className="text-secondary text-sm">Founder, Frontiertower</p>
          </div>
        </div>
      </div>
    </section>
  );
}
