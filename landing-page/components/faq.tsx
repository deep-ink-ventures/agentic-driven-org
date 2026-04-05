"use client";

import { useInView } from "@/hooks/use-in-view";
import { useState } from "react";

const questions = [
  {
    q: "What does an engagement look like?",
    a: "We start with a 30-minute call to map your operations. Then a focused 4\u20138 week engagement: we configure agents for your workflows, deploy to your cloud, and train your team to run it.",
  },
  {
    q: "Do I need my own cloud infrastructure?",
    a: "Optional. We can run it for you \u2014 GDPR-compliant, highest security standards, fully managed. Or you own the infrastructure: your GCP, AWS, or Azure account, your data, your agents. Everything is possible.",
  },
  {
    q: "How is this different from hiring an AI consultancy?",
    a: "Most consultancies deliver slide decks and prototypes. We deploy production systems. When we leave, you have working infrastructure \u2014 not a proof of concept.",
  },
  {
    q: "What happens after the engagement ends?",
    a: "You run it. The agents, workflows, and infrastructure are yours. We offer optional support retainers, but there\u2019s no lock-in. Everything works without us.",
  },
];

export default function FAQ() {
  const { ref, visible } = useInView();
  const [open, setOpen] = useState<number | null>(null);

  return (
    <section id="faq" ref={ref} className="py-16 md:py-24 lg:py-40 px-6 md:px-12 scroll-mt-14">
      <div className="max-w-3xl mx-auto">
        <div className={visible ? "animate-fade-in" : "opacity-0"}>
          <h2 className="font-display text-3xl md:text-5xl font-normal tracking-[-0.02em] leading-[1.1] mb-12">
            Common questions.
          </h2>

          <div className="divide-y divide-stone/10">
            {questions.map((item, i) => (
              <div key={i} className="py-6">
                <button
                  onClick={() => setOpen(open === i ? null : i)}
                  className="w-full flex justify-between items-start gap-4 text-left min-h-[44px] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-copper rounded-sm"
                  aria-expanded={open === i}
                >
                  <span className="text-white font-medium text-[15px]">
                    {item.q}
                  </span>
                  <span
                    className={`text-stone/40 text-lg shrink-0 transition-transform duration-200 ${
                      open === i ? "rotate-45" : ""
                    }`}
                    aria-hidden="true"
                  >
                    +
                  </span>
                </button>
                {open === i && (
                  <p className="mt-4 text-stone text-[15px] leading-relaxed max-w-2xl animate-fade-in">
                    {item.a}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
