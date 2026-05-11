import { useEffect, useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import { ConversationsPage } from "./ConversationsPage";
import { ExportPage } from "./ExportPage";
import { ImportPage } from "./ImportPage";
import { SearchPage } from "./SearchPage";

const navItems = [
  { to: "/conversations", label: "Переписки" },
  { to: "/search", label: "Поиск" },
  { to: "/export", label: "Экспорт" },
  { to: "/import", label: "Импорт" },
];

export function App() {
  const [theme, setTheme] = useState<"dark" | "light">(() => {
    const savedTheme = window.localStorage.getItem("vk-theme");
    return savedTheme === "light" ? "light" : "dark";
  });

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem("vk-theme", theme);
  }, [theme]);

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <h1>Архив сообщений VK</h1>
          <p className="muted">Локальный просмотр архива сообщений VK</p>
        </div>
        <div className="topbar-actions">
          <nav className="topnav" aria-label="Основная навигация">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  isActive ? "topnav-link active" : "topnav-link"
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          <button
            type="button"
            className="theme-toggle"
            onClick={() => setTheme((current) => (current === "dark" ? "light" : "dark"))}
            aria-label="Переключить тему"
            title={theme === "dark" ? "Светлая тема" : "Тёмная тема"}
          >
            <span aria-hidden="true">{theme === "dark" ? "☀" : "☾"}</span>
          </button>
        </div>
      </header>

      <main className="page">
        <Routes>
          <Route path="/" element={<ConversationsPage />} />
          <Route path="/conversations" element={<ConversationsPage />} />
          <Route path="/conversations/:userId" element={<ConversationsPage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/export" element={<ExportPage />} />
          <Route path="/import" element={<ImportPage />} />
        </Routes>
      </main>

      <footer className="site-footer" aria-label="Информация о проекте">
        <p className="site-footer__copy">(c) Aleksey Lobanov</p>
        <a
          className="site-footer__link"
          href="https://github.com/AlekseyLobanov"
          target="_blank"
          rel="noreferrer"
          aria-label="GitHub Aleksey Lobanov"
        >
          GitHub
        </a>
      </footer>
    </div>
  );
}
