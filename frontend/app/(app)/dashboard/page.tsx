"use client";

import { useAuth } from "@/hooks/use-auth";

export default function DashboardPage() {
  const { user } = useAuth();

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-3xl font-semibold mb-4">Dashboard</h1>
      <p className="text-text-secondary">
        Welcome{user?.first_name ? `, ${user.first_name}` : ""}. Your projects will appear here.
      </p>
    </div>
  );
}
