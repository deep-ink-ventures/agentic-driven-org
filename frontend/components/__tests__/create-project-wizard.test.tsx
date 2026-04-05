import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CreateProjectWizard } from "@/components/create-project-wizard";
import type { Project } from "@/lib/types";

// Mock ws module (dynamic import in the component)
vi.mock("@/lib/ws", () => ({
  connectWs: vi.fn().mockResolvedValue({ close: vi.fn() }),
}));

const mockCreateProject = vi.fn();
const mockUploadFile = vi.fn();
const mockAddSource = vi.fn();
const mockTriggerBootstrap = vi.fn();
const mockGetBootstrapLatest = vi.fn();
const mockApproveBootstrap = vi.fn();

vi.mock("@/lib/api", () => ({
  api: {
    createProject: (...args: unknown[]) => mockCreateProject(...args),
    uploadFile: (...args: unknown[]) => mockUploadFile(...args),
    addSource: (...args: unknown[]) => mockAddSource(...args),
    triggerBootstrap: (...args: unknown[]) => mockTriggerBootstrap(...args),
    getBootstrapLatest: (...args: unknown[]) => mockGetBootstrapLatest(...args),
    approveBootstrap: (...args: unknown[]) => mockApproveBootstrap(...args),
  },
}));

const onClose = vi.fn();
const onCreated = vi.fn();

beforeEach(() => {
  vi.clearAllMocks();
  mockCreateProject.mockResolvedValue({
    id: "new-project-id",
    name: "Test",
    slug: "test",
    goal: "",
    status: "setup",
    department_count: 0,
    agent_count: 0,
    source_count: 0,
    bootstrap_status: null,
    sources: [],
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-01-01T00:00:00Z",
  } satisfies Project);
  mockTriggerBootstrap.mockResolvedValue({
    id: "bp1",
    status: "processing",
    proposal: null,
    error_message: "",
    token_usage: null,
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-01-01T00:00:00Z",
  });
});

function renderWizard(existingProject?: Project) {
  return render(
    <CreateProjectWizard
      onClose={onClose}
      onCreated={onCreated}
      existingProject={existingProject}
    />,
  );
}

describe("CreateProjectWizard", () => {
  describe("Step 1 - Project", () => {
    it("renders first step with project name input", () => {
      renderWizard();
      expect(screen.getByLabelText("Project name")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /next/i })).toBeInTheDocument();
    });

    it("Next button is disabled when project name is empty", () => {
      renderWizard();
      expect(screen.getByRole("button", { name: /next/i })).toBeDisabled();
    });

    it("can enter project name and advance to next step", async () => {
      const user = userEvent.setup();
      renderWizard();

      await user.type(screen.getByLabelText("Project name"), "My New Project");
      await user.click(screen.getByRole("button", { name: /next/i }));

      await waitFor(() => {
        expect(mockCreateProject).toHaveBeenCalledWith({
          name: "My New Project",
          goal: undefined,
        });
      });

      // Should advance to step 2 (Sources)
      await waitFor(() => {
        expect(screen.getByText("Files")).toBeInTheDocument();
      });
    });

    it("can enter a goal alongside the project name", async () => {
      const user = userEvent.setup();
      renderWizard();

      await user.type(screen.getByLabelText("Project name"), "My Project");
      await user.type(
        screen.getByPlaceholderText("Describe what you want this project to achieve..."),
        "Build something great",
      );
      await user.click(screen.getByRole("button", { name: /next/i }));

      await waitFor(() => {
        expect(mockCreateProject).toHaveBeenCalledWith({
          name: "My Project",
          goal: "Build something great",
        });
      });
    });

    it("shows error when project creation fails", async () => {
      const user = userEvent.setup();
      mockCreateProject.mockRejectedValue(new Error("Server error"));
      renderWizard();

      await user.type(screen.getByLabelText("Project name"), "My Project");
      await user.click(screen.getByRole("button", { name: /next/i }));

      await waitFor(() => {
        expect(screen.getByText("Server error")).toBeInTheDocument();
      });
    });
  });

  describe("Step 2 - Sources", () => {
    async function goToStep2() {
      const user = userEvent.setup();
      renderWizard();
      await user.type(screen.getByLabelText("Project name"), "Test");
      await user.click(screen.getByRole("button", { name: /next/i }));
      await waitFor(() => {
        expect(screen.getByText("Files")).toBeInTheDocument();
      });
      return user;
    }

    it("can add a URL source", async () => {
      const user = await goToStep2();
      const urlInput = screen.getByPlaceholderText("https://example.com/about");
      await user.type(urlInput, "https://example.com");
      await user.click(screen.getByRole("button", { name: /add/i }));

      expect(screen.getByText("https://example.com")).toBeInTheDocument();
    });

    it("shows error for invalid URL", async () => {
      const user = await goToStep2();
      const urlInput = screen.getByPlaceholderText("https://example.com/about");
      await user.type(urlInput, "not-a-url");
      await user.click(screen.getByRole("button", { name: /add/i }));

      expect(screen.getByText("Please enter a valid URL")).toBeInTheDocument();
    });

    it("shows Skip when no sources added", async () => {
      await goToStep2();
      expect(screen.getByRole("button", { name: /skip/i })).toBeInTheDocument();
    });

    it("shows Next when sources are added", async () => {
      const user = await goToStep2();
      const urlInput = screen.getByPlaceholderText("https://example.com/about");
      await user.type(urlInput, "https://example.com");
      await user.click(screen.getByRole("button", { name: /add/i }));

      // Button text should now be "Next" instead of "Skip"
      const buttons = screen.getAllByRole("button");
      const nextBtn = buttons.find((b) => b.textContent?.includes("Next"));
      expect(nextBtn).toBeTruthy();
    });

    it("back button navigates to step 1", async () => {
      const user = await goToStep2();
      await user.click(screen.getByRole("button", { name: /back/i }));

      await waitFor(() => {
        expect(screen.getByLabelText("Project name")).toBeInTheDocument();
      });
    });
  });

  describe("Step 3 - Misc", () => {
    async function goToStep3() {
      const user = userEvent.setup();
      renderWizard();
      // Step 1
      await user.type(screen.getByLabelText("Project name"), "Test");
      await user.click(screen.getByRole("button", { name: /next/i }));
      await waitFor(() => expect(screen.getByText("Files")).toBeInTheDocument());
      // Step 2 - skip
      await user.click(screen.getByRole("button", { name: /skip/i }));
      await waitFor(() => expect(screen.getByText("Additional context")).toBeInTheDocument());
      return user;
    }

    it("can enter additional text", async () => {
      const user = await goToStep3();
      const textarea = screen.getByPlaceholderText("Company info, product descriptions, notes...");
      await user.type(textarea, "Some extra context");
      expect(textarea).toHaveValue("Some extra context");
    });

    it("back button goes to step 2", async () => {
      const user = await goToStep3();
      await user.click(screen.getByRole("button", { name: /back/i }));
      await waitFor(() => expect(screen.getByText("Files")).toBeInTheDocument());
    });
  });

  describe("Step 4 - Bootstrap", () => {
    it("triggers bootstrap and shows loading state", async () => {
      const user = userEvent.setup();
      renderWizard();
      // Step 1
      await user.type(screen.getByLabelText("Project name"), "Test");
      await user.click(screen.getByRole("button", { name: /next/i }));
      await waitFor(() => expect(screen.getByText("Files")).toBeInTheDocument());
      // Step 2 - skip
      await user.click(screen.getByRole("button", { name: /skip/i }));
      await waitFor(() => expect(screen.getByText("Additional context")).toBeInTheDocument());
      // Step 3 - skip
      await user.click(screen.getByRole("button", { name: /skip/i }));

      await waitFor(() => {
        expect(mockTriggerBootstrap).toHaveBeenCalledWith("new-project-id");
      });

      // Should show loading/processing UI
      expect(screen.getByText("Designing your organization")).toBeInTheDocument();
    });
  });

  describe("Close button", () => {
    it("calls onClose when clicking X", async () => {
      const user = userEvent.setup();
      renderWizard();
      // The X button is the last button in the header
      const closeBtn = screen.getByRole("button", { name: "" });
      await user.click(closeBtn);
      expect(onClose).toHaveBeenCalledOnce();
    });
  });
});
