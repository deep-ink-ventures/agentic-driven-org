"use client";

import { useEffect, useRef, useState } from "react";

export default function Quote() {
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
        <div className="border-l-4 border-violet pl-8">
          <blockquote className="text-2xl md:text-3xl font-light text-silver-light leading-relaxed italic">
            &ldquo;Placeholder for client testimonial. Replace this with a real
            quote.&rdquo;
          </blockquote>
          <p className="mt-6 text-silver">
            <span className="text-white font-medium">Name Surname</span>
            {" — "}Title, Company
          </p>
        </div>
      </div>
    </section>
  );
}
