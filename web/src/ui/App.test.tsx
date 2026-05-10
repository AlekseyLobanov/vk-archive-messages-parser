import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";

const apiMocks = vi.hoisted(() => ({
  exportMessages: vi.fn(),
  fetchConversations: vi.fn(),
  fetchMessages: vi.fn(),
  searchMessages: vi.fn(),
  streamImport: vi.fn(),
}));

vi.mock("../lib/api", () => ({
  ApiError: class extends Error {},
  exportMessages: apiMocks.exportMessages,
  fetchConversations: apiMocks.fetchConversations,
  fetchMessages: apiMocks.fetchMessages,
  searchMessages: apiMocks.searchMessages,
  streamImport: apiMocks.streamImport,
}));

describe("App", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.fetchConversations.mockResolvedValue({
      items: [],
      total: 0,
    });
  });

  it("renders top-level route navigation", () => {
    render(
      <MemoryRouter initialEntries={["/import"]}>
        <App />
      </MemoryRouter>,
    );

    expect(screen.getByRole("link", { name: "Переписки" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Поиск" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Экспорт" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Импорт" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Импорт архива" })).toBeInTheDocument();
  });

  it("keeps the interlocutor name when opening message context from search", async () => {
    const user = userEvent.setup();

    apiMocks.searchMessages.mockResolvedValue({
      items: [
        {
          user_id: 4043901,
          display_name: "Алексей Лобанов",
          timestamp: "2024-01-02T03:04:05Z",
          direction: "inbound",
          text: "github profile",
        },
      ],
      total: 1,
    });
    apiMocks.fetchConversations.mockResolvedValue({
      items: [
        {
          user_id: 1,
          display_name: "Другой собеседник",
          message_count: 3,
          first_message_at: "2024-01-01T00:00:00Z",
          last_message_at: "2024-01-03T00:00:00Z",
        },
      ],
      total: 51,
    });
    apiMocks.fetchMessages.mockResolvedValue({
      items: [
        {
          user_id: 4043901,
          timestamp: "2024-01-02T03:04:05Z",
          direction: "inbound",
          text: "github profile",
          has_attachments: false,
        },
      ],
      paging: {
        limit: 50,
        has_older: false,
        has_newer: false,
        next_before: null,
        next_after: null,
      },
      context: {
        mode: "around",
        anchor_timestamp: "2024-01-02T03:04:05Z",
        highlighted_timestamp: "2024-01-02T03:04:05Z",
      },
    });

    render(
      <MemoryRouter initialEntries={["/search"]}>
        <App />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText("Запрос"), {
      target: { value: "github" },
    });
    await user.click(screen.getByRole("button", { name: "Найти" }));

    await user.click(
      await screen.findByRole("link", { name: "Открыть контекст сообщения" }),
    );

    expect(
      await screen.findByRole("heading", { name: "Алексей Лобанов" }),
    ).toBeInTheDocument();

    await waitFor(() =>
      expect(apiMocks.fetchMessages).toHaveBeenCalledWith({
        userId: 4043901,
        limit: 50,
        around: "2024-01-02T03:04:05Z",
      }),
    );
  });
});
