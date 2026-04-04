"use client";

import { useEffect, useRef, useState } from "react";

const props = [
  {
    title: "Agentic AI software",
    description:
      "Not chatbots. Not copilots. Autonomous agents that run departments, execute workflows, and take action. We built the stack. You deploy it.",
  },
  {
    title: "Deep integration consulting",
    description:
      "We don\u2019t hand you software and disappear. We embed in your org, configure agents for your specific operations, and push you to the current state of the art.",
  },
  {
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
      { threshold: 0.2 }
    );
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  return (
    <section ref={ref} className="py-32 px-6">
      <div className="max-w-6xl mx-auto grid md:grid-cols-3 gap-12">
        {props.map((prop, i) => (
          <div
            key={prop.title}
            className={`${
              visible ? "animate-fade-in" : "opacity-0"
            }`}
            style={{ animationDelay: `${i * 150}ms` }}
          >
            <h3 className="text-xl font-bold mb-4 text-white">{prop.title}</h3>
            <p className="text-silver leading-relaxed">{prop.description}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
