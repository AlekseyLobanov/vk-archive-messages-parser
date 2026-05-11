import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Link,
  useLocation,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router-dom";
import { ApiError, fetchConversations, fetchMessages } from "../lib/api";
import type {
  Conversation,
  Message,
  MessagesResponse,
  SortField,
  SortOrder,
} from "../lib/types";
import { formatDateTime, mergeMessages } from "../lib/utils";

const PAGE_SIZE = 50;
const MAX_RENDERED_MESSAGES = 200;
const AUTOLOAD_THRESHOLD_PX = 120;
const TIMELINE_SCALE_MAX = 1000;

export function ConversationsPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { userId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [total, setTotal] = useState(0);
  const [selectedUserId, setSelectedUserId] = useState<number | null>(
    userId ? Number(userId) : null,
  );
  const [messages, setMessages] = useState<Message[]>([]);
  const [paging, setPaging] = useState<MessagesResponse["paging"] | null>(null);
  const [highlightedTimestamp, setHighlightedTimestamp] = useState<string | null>(
    null,
  );
  const [currentAnchorTimestamp, setCurrentAnchorTimestamp] = useState<string | null>(
    null,
  );
  const [jumpDateTime, setJumpDateTime] = useState("");
  const [sliderValue, setSliderValue] = useState<number | null>(null);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [loadingOlder, setLoadingOlder] = useState(false);
  const [loadingNewer, setLoadingNewer] = useState(false);
  const [jumping, setJumping] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const timelineRef = useRef<HTMLDivElement | null>(null);
  const topSentinelRef = useRef<HTMLDivElement | null>(null);
  const scrollRestoreRef = useRef<{
    mode: "prepend" | "append" | "reset" | "center";
    previousHeight: number;
    previousTop: number;
  } | null>(null);

  const sort = (searchParams.get("sort") as SortField | null) ?? "last_message_at";
  const order = (searchParams.get("order") as SortOrder | null) ?? "desc";
  const around = searchParams.get("around") ?? undefined;

  useEffect(() => {
    const run = async () => {
      setLoadingList(true);
      setError(null);

      try {
        const response = await fetchConversations({
          sort,
          order,
          limit: PAGE_SIZE,
          offset: 0,
        });

        setConversations(response.items);
        setTotal(response.total);

        if (response.items.length === 0) {
          navigate("/import", { replace: true });
          return;
        }

        const nextSelected = userId
          ? Number(userId)
          : response.items[0]?.user_id ?? null;

        setSelectedUserId(nextSelected);

        if (!userId && nextSelected !== null) {
          navigate(`/conversations/${nextSelected}`, { replace: true });
        }
      } catch (caughtError) {
        setError(toErrorMessage(caughtError));
      } finally {
        setLoadingList(false);
      }
    };

    void run();
  }, [navigate, order, sort, userId]);

  useEffect(() => {
    if (userId) {
      setSelectedUserId(Number(userId));
    }
  }, [userId]);

  useEffect(() => {
    if (!selectedUserId) {
      return;
    }

    const run = async () => {
      setLoadingMessages(true);
      setError(null);

      try {
        const response = await fetchMessages({
          userId: selectedUserId,
          limit: PAGE_SIZE,
          around,
        });

        scrollRestoreRef.current = {
          mode: around ? "center" : "reset",
          previousHeight: 0,
          previousTop: 0,
        };
        setMessages(limitMessagesWindow(response.items, "replace"));
        setPaging(response.paging);
        setHighlightedTimestamp(response.context?.highlighted_timestamp ?? null);
        const anchorTimestamp = getAnchorTimestamp(response);
        setCurrentAnchorTimestamp(anchorTimestamp);
        setJumpDateTime(toDateTimeLocalValue(anchorTimestamp));
      } catch (caughtError) {
        setError(toErrorMessage(caughtError));
      } finally {
        setLoadingMessages(false);
      }
    };

    void run();
  }, [around, selectedUserId]);

  useEffect(() => {
    setSliderValue(null);
  }, [selectedUserId]);

  const loadOlderMessages = useCallback(async () => {
    if (!selectedUserId || !paging?.next_before || loadingOlder) {
      return;
    }

    const timeline = timelineRef.current;
    scrollRestoreRef.current = {
      mode: "prepend",
      previousHeight: timeline?.scrollHeight ?? 0,
      previousTop: timeline?.scrollTop ?? 0,
    };
    setLoadingOlder(true);
    try {
      const response = await fetchMessages({
        userId: selectedUserId,
        limit: PAGE_SIZE,
        before: paging.next_before,
      });
      setMessages((current) =>
        limitMessagesWindow(mergeMessages(current, response.items, "prepend"), "prepend"),
      );
      setPaging(response.paging);
    } catch (caughtError) {
      setError(toErrorMessage(caughtError));
    } finally {
      setLoadingOlder(false);
    }
  }, [loadingOlder, paging?.next_before, selectedUserId]);

  const loadNewerMessages = useCallback(async () => {
    if (!selectedUserId || !paging?.next_after || loadingNewer) {
      return;
    }

    const timeline = timelineRef.current;
    scrollRestoreRef.current = {
      mode: "append",
      previousHeight: timeline?.scrollHeight ?? 0,
      previousTop: timeline?.scrollTop ?? 0,
    };
    setLoadingNewer(true);
    try {
      const response = await fetchMessages({
        userId: selectedUserId,
        limit: PAGE_SIZE,
        after: paging.next_after,
      });
      setMessages((current) =>
        limitMessagesWindow(mergeMessages(current, response.items, "append"), "append"),
      );
      setPaging(response.paging);
    } catch (caughtError) {
      setError(toErrorMessage(caughtError));
    } finally {
      setLoadingNewer(false);
    }
  }, [loadingNewer, paging?.next_after, selectedUserId]);

  useEffect(() => {
    if (!topSentinelRef.current || !timelineRef.current || !paging?.has_older || !selectedUserId) {
      return;
    }

    const observer = new IntersectionObserver((entries) => {
      const target = entries[0];
      if (target?.isIntersecting && !loadingOlder) {
        void loadOlderMessages();
      }
    }, {
      root: timelineRef.current,
      rootMargin: `${AUTOLOAD_THRESHOLD_PX}px 0px 0px 0px`,
    });

    observer.observe(topSentinelRef.current);
    return () => observer.disconnect();
  }, [loadOlderMessages, loadingOlder, paging?.has_older, selectedUserId]);

  useEffect(() => {
    const timeline = timelineRef.current;
    const restore = scrollRestoreRef.current;
    if (!timeline || !restore) {
      return;
    }

    if (restore.mode === "prepend") {
      const heightDiff = timeline.scrollHeight - restore.previousHeight;
      timeline.scrollTop = restore.previousTop + Math.max(heightDiff, 0);
    } else if (restore.mode === "append") {
      timeline.scrollTop = restore.previousTop;
    } else if (restore.mode === "center") {
      timeline.scrollTop = Math.max((timeline.scrollHeight - timeline.clientHeight) / 2, 0);
    } else {
      timeline.scrollTop = timeline.scrollHeight;
    }

    scrollRestoreRef.current = null;
  }, [messages]);

  const selectedConversation = useMemo(
    () => conversations.find((item) => item.user_id === selectedUserId) ?? null,
    [conversations, selectedUserId],
  );
  const selectedConversationName = useMemo(() => {
    if (selectedConversation) {
      return selectedConversation.display_name;
    }

    const routeState = location.state;
    if (
      routeState &&
      typeof routeState === "object" &&
      "userId" in routeState &&
      "displayName" in routeState &&
      routeState.userId === selectedUserId &&
      typeof routeState.displayName === "string" &&
      selectedUserId !== null
    ) {
      return routeState.displayName;
    }

    return null;
  }, [location.state, selectedConversation, selectedUserId]);
  const sliderPosition = useMemo(() => {
    if (!selectedConversation?.first_message_at || !selectedConversation.last_message_at) {
      return 0;
    }

    return timestampToSliderValue(
      sliderValue !== null
        ? sliderValueToTimestamp(
            sliderValue,
            selectedConversation.first_message_at,
            selectedConversation.last_message_at,
          )
        : currentAnchorTimestamp ?? selectedConversation.last_message_at,
      selectedConversation.first_message_at,
      selectedConversation.last_message_at,
    );
  }, [currentAnchorTimestamp, selectedConversation, sliderValue]);
  const sliderPreviewTimestamp = useMemo(() => {
    if (
      sliderValue === null ||
      !selectedConversation?.first_message_at ||
      !selectedConversation.last_message_at
    ) {
      return null;
    }

    return sliderValueToTimestamp(
      sliderValue,
      selectedConversation.first_message_at,
      selectedConversation.last_message_at,
    );
  }, [selectedConversation, sliderValue]);

  function updateSort(field: SortField) {
    const next = new URLSearchParams(searchParams);
    next.set("sort", field);
    next.set("order", order);
    setSearchParams(next);
  }

  function updateOrder(nextOrder: SortOrder) {
    const next = new URLSearchParams(searchParams);
    next.set("sort", sort);
    next.set("order", nextOrder);
    setSearchParams(next);
  }

  const jumpToTimestamp = useCallback(
    async (timestamp: string) => {
      if (!selectedUserId) {
        return;
      }

      setJumping(true);
      setError(null);

      try {
        const response = await fetchMessages({
          userId: selectedUserId,
          limit: PAGE_SIZE,
          around: timestamp,
        });

        scrollRestoreRef.current = {
          mode: "center",
          previousHeight: 0,
          previousTop: 0,
        };
        setMessages(limitMessagesWindow(response.items, "replace"));
        setPaging(response.paging);
        setHighlightedTimestamp(response.context?.highlighted_timestamp ?? null);
        const anchorTimestamp = getAnchorTimestamp(response);
        setCurrentAnchorTimestamp(anchorTimestamp);
        setJumpDateTime(toDateTimeLocalValue(anchorTimestamp));
        setSliderValue(null);
      } catch (caughtError) {
        setError(toErrorMessage(caughtError));
      } finally {
        setJumping(false);
      }
    },
    [selectedUserId],
  );

  async function shiftAnchor(days: number, years = 0) {
    if (!currentAnchorTimestamp) {
      return;
    }

    await jumpToTimestamp(shiftTimestamp(currentAnchorTimestamp, days, years));
  }

  async function handleJumpToDate() {
    if (!jumpDateTime) {
      return;
    }

    await jumpToTimestamp(new Date(jumpDateTime).toISOString());
  }

  async function commitSliderPosition() {
    if (
      sliderValue === null ||
      !selectedConversation?.first_message_at ||
      !selectedConversation.last_message_at
    ) {
      return;
    }

    await jumpToTimestamp(
      sliderValueToTimestamp(
        sliderValue,
        selectedConversation.first_message_at,
        selectedConversation.last_message_at,
      ),
    );
  }

  return (
    <section className="panel-grid">
      <aside className="panel">
        <div className="panel-header">
          <div>
            <h2>Переписки</h2>
            <p className="muted">{total} диалогов</p>
          </div>
          <Link className="ghost-link" to="/import">
            Импортировать
          </Link>
        </div>

        <div className="controls-row">
          <label className="field">
            Сортировка
            <select
              value={sort}
              onChange={(event) => updateSort(event.target.value as SortField)}
            >
              <option value="last_message_at">По последнему сообщению</option>
              <option value="message_count">По числу сообщений</option>
            </select>
          </label>
          <label className="field">
            Порядок
            <select
              value={order}
              onChange={(event) => updateOrder(event.target.value as SortOrder)}
            >
              <option value="desc">По убыванию</option>
              <option value="asc">По возрастанию</option>
            </select>
          </label>
        </div>

        {loadingList ? <p className="status-card">Загружаю список переписок…</p> : null}
        {error ? <p className="status-card error">{error}</p> : null}

        <div className="conversation-list">
          {conversations.map((conversation) => (
            <Link
              key={conversation.user_id}
              className={
                conversation.user_id === selectedUserId
                  ? "conversation-card active"
                  : "conversation-card"
              }
              to={`/conversations/${conversation.user_id}?sort=${sort}&order=${order}`}
            >
              <div className="conversation-card__top">
                <strong>{conversation.display_name}</strong>
                <span>{conversation.message_count} сообщений</span>
              </div>
              <div className="conversation-card__meta">
                <span>ID: {conversation.user_id}</span>
                <span>{formatDateTime(conversation.last_message_at)}</span>
              </div>
            </Link>
          ))}
        </div>
      </aside>

      <section className="panel timeline-panel">
        <div className="panel-header">
          <div>
            <h2>{selectedConversationName ?? "Выберите переписку"}</h2>
            <p className="muted">
              {selectedConversation
                ? `Начало переписки: ${formatDateTime(selectedConversation.first_message_at)}`
                : selectedUserId
                  ? `Диалог User ID ${selectedUserId}`
                  : "Откройте диалог слева"}
            </p>
          </div>
          {paging?.has_newer ? (
            <button
              type="button"
              className="secondary-button"
              onClick={() => void loadNewerMessages()}
            >
              Новее
            </button>
          ) : null}
        </div>

        {!selectedUserId ? (
          <p className="status-card">Выберите переписку.</p>
        ) : null}

        {selectedUserId && loadingMessages && messages.length === 0 ? (
          <p className="status-card">Загружаю сообщения…</p>
        ) : null}

        <div className="timeline-toolbar">
          <div className="muted">
            На экране показана часть сообщений. Остальные можно загрузить
            кнопками выше и ниже.
          </div>
          <div className="timeline-toolbar__actions">
            <button
              type="button"
              className="secondary-button"
              onClick={() => void loadOlderMessages()}
              disabled={!paging?.has_older || loadingOlder}
            >
              {loadingOlder ? "Загружаю старые…" : "Старее"}
            </button>
            <button
              type="button"
              className="secondary-button"
              onClick={() => void loadNewerMessages()}
              disabled={!paging?.has_newer || loadingNewer}
            >
              {loadingNewer ? "Загружаю новые…" : "Новее"}
            </button>
          </div>
        </div>

        <div className="timeline-jump panel panel--inner">
          <div className="timeline-jump__row">
            <label className="field">
              Перейти к дате
              <input
                type="datetime-local"
                value={jumpDateTime}
                onChange={(event) => setJumpDateTime(event.target.value)}
              />
            </label>
            <div className="timeline-jump__actions">
              <button
                type="button"
                className="secondary-button"
                onClick={() => void handleJumpToDate()}
                disabled={!selectedUserId || !jumpDateTime || jumping}
              >
                {jumping ? "Перехожу…" : "Перейти"}
              </button>
              <button
                type="button"
                className="secondary-button"
                onClick={() => void shiftAnchor(-30)}
                disabled={!currentAnchorTimestamp || jumping}
              >
                -30 дн.
              </button>
              <button
                type="button"
                className="secondary-button"
                onClick={() => void shiftAnchor(30)}
                disabled={!currentAnchorTimestamp || jumping}
              >
                +30 дн.
              </button>
              <button
                type="button"
                className="secondary-button"
                onClick={() => void shiftAnchor(0, -1)}
                disabled={!currentAnchorTimestamp || jumping}
              >
                -1 год
              </button>
              <button
                type="button"
                className="secondary-button"
                onClick={() => void shiftAnchor(0, 1)}
                disabled={!currentAnchorTimestamp || jumping}
              >
                +1 год
              </button>
            </div>
          </div>

          <div className="timeline-slider">
            <div className="timeline-slider__meta">
              <span>{formatDateTime(selectedConversation?.first_message_at ?? null)}</span>
              <strong>
                {formatDateTime(sliderPreviewTimestamp ?? currentAnchorTimestamp)}
              </strong>
              <span>{formatDateTime(selectedConversation?.last_message_at ?? null)}</span>
            </div>
            <input
              type="range"
              min={0}
              max={TIMELINE_SCALE_MAX}
              step={1}
              value={sliderPosition}
              disabled={
                !selectedConversation?.first_message_at ||
                !selectedConversation.last_message_at ||
                jumping
              }
              onChange={(event) => setSliderValue(Number(event.target.value))}
              onMouseUp={() => void commitSliderPosition()}
              onTouchEnd={() => void commitSliderPosition()}
              onKeyUp={(event) => {
                if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
                  void commitSliderPosition();
                }
              }}
            />
          </div>
        </div>

        <div ref={timelineRef} className="timeline-scroller">
          <div ref={topSentinelRef} className="sentinel" />
          <div className="timeline-status">
            {paging?.has_older
              ? "Прокрутите вверх, чтобы загрузить предыдущие сообщения"
              : "Это начало переписки"}
          </div>

          <div className="timeline">
          {messages.map((message) => (
            <article
              key={`${message.user_id}:${message.timestamp}`}
              className={
                highlightedTimestamp === message.timestamp
                  ? `message-bubble ${message.direction} highlighted`
                  : `message-bubble ${message.direction}`
              }
            >
              <div className="message-meta">
                <span>{message.direction === "outbound" ? "Вы" : "Собеседник"}</span>
                <time dateTime={message.timestamp}>
                  {formatDateTime(message.timestamp)}
                </time>
              </div>
              <p>{message.text}</p>
              {message.has_attachments ? (
                <span className="attachment-flag">С вложениями</span>
              ) : null}
            </article>
          ))}
          </div>

          <div className="timeline-status timeline-status--bottom">
            {paging?.has_newer
              ? "Есть более новые сообщения"
              : "Это конец переписки"}
          </div>
        </div>
      </section>
    </section>
  );
}

function limitMessagesWindow(
  messages: Message[],
  mode: "replace" | "prepend" | "append",
): Message[] {
  if (messages.length <= MAX_RENDERED_MESSAGES) {
    return messages;
  }

  if (mode === "prepend") {
    return messages.slice(0, MAX_RENDERED_MESSAGES);
  }

  if (mode === "append") {
    return messages.slice(-MAX_RENDERED_MESSAGES);
  }

  return messages.slice(-MAX_RENDERED_MESSAGES);
}

function getAnchorTimestamp(response: MessagesResponse): string | null {
  return (
    response.context?.anchor_timestamp ??
    response.context?.highlighted_timestamp ??
    response.items[Math.floor(response.items.length / 2)]?.timestamp ??
    response.items.at(-1)?.timestamp ??
    null
  );
}

function shiftTimestamp(
  value: string,
  daysDelta: number,
  yearsDelta: number,
): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  if (daysDelta !== 0) {
    date.setUTCDate(date.getUTCDate() + daysDelta);
  }
  if (yearsDelta !== 0) {
    date.setUTCFullYear(date.getUTCFullYear() + yearsDelta);
  }

  return date.toISOString();
}

function toDateTimeLocalValue(value: string | null): string {
  if (!value) {
    return "";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }

  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

function timestampToSliderValue(
  timestamp: string,
  firstTimestamp: string,
  lastTimestamp: string,
): number {
  const current = new Date(timestamp).getTime();
  const first = new Date(firstTimestamp).getTime();
  const last = new Date(lastTimestamp).getTime();

  if (!Number.isFinite(current) || !Number.isFinite(first) || !Number.isFinite(last)) {
    return TIMELINE_SCALE_MAX;
  }

  if (last <= first) {
    return TIMELINE_SCALE_MAX;
  }

  return Math.round(((current - first) / (last - first)) * TIMELINE_SCALE_MAX);
}

function sliderValueToTimestamp(
  value: number,
  firstTimestamp: string,
  lastTimestamp: string,
): string {
  const first = new Date(firstTimestamp).getTime();
  const last = new Date(lastTimestamp).getTime();

  if (!Number.isFinite(first) || !Number.isFinite(last) || last <= first) {
    return lastTimestamp;
  }

  const ratio = value / TIMELINE_SCALE_MAX;
  return new Date(first + (last - first) * ratio).toISOString();
}

function toErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return `Ошибка API: ${error.message}`;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Неизвестная ошибка";
}
