"use client";

import { useInView } from "@/hooks/use-in-view";
import Image from "next/image";

const clients = [
  { name: "Frontiertower", logo: "/logos/frontiertower.jpeg" },
  { name: "Superhero Residency", logo: "/logos/superheroresidency.jpg" },
  { name: "Deep Ink Ventures", logo: "/logos/deep-ink.png" },
];

export default function Logos() {
  const { ref, visible } = useInView();

  return (
    <section ref={ref} className="py-16 md:py-24 px-6 md:px-12 border-t border-stone/5">
      <div
        className={`max-w-6xl mx-auto ${visible ? "animate-fade-in" : "opacity-0"}`}
      >
        <p className="text-xs font-semibold tracking-[0.2em] uppercase text-stone/40 mb-10 text-center">
          Trusted by forward-thinking teams
        </p>
        <div className="flex flex-wrap justify-center items-center gap-x-12 gap-y-6 md:gap-x-20">
          {clients.map((client) => (
            <div key={client.name} className="flex items-center gap-3">
              <Image
                src={client.logo}
                alt={client.name}
                width={32}
                height={32}
                className="w-8 h-8 rounded-md object-cover"
              />
              <span className="text-stone/50 text-sm font-medium tracking-wide whitespace-nowrap">
                {client.name}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
