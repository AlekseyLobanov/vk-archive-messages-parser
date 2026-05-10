import type { FormEvent } from "react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { ApiError, searchMessages } from "../lib/api";
import type { SearchMode, SearchResultItem } from "../lib/types";
import { formatDateTime, highlightText, toIsoOrUndefined } from "../lib/utils";

export function SearchPage() {
  const [query, setQuery] = useState("");
  const [userId, setUserId] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [mode, setMode] = useState<SearchMode>("simple");
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await searchMessages({
        query,
        mode,
        user_id: userId ? Number(userId) : undefined,
        date_from: toIsoOrUndefined(dateFrom),
        date_to: toIsoOrUndefined(dateTo),
        limit: 50,
        offset: 0,
      });

      setResults(response.items);
      setTotal(response.total);
    } catch (caughtError) {
      setError(toErrorMessage(caughtError));
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="stack">
      <div className="panel">
        <div className="panel-header">
          <div>
            <h2>Поиск по сообщениям</h2>
            <p className="muted">
              Ищите по всем перепискам или ограничивайте поиск одним user ID.
            </p>
          </div>
          <span className={mode === "fts" ? "mode-badge advanced" : "mode-badge"}>
            {mode === "fts" ? "Расширенный FTS режим" : "Обычный поиск"}
          </span>
        </div>

        <form className="form-grid" onSubmit={(event) => void handleSubmit(event)}>
          <label className="field field-wide">
            Запрос
            <input
              required
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder={mode === "fts" ? "phrase OR word*" : "например, сумерки"}
            />
          </label>

          <label className="field">
            Режим поиска
            <select
              value={mode}
              onChange={(event) => setMode(event.target.value as SearchMode)}
            >
              <option value="simple">simple</option>
              <option value="fts">fts</option>
            </select>
          </label>

          <label className="field">
            User ID
            <input
              inputMode="numeric"
              value={userId}
              onChange={(event) => setUserId(event.target.value)}
              placeholder="Все переписки"
            />
          </label>

          <label className="field">
            Дата от
            <input
              type="datetime-local"
              value={dateFrom}
              onChange={(event) => setDateFrom(event.target.value)}
            />
          </label>

          <label className="field">
            Дата до
            <input
              type="datetime-local"
              value={dateTo}
              onChange={(event) => setDateTo(event.target.value)}
            />
          </label>

          <div className="field field-actions">
            <button type="submit" className="primary-button" disabled={loading}>
              {loading ? "Ищу…" : "Найти"}
            </button>
          </div>
        </form>

        {mode === "fts" ? (
          <p className="status-card warning">
            Включен расширенный режим: запрос уйдёт в backend как ручное
            FTS-выражение.
          </p>
        ) : null}
        {error ? <p className="status-card error">{error}</p> : null}
      </div>

      <div className="panel">
        <div className="panel-header">
          <div>
            <h2>Результаты</h2>
            <p className="muted">{total} совпадений</p>
          </div>
        </div>

        <div className="results-list">
          {results.map((item) => (
            <article key={`${item.user_id}:${item.timestamp}`} className="result-card">
              <div className="result-card__top">
                <strong>{item.display_name}</strong>
                <span>{item.direction === "outbound" ? "Исходящее" : "Входящее"}</span>
              </div>
              <time dateTime={item.timestamp}>{formatDateTime(item.timestamp)}</time>
              <p>
                {highlightText(item.text, mode === "simple" ? query : "").map(
                  (part, index) =>
                    part.toLowerCase() === query.trim().toLowerCase() ? (
                      <mark key={`${part}-${index}`}>{part}</mark>
                    ) : (
                      <span key={`${part}-${index}`}>{part}</span>
                    ),
                )}
              </p>
              <Link
                className="ghost-link"
                to={`/conversations/${item.user_id}?around=${encodeURIComponent(item.timestamp)}`}
                state={{ userId: item.user_id, displayName: item.display_name }}
              >
                Открыть контекст сообщения
              </Link>
            </article>
          ))}
          {!loading && results.length === 0 ? (
            <p className="status-card">Пока ничего не найдено.</p>
          ) : null}
        </div>
      </div>
    </section>
  );
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
