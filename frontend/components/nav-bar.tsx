"use client";

import { useState, useRef, useEffect } from "react";
import { useAuth } from "@/hooks/use-auth";
import Link from "next/link";
import { LogOut, User as UserIcon, ChevronDown } from "lucide-react";

export function NavBar() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const handleLogout = async () => {
    await logout();
    window.location.href = "/login";
  };

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  return (
    <nav className="h-14 border-b border-border/50 bg-bg-primary/80 backdrop-blur-md flex items-center justify-between px-6 sticky top-0 z-50">
      <Link href="/dashboard" className="flex items-center gap-2 group">
        <span className="text-2xl font-bold text-accent-gold font-serif tracking-tight">
          AgentDriven
        </span>
      </Link>

      <div className="relative" ref={menuRef}>
        <button
          onClick={() => setOpen(!open)}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-border/60 hover:border-accent-gold/30 hover:bg-bg-surface transition-all"
        >
          <div className="h-7 w-7 rounded-full bg-accent-gold/20 border border-accent-gold/30 flex items-center justify-center text-accent-gold">
            <UserIcon className="h-3.5 w-3.5" />
          </div>
          <ChevronDown className={`h-3.5 w-3.5 text-text-secondary transition-transform ${open ? "rotate-180" : ""}`} />
        </button>

        {open && (
          <div className="absolute right-0 mt-2 w-64 rounded-lg border border-border bg-bg-surface shadow-xl py-1 z-50">
            <div className="px-4 py-3 border-b border-border">
              <p className="text-xs text-text-secondary">Signed in as</p>
              <p className="text-sm text-text-primary font-medium truncate">{user?.email}</p>
            </div>

            <Link
              href="/dashboard"
              onClick={() => setOpen(false)}
              className="flex items-center gap-2 px-4 py-2 text-sm text-text-primary hover:bg-bg-surface-hover transition-colors"
            >
              Dashboard
            </Link>

            <button
              onClick={handleLogout}
              className="w-full flex items-center gap-2 px-4 py-2 text-sm text-flag-critical hover:bg-bg-surface-hover transition-colors"
            >
              <LogOut className="h-4 w-4" />
              Log out
            </button>
          </div>
        )}
      </div>
    </nav>
  );
}
