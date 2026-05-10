import base64
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from bs4 import BeautifulSoup, Tag

RUSSIAN_MONTHS = {
    "янв": 1,
    "фев": 2,
    "мар": 3,
    "апр": 4,
    "мая": 5,
    "май": 5,
    "июн": 6,
    "июл": 7,
    "авг": 8,
    "сен": 9,
    "окт": 10,
    "ноя": 11,
    "дек": 12,
}

HEADER_PATTERN = re.compile(
    r"^(?:(?P<author>.*?)\s*,\s*)?"
    r"(?P<day>\d{1,2})\s+(?P<month>[^\s]+)\s+(?P<year>\d{4})"
    r"\s+в\s+(?P<time>\d{1,2}:\d{2}:\d{2})(?:\s+\(корр\.\))?$"
)


@dataclass(slots=True)
class ParsedMessage:
    timestamp: datetime
    direction: str
    text: str
    has_attachments: bool


@dataclass(slots=True)
class ParsedConversationFile:
    user_id: int
    owner_user_id: int | None
    display_name: str
    messages: list[ParsedMessage]


class VKHTMLParser:
    def parse_file(self, path: Path) -> ParsedConversationFile:
        html = path.read_text(encoding="cp1251")
        soup = BeautifulSoup(html, "html.parser")
        user_id = int(path.parent.name)
        display_name = self._extract_display_name(soup)
        owner_user_id = self._extract_owner_user_id(soup)
        messages = [message for message in self._parse_messages(soup) if message.text]

        return ParsedConversationFile(
            user_id=user_id,
            owner_user_id=owner_user_id,
            display_name=display_name,
            messages=messages,
        )

    def _extract_display_name(self, soup: BeautifulSoup) -> str:
        crumbs = soup.select(".ui_crumb")
        if crumbs:
            return crumbs[-1].get_text(" ", strip=True)
        header_link = soup.select_one(".message__header a")
        if header_link:
            return header_link.get_text(" ", strip=True)
        return "Unknown"

    def _extract_owner_user_id(self, soup: BeautifulSoup) -> int | None:
        meta = soup.find("meta", attrs={"name": "jd"})
        if not meta or not meta.get("content"):
            return None
        payload = meta["content"]
        padding = "=" * (-len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload + padding).decode("utf-8")
        return json.loads(decoded).get("user_id")

    def _parse_messages(self, soup: BeautifulSoup) -> list[ParsedMessage]:
        parsed_messages: list[ParsedMessage] = []
        for node in soup.select(".message"):
            header = node.select_one(".message__header")
            if header is None:
                continue
            body = self._message_body(node)
            if body is None:
                continue

            timestamp, direction = self._parse_header(header)
            text, has_attachments = self._extract_text(body)
            parsed_messages.append(
                ParsedMessage(
                    timestamp=timestamp,
                    direction=direction,
                    text=text,
                    has_attachments=has_attachments,
                )
            )
        return parsed_messages

    def _message_body(self, message: Tag) -> Tag | None:
        direct_divs = [child for child in message.find_all("div", recursive=False)]
        if len(direct_divs) < 2:
            return None
        return direct_divs[1]

    def _parse_header(self, header: Tag) -> tuple[datetime, str]:
        header_text = header.get_text(" ", strip=True)
        match = HEADER_PATTERN.match(header_text)
        if not match:
            raise ValueError(f"Unsupported message header format: {header_text}")

        day = int(match.group("day"))
        month_token = match.group("month").lower()[:3]
        month = RUSSIAN_MONTHS.get(month_token) or RUSSIAN_MONTHS.get(
            match.group("month").lower()
        )
        if month is None:
            raise ValueError(f"Unsupported month token: {match.group('month')}")

        year = int(match.group("year"))
        time_value = datetime.strptime(match.group("time"), "%H:%M:%S").time()
        timestamp = datetime(
            year,
            month,
            day,
            time_value.hour,
            time_value.minute,
            time_value.second,
            tzinfo=UTC,
        )

        author = (match.group("author") or "").strip()
        direction = "outbound" if author == "Вы" or not header.find("a") else "inbound"
        return timestamp, direction

    def _extract_text(self, body: Tag) -> tuple[str, bool]:
        body_soup = BeautifulSoup(str(body), "html.parser")
        kludges = body_soup.select_one(".kludges")
        if kludges is not None:
            kludges.decompose()
        main_text = self._normalize_text(body_soup.get_text("\n", strip=True))

        attachment_lines: list[str] = []
        for attachment in body.select(".kludges .attachment"):
            description = self._normalize_text(
                attachment.select_one(".attachment__description").get_text(
                    " ", strip=True
                )
                if attachment.select_one(".attachment__description")
                else ""
            )
            link_node = attachment.select_one(".attachment__link")
            link = self._normalize_text(
                link_node.get_text(" ", strip=True) if link_node else ""
            )

            if description and link:
                attachment_lines.append(f"{description}: {link}")
            elif description:
                attachment_lines.append(description)
            elif link:
                attachment_lines.append(link)

        parts = [part for part in [main_text, *attachment_lines] if part]
        return "\n".join(parts).strip(), bool(attachment_lines)

    def _normalize_text(self, text: str) -> str:
        lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
        return "\n".join(line for line in lines if line)
