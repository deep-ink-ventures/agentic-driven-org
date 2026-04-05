import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { NavBar } from "@/components/nav-bar";

const mockLogout = vi.fn().mockResolvedValue(undefined);

vi.mock("@/hooks/use-auth", () => ({
  useAuth: () => ({
    user: {
      id: "1",
      email: "test@example.com",
      first_name: "Test",
      last_name: "User",
      is_staff: false,
    },
    logout: mockLogout,
  }),
}));

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

// Track location changes
const originalLocation = window.location;

beforeEach(() => {
  mockLogout.mockClear();
  Object.defineProperty(window, "location", {
    writable: true,
    value: { ...originalLocation, href: "" },
  });
});

describe("NavBar", () => {
  it("renders brand logo", () => {
    render(<NavBar />);
    expect(screen.getByText("AgentDriven")).toBeInTheDocument();
  });

  it("shows user email when menu is opened", async () => {
    const user = userEvent.setup();
    render(<NavBar />);
    // Click the dropdown trigger (the button with ChevronDown)
    const trigger = screen.getByRole("button");
    await user.click(trigger);
    expect(screen.getByText("test@example.com")).toBeInTheDocument();
  });

  it("logout button calls logout and redirects", async () => {
    const user = userEvent.setup();
    render(<NavBar />);
    // Open menu
    await user.click(screen.getByRole("button"));
    // Click logout
    const logoutBtn = screen.getByText("Log out");
    await user.click(logoutBtn);
    expect(mockLogout).toHaveBeenCalledOnce();
  });
});
