"use client";

import Link from "next/link";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Calendar, Users, Building2 } from "lucide-react";
import type { Project } from "@/lib/types";

export function ProjectCard({ project }: { project: Project }) {
  return (
    <Link href={`/project/${project.id}`}>
      <Card className="bg-bg-surface border-border hover:border-accent-gold/50 transition-colors cursor-pointer group h-44 flex flex-col">
        <CardHeader className="pb-2">
          <h3 className="text-lg font-semibold text-text-heading group-hover:text-accent-gold transition-colors truncate">
            {project.name}
          </h3>
          {project.goal && (
            <p className="text-text-secondary text-xs mt-1 line-clamp-2">
              {project.goal}
            </p>
          )}
        </CardHeader>
        <CardContent className="flex flex-col justify-between flex-1">
          <div className="flex items-center gap-4 text-text-secondary text-xs">
            <span className="flex items-center gap-1">
              <Building2 className="h-3 w-3" />
              {project.department_count} dept{project.department_count !== 1 ? "s" : ""}
            </span>
            <span className="flex items-center gap-1">
              <Users className="h-3 w-3" />
              {project.agent_count} agent{project.agent_count !== 1 ? "s" : ""}
            </span>
          </div>
          <div className="flex items-center gap-1.5 text-text-secondary text-xs mt-auto">
            <Calendar className="h-3 w-3" />
            <span>{new Date(project.updated_at).toLocaleDateString()}</span>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
