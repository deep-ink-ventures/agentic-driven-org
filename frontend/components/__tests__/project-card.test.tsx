import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ProjectCard } from "@/components/project-card";
import type { Project } from "@/lib/types";

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    ...props
  }: {
    children: React.ReactNode;
    href: string;
    [key: string]: unknown;
  }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

function makeProject(overrides: Partial<Project> = {}): Project {
  return {
    id: "p1",
    name: "Test Project",
    slug: "test-project",
    goal: "A test goal",
    status: "active",
    department_count: 3,
    agent_count: 5,
    source_count: 2,
    bootstrap_status: null,
    sources: [],
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-03-15T00:00:00Z",
    ...overrides,
  };
}

describe("ProjectCard", () => {
  it("renders project name", () => {
    render(<ProjectCard project={makeProject()} />);
    expect(screen.getByText("Test Project")).toBeInTheDocument();
  });

  it("renders department and agent counts for active projects", () => {
    render(<ProjectCard project={makeProject()} />);
    expect(screen.getByText("3 depts")).toBeInTheDocument();
    expect(screen.getByText("5 agents")).toBeInTheDocument();
  });

  it("links to correct project page for active projects", () => {
    render(<ProjectCard project={makeProject()} />);
    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "/project/test-project");
  });

  it("shows setup badge and source info for setup status", () => {
    render(
      <ProjectCard
        project={makeProject({
          status: "setup",
          source_count: 0,
          bootstrap_status: null,
        })}
      />,
    );
    expect(screen.getByText("Setup")).toBeInTheDocument();
    expect(screen.getByText(/0 sources added/)).toBeInTheDocument();
    expect(screen.getByText("Continue Setup")).toBeInTheDocument();
  });

  it("calls onSetup when clicking a setup project", async () => {
    const user = userEvent.setup();
    const onSetup = vi.fn();
    const project = makeProject({ status: "setup" });
    render(<ProjectCard project={project} onSetup={onSetup} />);
    // Setup cards are wrapped in a div with onClick, not a link
    await user.click(screen.getByText("Test Project"));
    expect(onSetup).toHaveBeenCalledWith(project);
  });

  it("shows review ready for proposed bootstrap status", () => {
    render(
      <ProjectCard
        project={makeProject({
          status: "setup",
          source_count: 2,
          bootstrap_status: "proposed",
        })}
      />,
    );
    expect(screen.getByText(/review ready/)).toBeInTheDocument();
  });
});
