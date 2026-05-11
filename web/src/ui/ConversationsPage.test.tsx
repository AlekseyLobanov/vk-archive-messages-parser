import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ConversationsPage } from "./ConversationsPage";

const apiMocks = vi.hoisted(() => ({
  fetchConversations: vi.fn(),
  fetchMessages: vi.fn(),
}));

vi.mock("../lib/api", () => ({
  ApiError: class extends Error {},
  fetchConversations: apiMocks.fetchConversations,
  fetchMessages: apiMocks.fetchMessages,
}));

function renderConversationsPage(initialEntry = "/conversations") {
  render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route path="/conversations" element={<ConversationsPage />} />
        <Route path="/conversations/:userId" element={<ConversationsPage />} />
        <Route path="/import" element={<h2>Импорт архива</h2>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("ConversationsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("redirects to import when there are no conversations", async () => {
    apiMocks.fetchConversations.mockResolvedValue({
      items: [],
      total: 0,
    });

    renderConversationsPage();

    expect(
      await screen.findByRole("heading", { name: "Импорт архива" }),
    ).toBeInTheDocument();
    expect(apiMocks.fetchMessages).not.toHaveBeenCalled();
  });

  it("selects the first conversation and loads its messages", async () => {
    apiMocks.fetchConversations.mockResolvedValue({
      items: [
        {
          user_id: 42,
          display_name: "Иван Петров",
          message_count: 2,
          first_message_at: "2024-01-01T10:00:00Z",
          last_message_at: "2024-01-02T12:00:00Z",
        },
      ],
      total: 1,
    });
    apiMocks.fetchMessages.mockResolvedValue({
      items: [
        {
          user_id: 42,
          timestamp: "2024-01-02T12:00:00Z",
          direction: "inbound",
          text: "Привет",
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
      context: null,
    });

    renderConversationsPage();

    expect(await screen.findByRole("heading", { name: "Иван Петров" })).toBeInTheDocument();
    expect(await screen.findByText("Привет")).toBeInTheDocument();

    await waitFor(() =>
      expect(apiMocks.fetchMessages).toHaveBeenCalledWith({
        userId: 42,
        limit: 50,
        around: undefined,
      }),
    );
  });

  it("loads older messages when the user clicks the older button", async () => {
    const user = userEvent.setup();

    apiMocks.fetchConversations.mockResolvedValue({
      items: [
        {
          user_id: 42,
          display_name: "Иван Петров",
          message_count: 3,
          first_message_at: "2024-01-01T09:00:00Z",
          last_message_at: "2024-01-03T12:00:00Z",
        },
      ],
      total: 1,
    });
    apiMocks.fetchMessages
      .mockResolvedValueOnce({
        items: [
          {
            user_id: 42,
            timestamp: "2024-01-02T10:00:00Z",
            direction: "inbound",
            text: "Второе сообщение",
            has_attachments: false,
          },
          {
            user_id: 42,
            timestamp: "2024-01-03T12:00:00Z",
            direction: "outbound",
            text: "Третье сообщение",
            has_attachments: false,
          },
        ],
        paging: {
          limit: 50,
          has_older: true,
          has_newer: false,
          next_before: "2024-01-02T10:00:00Z",
          next_after: null,
        },
        context: null,
      })
      .mockResolvedValueOnce({
        items: [
          {
            user_id: 42,
            timestamp: "2024-01-01T09:00:00Z",
            direction: "inbound",
            text: "Первое сообщение",
            has_attachments: false,
          },
        ],
        paging: {
          limit: 50,
          has_older: false,
          has_newer: true,
          next_before: null,
          next_after: "2024-01-02T10:00:00Z",
        },
        context: null,
      });

    renderConversationsPage();

    const olderButton = await screen.findByRole("button", { name: "Старее" });
    await user.click(olderButton);

    expect(await screen.findByText("Первое сообщение")).toBeInTheDocument();

    await waitFor(() =>
      expect(apiMocks.fetchMessages).toHaveBeenLastCalledWith({
        userId: 42,
        limit: 50,
        before: "2024-01-02T10:00:00Z",
      }),
    );
  });
});
