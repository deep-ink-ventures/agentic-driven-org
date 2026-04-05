"use client";

import { useEffect, useState } from "react";
import Logomark from "./logomark";

const links = [
  { label: "Product", href: "#product" },
  { label: "Consulting", href: "#consulting" },
  { label: "Security", href: "#security" },
  { label: "Waitlist", href: "#waitlist" },
];

export default function Nav() {
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 80);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // Lock body scroll when menu is open
  useEffect(() => {
    document.body.style.overflow = menuOpen ? "hidden" : "";
    return () => { document.body.style.overflow = ""; };
  }, [menuOpen]);

  return (
    <>
      <header
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
          scrolled || menuOpen
            ? "bg-ink/90 backdrop-blur-sm border-b border-copper/10"
            : "bg-transparent"
        }`}
      >
        <div className="max-w-6xl mx-auto px-6 md:px-12 flex items-center justify-between h-14">
          <a
            href="#"
            className="flex items-center gap-2.5 font-display text-white text-base focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-copper rounded-sm"
            aria-label="The Agent Driven Organization — back to top"
            onClick={() => setMenuOpen(false)}
          >
            <Logomark size={22} className="text-copper" />
            The Agent Driven Organization
          </a>

          {/* Desktop nav */}
          <nav aria-label="Main navigation" className="hidden sm:flex items-center gap-8">
            {links.map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="text-stone text-sm hover:text-white transition-colors duration-200 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-copper rounded-sm"
              >
                {link.label}
              </a>
            ))}
          </nav>

          {/* Mobile hamburger */}
          <button
            className="sm:hidden flex flex-col justify-center items-center w-11 h-11 gap-1.5 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-copper rounded-sm -mr-1.5"
            onClick={() => setMenuOpen(!menuOpen)}
            aria-label={menuOpen ? "Close menu" : "Open menu"}
            aria-expanded={menuOpen}
          >
            <span
              className={`block w-5 h-[1.5px] bg-white transition-all duration-200 ${
                menuOpen ? "rotate-45 translate-y-[4.5px]" : ""
              }`}
            />
            <span
              className={`block w-5 h-[1.5px] bg-white transition-all duration-200 ${
                menuOpen ? "-rotate-45 -translate-y-[1.5px]" : ""
              }`}
            />
          </button>
        </div>
      </header>

      {/* Mobile menu overlay — always mounted, animated via opacity+visibility */}
      <div
        className={`fixed inset-0 z-40 bg-ink/95 backdrop-blur-sm pt-20 px-6 sm:hidden transition-all duration-300 ${
          menuOpen
            ? "opacity-100 visible"
            : "opacity-0 invisible pointer-events-none"
        }`}
        aria-hidden={!menuOpen}
      >
        <nav aria-label="Mobile navigation" className="flex flex-col gap-2">
          {links.map((link, i) => (
            <a
              key={link.href}
              href={link.href}
              tabIndex={menuOpen ? 0 : -1}
              onClick={() => setMenuOpen(false)}
              className="font-display text-2xl text-white hover:text-copper transition-all duration-200 py-3"
              style={{
                transitionDelay: menuOpen ? `${i * 50}ms` : "0ms",
                opacity: menuOpen ? 1 : 0,
                transform: menuOpen ? "translateX(0)" : "translateX(-12px)",
              }}
            >
              {link.label}
            </a>
          ))}
        </nav>
      </div>
    </>
  );
}
