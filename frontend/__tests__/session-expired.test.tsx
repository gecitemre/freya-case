import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React, { act } from "react";

import Home from "../app/page";

jest.mock("@pipecat-ai/client-js", () => ({
  PipecatClient: jest.fn().mockImplementation(() => ({
    connect: jest.fn(),
    disconnect: jest.fn(),
  })),
}));

jest.mock("@pipecat-ai/daily-transport", () => ({
  DailyTransport: jest.fn(),
}));

const renderWithClient = (ui: React.ReactElement) => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
};

describe("session expiry handling", () => {
  afterEach(() => {
    (global.fetch as jest.Mock).mockReset();
  });

  it("shows session expired message on 404 state", async () => {
    global.fetch = jest.fn().mockImplementation((url: string, options?: RequestInit) => {
      if (options?.method === "POST") {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ session_id: "s1", room_url: "room", token: "token" }),
        });
      }
      if (url.includes("/state")) {
        return Promise.resolve({
          ok: false,
          status: 404,
          json: async () => ({}),
        });
      }
      return Promise.resolve({
        ok: false,
        status: 500,
        json: async () => ({}),
      });
    });

    renderWithClient(<Home />);
    const user = userEvent.setup();

    await act(async () => {
      await user.click(screen.getByRole("button", { name: /start session/i }));
    });

    await waitFor(() => {
      expect(
        screen.getByText(/session expired — click start session again\./i)
      ).toBeInTheDocument();
    }, { timeout: 3000 });
  });
});
