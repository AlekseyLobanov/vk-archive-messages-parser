import type { FormEvent } from "react";
import { useMemo, useState } from "react";
import { ApiError, streamImport } from "../lib/api";
import type { ImportProgressEvent } from "../lib/types";

export function ImportPage() {
  const [path, setPath] = useState("./messages");
  const [progress, setProgress] = useState<ImportProgressEvent | null>(null);
  const [status, setStatus] = useState<"idle" | "running" | "done">("idle");
  const [error, setError] = useState<string | null>(null);

  const progressRatio = useMemo(() => {
    if (!progress || progress.total === 0) {
      return 0;
    }

    return Math.max(
      0,
      Math.min(100, ((progress.total - progress.remains) / progress.total) * 100),
    );
  }, [progress]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus("running");
    setProgress(null);
    setError(null);

    try {
      await streamImport(path, (eventName, data) => {
        setProgress(data);
        if (eventName === "done") {
          setStatus("done");
        }
      });
    } catch (caughtError) {
      setStatus("idle");
      setError(toErrorMessage(caughtError));
    }
  }

  return (
    <section className="stack">
      <div className="panel">
        <div className="panel-header">
          <div>
            <h2>Импорт архива</h2>
            <p className="muted">
              Укажите путь к корню архива. Backend обработает HTML-файлы и будет
              присылать прогресс по SSE.
            </p>
          </div>
        </div>

        <form className="import-form" onSubmit={(event) => void handleSubmit(event)}>
          <label className="field field-wide">
            Путь к архиву
            <input
              value={path}
              onChange={(event) => setPath(event.target.value)}
              placeholder="/path/to/messages"
            />
          </label>

          <button type="submit" className="primary-button" disabled={status === "running"}>
            {status === "running" ? "Импорт идет…" : "Запустить импорт"}
          </button>
        </form>
      </div>

      <div className="panel">
        <div className="panel-header">
          <div>
            <h2>Прогресс</h2>
            <p className="muted">Импорт считается по числу обработанных файлов.</p>
          </div>
        </div>

        <div className="progress-track" aria-hidden="true">
          <div className="progress-bar" style={{ width: `${progressRatio}%` }} />
        </div>

        <div className="stats-grid">
          <StatCard label="Всего файлов" value={progress?.total ?? 0} />
          <StatCard label="Осталось" value={progress?.remains ?? 0} />
          <StatCard label="Ошибок" value={progress?.errors ?? 0} />
          <StatCard label="Импортировано" value={progress?.imported ?? 0} />
          <StatCard label="Пропущено" value={progress?.skipped ?? 0} />
        </div>

        {status === "done" ? (
          <p className="status-card success">
            Импорт завершён. Можно перейти к перепискам и поиску.
          </p>
        ) : null}
        {error ? <p className="status-card error">{error}</p> : null}
      </div>
    </section>
  );
}

function StatCard(props: { label: string; value: number }) {
  return (
    <div className="stat-card">
      <span>{props.label}</span>
      <strong>{props.value}</strong>
    </div>
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
