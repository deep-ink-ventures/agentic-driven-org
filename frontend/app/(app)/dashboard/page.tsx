"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import type { Project } from "@/lib/types";
import { ProjectCard } from "@/components/project-card";
import { CreateProjectWizard } from "@/components/create-project-wizard";
import { Plus, Loader2 } from "lucide-react";

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
    <div className="max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-semibold">Projects</h1>
        <button
          onClick={openNewWizard}
          className="flex items-center gap-2 px-3 py-2 rounded-lg border border-border text-text-secondary hover:text-text-primary hover:border-accent-gold/50 transition-colors text-sm"
        >
          <Plus className="h-4 w-4" />
          New Project
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-6 w-6 text-text-secondary animate-spin" />
        </div>
      ) : projects.length === 0 ? (
        <div className="text-center py-20">
          <p className="text-text-secondary mb-4">No projects yet. Create your first one to get started.</p>
          <button
            onClick={openNewWizard}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-accent-gold text-bg-primary hover:bg-accent-gold-hover font-medium text-sm transition-colors"
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
