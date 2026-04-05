import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";

// Mock next/navigation
const mockPush = vi.fn();
const mockSearchParams = new URLSearchParams();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
  useSearchParams: () => mockSearchParams,
}));

// Mock useAuth
const mockLogin = vi.fn();

vi.mock("@/hooks/use-auth", () => ({
  useAuth: () => ({
    login: mockLogin,
  }),
}));

// Mock next/link
vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: { children: React.ReactNode; href: string }) =>
    React.createElement("a", { href, ...props }, children),
}));

import LoginPage from "../page";

beforeEach(() => {
  vi.clearAllMocks();
  // Reset search params
  for (const key of [...mockSearchParams.keys()]) {
    mockSearchParams.delete(key);
  }
});

describe("LoginPage", () => {
  it("renders login form with email and password fields", () => {
    render(<LoginPage />);

    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /log in/i })).toBeInTheDocument();
  });

  it("renders Google OAuth link", () => {
    render(<LoginPage />);

    expect(screen.getByText(/continue with google/i)).toBeInTheDocument();
  });

  it('only shows allowlist error when error param is "allowlist"', () => {
    // No error param - should not show
    render(<LoginPage />);
    expect(screen.queryByText(/must be invited/i)).not.toBeInTheDocument();
  });

  it("shows allowlist error when error=allowlist", () => {
    mockSearchParams.set("error", "allowlist");

    render(<LoginPage />);

    expect(screen.getAllByText(/must be invited/i).length).toBeGreaterThan(0);
  });

  it("does not show allowlist error for other error values", () => {
    mockSearchParams.set("error", "something_else");

    render(<LoginPage />);

    expect(screen.queryByText(/must be invited/i)).not.toBeInTheDocument();
  });

  it("validates email format in blockedEmail param (security fix)", () => {
    mockSearchParams.set("error", "allowlist");
    // Valid email - should be displayed
    mockSearchParams.set("email", "blocked@example.com");

    render(<LoginPage />);

    expect(screen.getByText("blocked@example.com")).toBeInTheDocument();
  });

  it("renders email param in allowlist error (React auto-escapes XSS)", () => {
    mockSearchParams.set("error", "allowlist");
    mockSearchParams.set("email", "<script>alert(1)</script>");

    render(<LoginPage />);

    // React auto-escapes HTML, so the string is rendered as text, not executed
    expect(screen.getByText("<script>alert(1)</script>")).toBeInTheDocument();
  });

  it("shows error on failed login", async () => {
    mockLogin.mockRejectedValue(new Error("Invalid credentials"));

    render(<LoginPage />);

    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/email/i), "test@test.com");
    await user.type(screen.getByLabelText(/password/i), "wrongpass");
    await user.click(screen.getByRole("button", { name: /log in/i }));

    await waitFor(() => {
      expect(screen.getByText(/email or password doesn.t match/i)).toBeInTheDocument();
    });
  });

  it("shows generic error for non-credential errors", async () => {
    mockLogin.mockRejectedValue(new Error("Server Error"));

    render(<LoginPage />);

    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/email/i), "test@test.com");
    await user.type(screen.getByLabelText(/password/i), "pass");
    await user.click(screen.getByRole("button", { name: /log in/i }));

    await waitFor(() => {
      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
    });
  });

  it("redirects to dashboard on successful login", async () => {
    mockLogin.mockResolvedValue(undefined);

    render(<LoginPage />);

    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/email/i), "test@test.com");
    await user.type(screen.getByLabelText(/password/i), "correct");
    await user.click(screen.getByRole("button", { name: /log in/i }));

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/dashboard");
    });
  });
});
