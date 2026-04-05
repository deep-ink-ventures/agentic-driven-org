"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import type { Project } from "@/lib/types";
import { ProjectCard } from "@/components/project-card";
import { CreateProjectWizard } from "@/components/create-project-wizard";
import { Plus } from "lucide-react";
import Logomark from "@/components/logomark";

function CardSkeleton() {
  return (
    <div className="rounded-xl border border-border bg-bg-surface p-4 animate-pulse">
      <div className="h-5 w-2/3 bg-bg-surface-hover rounded mb-3" />
      <div className="h-3 w-full bg-bg-surface-hover rounded mb-2" />
      <div className="h-3 w-1/2 bg-bg-surface-hover rounded mb-6" />
      <div className="flex justify-between">
        <div className="h-3 w-20 bg-bg-surface-hover rounded" />
        <div className="h-3 w-16 bg-bg-surface-hover rounded" />
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [showWizard, setShowWizard] = useState(false);
  const [wizardProject, setWizardProject] = useState<Project | null>(null);

  const loadProjects = useCallback(() => {
    setLoading(true);
    api.listProjects()
      .then(setProjects)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  function openNewWizard() {
    setWizardProject(null);
    setShowWizard(true);
  }

  function handleSetup(project: Project) {
    setWizardProject(project);
    setShowWizard(true);
  }

  function handleCloseWizard() {
    setShowWizard(false);
    setWizardProject(null);
  }

  function handleCreated() {
    setShowWizard(false);
    setWizardProject(null);
    loadProjects();
  }

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8 sm:py-10">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-semibold">Projects</h1>
          <p className="text-sm text-text-secondary mt-1">Your agent-driven workspaces</p>
        </div>
        <button
          onClick={openNewWizard}
          className="flex items-center gap-2 px-3 py-2 rounded-lg border border-border text-text-secondary hover:text-text-primary hover:border-accent-violet/50 transition-colors text-sm"
        >
          <Plus className="h-4 w-4" />
          <span className="hidden sm:inline">New Project</span>
          <span className="sm:hidden">New</span>
        </button>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
        </div>
      ) : projects.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 px-4">
          <div className="h-16 w-16 rounded-2xl bg-accent-violet/10 border border-accent-violet/20 flex items-center justify-center mb-6">
            <Logomark size={32} className="text-accent-violet" />
          </div>
          <h2 className="text-lg font-semibold text-text-heading mb-2">No projects yet</h2>
          <p className="text-text-secondary text-sm text-center max-w-sm mb-6">
            Create your first project to start building with AI agents. Add sources, configure departments, and let your agents get to work.
          </p>
          <button
            onClick={openNewWizard}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-accent-gold text-bg-primary hover:bg-accent-gold-hover font-medium text-sm transition-colors"
          >
            <Plus className="h-4 w-4" />
            Create Project
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((project) => (
            <ProjectCard
              key={project.id}
              project={project}
              onSetup={handleSetup}
            />
          ))}
        </div>
      )}

      {showWizard && (
        <CreateProjectWizard
          onClose={handleCloseWizard}
          onCreated={handleCreated}
          existingProject={wizardProject ?? undefined}
        />
      )}
    </div>
  );
}
