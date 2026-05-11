from bs4 import BeautifulSoup

from app.parsers.vk_html import VKHTMLParser


def test_parser_extracts_messages_and_attachments(archive_root) -> None:
    parser = VKHTMLParser()

    parsed = parser.parse_file(archive_root / "303/messages50.html")

    assert parsed.user_id == 303
    assert parsed.display_name
    assert parsed.owner_user_id == 42
    assert parsed.messages
    assert any(message.direction == "inbound" for message in parsed.messages)
    assert any(message.direction == "outbound" for message in parsed.messages)
    assert any(message.has_attachments for message in parsed.messages)
    assert any(
        "https://" in message.text
        for message in parsed.messages
        if message.has_attachments
    )


def test_parser_supports_single_digit_hour_in_header(archive_root) -> None:
    parser = VKHTMLParser()

    parsed = parser.parse_file(archive_root / "-101/messages0.html")

    assert parsed.user_id == -101
    assert parsed.display_name
    assert len(parsed.messages) == 3
    assert any(message.timestamp.hour == 0 for message in parsed.messages)


def test_parser_supports_edited_message_marker_in_header(archive_root) -> None:
    parser = VKHTMLParser()

    parsed = parser.parse_file(archive_root / "202/messages2650.html")

    assert parsed.user_id == 202
    assert parsed.display_name
    assert parsed.messages
    assert any(
        message.timestamp.isoformat() == "2020-09-01T16:28:26+00:00"
        for message in parsed.messages
    )


def test_parser_supports_space_before_comma_in_edited_header() -> None:
    parser = VKHTMLParser()
    header = BeautifulSoup(
        """
        <div class="message__header">
          <a href="https://vk.com/id294036277">Вадим Зизов</a>, 1 сен 2020 в 16:28:26
          <span class="message-edited" title="1 сен 2020 в 16:29:01"> (корр.)</span>
        </div>
        """,
        "html.parser",
    ).select_one(".message__header")

    assert header is not None
    assert (
        header.get_text(" ", strip=True)
        == "Вадим Зизов , 1 сен 2020 в 16:28:26 (корр.)"
    )

    timestamp, direction = parser._parse_header(header)

    assert timestamp.isoformat() == "2020-09-01T16:28:26+00:00"
    assert direction == "inbound"
