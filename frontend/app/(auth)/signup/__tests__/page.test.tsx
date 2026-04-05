import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SignupPage from "@/app/(auth)/signup/page";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
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

const mockSignup = vi.fn();

vi.mock("@/hooks/use-auth", () => ({
  useAuth: () => ({
    signup: mockSignup,
  }),
}));

beforeEach(() => {
  mockPush.mockClear();
  mockSignup.mockReset();
});

describe("SignupPage", () => {
  it("renders signup form with email and password fields", () => {
    render(<SignupPage />);
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sign Up" })).toBeInTheDocument();
  });

  it("Google signup button is disabled when terms not accepted", () => {
    render(<SignupPage />);
    const googleBtn = screen.getByText("Continue with Google").closest("button")!;
    expect(googleBtn).toBeDisabled();
  });

  it("Google signup button is enabled when terms accepted", async () => {
    const user = userEvent.setup();
    render(<SignupPage />);
    const checkbox = screen.getByRole("checkbox");
    await user.click(checkbox);
    const googleBtn = screen.getByText("Continue with Google").closest("button")!;
    expect(googleBtn).not.toBeDisabled();
  });

  it("shows error on failed signup", async () => {
    const user = userEvent.setup();
    mockSignup.mockRejectedValue(new Error("Something went wrong"));
    render(<SignupPage />);

    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Password"), "password123");
    await user.click(screen.getByRole("checkbox"));
    await user.click(screen.getByRole("button", { name: "Sign Up" }));

    await waitFor(() => {
      expect(screen.getByText("Something went wrong. Please try again.")).toBeInTheDocument();
    });
  });

  it("shows invitation error for allowlist rejection", async () => {
    const user = userEvent.setup();
    mockSignup.mockRejectedValue(new Error("User not on allow list"));
    render(<SignupPage />);

    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Password"), "password123");
    await user.click(screen.getByRole("checkbox"));
    await user.click(screen.getByRole("button", { name: "Sign Up" }));

    await waitFor(() => {
      expect(screen.getByText("You must be invited in order to sign up.")).toBeInTheDocument();
    });
  });

  it("redirects on successful signup", async () => {
    const user = userEvent.setup();
    mockSignup.mockResolvedValue(undefined);
    render(<SignupPage />);

    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Password"), "password123");
    await user.click(screen.getByRole("checkbox"));
    await user.click(screen.getByRole("button", { name: "Sign Up" }));

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/dashboard");
    });
  });
});
