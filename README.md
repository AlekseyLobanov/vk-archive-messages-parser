# VK Archive Message Parser

Локальное офлайн-приложение для архива сообщений VK.
Получить архив можно стандартным [экспортом VK](https://vk.com/faq18145?n=1&q=%D0%B0%D1%80%D1%85%D0%B8%D0%B2).

Что это:
- открывает архив сообщений VK в браузере локально, без облака и внешних сервисов;
- импортирует сообщения в SQLite и показывает их по перепискам;
- умеет искать по сообщениям и экспортировать выборку в `txt`, `json`, `jsonl`.

![Скриншот интерфейса](docs/screen.png)


**Что умеет**
- Импортировать архив сообщений VK из локальной директории
- Конвертирует и хранит в sqlite
- Полноценный **поиск текста** по всей базе через FTS5, включая обычный и расширенный FTS-поиск
- Web UI для очень быстрого просмотра переписок
- Экспорт сообщений в `txt`, `json`, `jsonl`

**Что нужно для запуска**
- `uv`
- Python `3.12+`
- `make`

`uv` можно установить по официальной инструкции Astral:
- https://docs.astral.sh/uv/getting-started/installation/

Если Python уже установлен локально, `uv` обычно использует его. Если нет, `uv` умеет ставить Python сам.


**Запуск:**

```bash
cp config.example.toml config.toml
make backend ARGS="--config config.toml"
```

После запуска Web доступен по адресу `http://127.0.0.1:8001` или адресу из конфига.

**Фронтенд** уже собран, но для повторной сборки можно использовать команду
```bash
make frontend-build
```

Подробная техническая спецификация:
- [docs/tech.md](docs/tech.md)

**Импорт сообщений**
1. Открыть приложение.
2. Если переписок ещё нет, UI сразу предложит импорт.
3.
1. Указать путь к корню архива сообщений VK, например `./messages`.
2. Дождаться завершения импорта.

Во время импорта backend пишет структурированные логи:
- какие файлы обработаны;
- какие не обработаны;
- почему произошла ошибка, если она была.

**Конфиг**

Приложение читает TOML-конфиг только если путь передан явно:
- через `VK_ARCHIVE_CONFIG`
- через `--config some_file.toml`

Примеры:

```bash
VK_ARCHIVE_CONFIG=config.toml make backend
make backend ARGS="--config config.toml"
make demo-data ARGS="--config config.toml --reset"
```

Обычно локальный конфиг лежит в корне:
- `config.toml`
- пример: [config.example.toml](config.example.toml)

Ключевые настройки:

```toml
[database]
url = "sqlite:///data/vk_messages.db"

[logging]
level = "INFO"
path = "logs/backend.log"
max_bytes = 1048576
backup_count = 3

[server]
host = "127.0.0.1"
port = 8001
```

`logging.path` — путь к основному лог-файлу.

Ротация простая:
- `max_bytes` — максимальный размер одного файла до ротации;
- `backup_count` — сколько старых файлов хранить.

**Миграции**

Применить миграции вручную:

```bash
make migrate
```

Это запускает `alembic upgrade head`.

Обычно вручную это не нужно: backend сам делает `upgrade head` на старте.

**Проверки**

Тесты backend:

```bash
make test
```

Линтер backend:

```bash
make lint
```

Форматирование backend:

```bash
make format
```

Проверки перед публикацией:

```bash
make test
make pre-commit
```
