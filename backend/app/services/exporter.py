import json

from app.repositories.storage import MessageRepository
from app.schemas.api import ExportFormat, ExportRequest


def export_messages(
    repository: MessageRepository, request: ExportRequest
) -> tuple[str, str, str]:
    items = repository.export_messages(request)

    if request.format == ExportFormat.JSON:
        content = json.dumps(
            [item.model_dump(mode="json") for item in items],
            ensure_ascii=False,
            indent=2,
        )
        return content, "application/json", "messages.json"

    if request.format == ExportFormat.JSONL:
        lines = [
            json.dumps(item.model_dump(mode="json"), ensure_ascii=False)
            for item in items
        ]
        return "\n".join(lines), "application/jsonl", "messages.jsonl"

    lines = [
        (
            f"[{item.timestamp.isoformat()}] "
            f"{item.display_name} ({item.direction}): "
            f"{item.text}"
        )
        for item in items
    ]
    return "\n".join(lines), "text/plain; charset=utf-8", "messages.txt"
