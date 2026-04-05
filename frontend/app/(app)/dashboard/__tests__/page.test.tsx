import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import DashboardPage from "@/app/(app)/dashboard/page";
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

// Mock the ws module used by CreateProjectWizard
vi.mock("@/lib/ws", () => ({
  connectWs: vi.fn(),
}));

const mockListProjects = vi.fn();

vi.mock("@/lib/api", () => ({
  api: {
    listProjects: (...args: unknown[]) => mockListProjects(...args),
    createProject: vi.fn(),
    uploadFile: vi.fn(),
    addSource: vi.fn(),
    triggerBootstrap: vi.fn(),
    getBootstrapLatest: vi.fn(),
    approveBootstrap: vi.fn(),
  },
}));

function makeProject(overrides: Partial<Project> = {}): Project {
  return {
    id: "p1",
    name: "My Project",
    slug: "my-project",
    goal: "Test goal",
    status: "active",
    department_count: 2,
    agent_count: 4,
    source_count: 1,
    bootstrap_status: null,
    sources: [],
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-03-15T00:00:00Z",
    ...overrides,
  };
}

beforeEach(() => {
  mockListProjects.mockReset();
});

describe("DashboardPage", () => {
  it("renders loading state initially", () => {
    mockListProjects.mockReturnValue(new Promise(() => {})); // never resolves
    render(<DashboardPage />);
    expect(screen.getByText("Projects")).toBeInTheDocument();
    // The Loader2 spinner is rendered as an SVG with animate-spin class
    expect(document.querySelector(".animate-spin")).toBeInTheDocument();
  });

  it("shows project list after loading", async () => {
    mockListProjects.mockResolvedValue([
      makeProject(),
      makeProject({ id: "p2", name: "Second", slug: "second" }),
    ]);
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText("My Project")).toBeInTheDocument();
    });
    expect(screen.getByText("Second")).toBeInTheDocument();
  });

  it("shows empty state when no projects", async () => {
    mockListProjects.mockResolvedValue([]);
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText(/No projects yet/)).toBeInTheDocument();
    });
  });

  it("has a create project button", async () => {
    mockListProjects.mockResolvedValue([]);
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText("New Project")).toBeInTheDocument();
    });
  });

  it("opens wizard when clicking New Project", async () => {
    const user = userEvent.setup();
    mockListProjects.mockResolvedValue([]);
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText("New Project")).toBeInTheDocument();
    });
    await user.click(screen.getByText("New Project"));
    // Wizard should show step 1 with project name input
    expect(screen.getByLabelText("Project name")).toBeInTheDocument();
  });
});
