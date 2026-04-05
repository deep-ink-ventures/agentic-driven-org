"use client";

import Link from "next/link";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Calendar, Users, Building2, ArrowRight, Settings2 } from "lucide-react";
import type { Project } from "@/lib/types";

interface ProjectCardProps {
  project: Project;
  onSetup?: (project: Project) => void;
}

export function ProjectCard({ project, onSetup }: ProjectCardProps) {
  const isSetup = project.status === "setup";

  const card = (
    <Card className="bg-bg-surface border-border hover:border-accent-gold/50 transition-colors cursor-pointer group flex flex-col">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-text-heading group-hover:text-accent-gold transition-colors truncate">
            {project.name}
          </h3>
          {isSetup && (
            <span className="shrink-0 text-[10px] font-medium px-2 py-0.5 rounded-full bg-accent-gold/15 text-accent-gold border border-accent-gold/30">
              Setup
            </span>
          )}
        </div>
        {project.goal && (
          <p className="text-text-secondary text-xs mt-1 line-clamp-1">
            {project.goal}
          </p>
        )}
      </CardHeader>
      <CardContent className="flex flex-col justify-between flex-1">
        {isSetup ? (
          <div className="flex items-center gap-2 text-text-secondary text-xs">
            <Settings2 className="h-3 w-3" />
            <span>
              {project.source_count} source{project.source_count !== 1 ? "s" : ""} added
              {project.bootstrap_status === "proposed" && " — review ready"}
              {project.bootstrap_status === "processing" && " — analyzing..."}
              {!project.bootstrap_status && project.source_count === 0 && " — add sources"}
            </span>
          </div>
        ) : (
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
        )}
        <div className="flex items-center justify-between mt-auto">
          <div className="flex items-center gap-1.5 text-text-secondary text-xs">
            <Calendar className="h-3 w-3" />
            <span>{new Date(project.updated_at).toLocaleDateString()}</span>
          </div>
          <span className={`flex items-center gap-1 text-xs font-medium ${isSetup ? "text-accent-gold" : "text-text-secondary group-hover:text-accent-gold"} transition-colors`}>
            {isSetup ? "Continue Setup" : "Open"}
            <ArrowRight className="h-3 w-3" />
          </span>
        </div>
      </CardContent>
    </Card>
  );

  if (isSetup) {
    return (
      <div onClick={() => onSetup?.(project)} className="cursor-pointer">
        {card}
      </div>
    );
  }

  return (
    <Link href={`/project/${project.slug}`}>
      {card}
    </Link>
  );
}
