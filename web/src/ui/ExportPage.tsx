import type { FormEvent } from "react";
import { useState } from "react";
import { ApiError, exportMessages } from "../lib/api";
import type { ExportFormat } from "../lib/types";
import { toIsoOrUndefined } from "../lib/utils";

export function ExportPage() {
  const [format, setFormat] = useState<ExportFormat>("jsonl");
  const [userId, setUserId] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [limit, setLimit] = useState("1000");
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setStatus(null);
    setError(null);

    try {
      const { blob, filename } = await exportMessages({
        format,
        user_id: userId ? Number(userId) : undefined,
        date_from: toIsoOrUndefined(dateFrom),
        date_to: toIsoOrUndefined(dateTo),
        limit: limit ? Number(limit) : undefined,
      });

      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = filename;
      link.click();
      URL.revokeObjectURL(objectUrl);
      setStatus(`Файл ${filename} подготовлен.`);
    } catch (caughtError) {
      setError(toErrorMessage(caughtError));
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="panel stack">
      <div className="panel-header">
        <div>
          <h2>Экспорт сообщений</h2>
          <p className="muted">
            Можно выгрузить весь архив или ограничиться одним диалогом и
            диапазоном дат.
          </p>
        </div>
      </div>

      <form className="form-grid" onSubmit={(event) => void handleSubmit(event)}>
        <label className="field">
          Формат
          <select
            value={format}
            onChange={(event) => setFormat(event.target.value as ExportFormat)}
          >
            <option value="txt">txt</option>
            <option value="json">json</option>
            <option value="jsonl">jsonl</option>
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

        <label className="field">
          Лимит
          <input
            inputMode="numeric"
            value={limit}
            onChange={(event) => setLimit(event.target.value)}
          />
        </label>

        <div className="field field-actions">
          <button type="submit" className="primary-button" disabled={loading}>
            {loading ? "Готовлю…" : "Экспортировать"}
          </button>
        </div>
      </form>

      {status ? <p className="status-card success">{status}</p> : null}
      {error ? <p className="status-card error">{error}</p> : null}
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
