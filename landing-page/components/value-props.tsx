"use client";

import { useEffect, useRef, useState } from "react";

const props = [
  {
    num: "01",
    title: "Agentic AI software",
    description:
      "Not chatbots. Not copilots. Autonomous agents that run departments, execute workflows, and take action. We built the stack. You deploy it.",
  },
  {
    num: "02",
    title: "Deep integration consulting",
    description:
      "We don\u2019t hand you software and disappear. We embed in your org, configure agents for your specific operations, and push you to the current state of the art.",
  },
  {
    num: "03",
    title: "Replace legacy, not people",
    description:
      "Kill the spreadsheets, the manual handoffs, the processes nobody remembers why they exist. Upskill your team. Modernize how your company actually works.",
  },
];

export default function ValueProps() {
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
        <div className="grid md:grid-cols-3 gap-x-16 gap-y-16">
          {props.map((prop, i) => (
            <div
              key={prop.num}
              className={`${visible ? "animate-fade-up" : "opacity-0"}`}
              style={{ animationDelay: `${i * 120}ms` }}
            >
              <span className="font-display text-xs font-medium tracking-[0.2em] text-violet/60 block mb-5">
                {prop.num}
              </span>
              <h3 className="font-display text-xl font-bold mb-4 text-heading">
                {prop.title}
              </h3>
              <p className="text-silver leading-relaxed text-[15px]">
                {prop.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
