import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";
import { AuthProvider, AuthContext } from "../auth-provider";

// Mock the api module
const mockGetSession = vi.fn();
const mockLogin = vi.fn();
const mockSignup = vi.fn();
const mockLogout = vi.fn();

vi.mock("@/lib/api", () => ({
  api: {
    getSession: (...args: unknown[]) => mockGetSession(...args),
    login: (...args: unknown[]) => mockLogin(...args),
    signup: (...args: unknown[]) => mockSignup(...args),
    logout: (...args: unknown[]) => mockLogout(...args),
  },
}));

// Helper component to access auth context
function AuthConsumer() {
  const ctx = React.useContext(AuthContext);
  return (
    <div>
      <span data-testid="loading">{String(ctx.loading)}</span>
      <span data-testid="user">{ctx.user ? ctx.user.email : "null"}</span>
      <button onClick={() => ctx.login("test@test.com", "pass")}>Login</button>
      <button onClick={() => ctx.logout()}>Logout</button>
    </div>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mockGetSession.mockResolvedValue({ user: null });
});

describe("AuthProvider", () => {
  it("fetches session on mount", async () => {
    render(
      <AuthProvider>
        <AuthConsumer />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(mockGetSession).toHaveBeenCalledTimes(1);
    });
  });

  it("sets user when session returns authenticated user", async () => {
    mockGetSession.mockResolvedValue({
      user: {
        id: "1",
        email: "user@test.com",
        first_name: "Test",
        last_name: "User",
        is_staff: false,
      },
    });

    render(
      <AuthProvider>
        <AuthConsumer />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("user").textContent).toBe("user@test.com");
    });
  });

  it("login() calls api.login and updates user state", async () => {
    mockLogin.mockResolvedValue({
      user: { id: "2", email: "logged@in.com", first_name: "L", last_name: "I", is_staff: false },
    });

    render(
      <AuthProvider>
        <AuthConsumer />
      </AuthProvider>,
    );

    // Wait for initial session fetch
    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("false");
    });

    const user = userEvent.setup();
    await user.click(screen.getByText("Login"));

    expect(mockLogin).toHaveBeenCalledWith("test@test.com", "pass");
    await waitFor(() => {
      expect(screen.getByTestId("user").textContent).toBe("logged@in.com");
    });
  });

  it("logout() calls api.logout and clears user", async () => {
    mockGetSession.mockResolvedValue({
      user: { id: "1", email: "user@test.com", first_name: "T", last_name: "U", is_staff: false },
    });
    mockLogout.mockResolvedValue(undefined);

    render(
      <AuthProvider>
        <AuthConsumer />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("user").textContent).toBe("user@test.com");
    });

    const user = userEvent.setup();
    await user.click(screen.getByText("Logout"));

    expect(mockLogout).toHaveBeenCalledTimes(1);
    await waitFor(() => {
      expect(screen.getByTestId("user").textContent).toBe("null");
    });
  });

  it("sets user to null if session fetch fails", async () => {
    mockGetSession.mockRejectedValue(new Error("network error"));

    render(
      <AuthProvider>
        <AuthConsumer />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("false");
      expect(screen.getByTestId("user").textContent).toBe("null");
    });
  });
});

describe("useAuth outside provider", () => {
  it("returns default context values (loading: true, user: null) when used outside provider", () => {
    // The default context has loading: true and user: null
    function Naked() {
      const ctx = React.useContext(AuthContext);
      return (
        <div>
          <span data-testid="loading">{String(ctx.loading)}</span>
          <span data-testid="user">{ctx.user ? "has-user" : "null"}</span>
        </div>
      );
    }

    render(<Naked />);
    expect(screen.getByTestId("loading").textContent).toBe("true");
    expect(screen.getByTestId("user").textContent).toBe("null");
  });
});
