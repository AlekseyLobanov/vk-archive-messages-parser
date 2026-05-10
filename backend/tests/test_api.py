def test_get_conversations_empty(client) -> None:
    response = client.get("/api/v1/conversations")

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] == []
    assert payload["total"] == 0


def test_serves_built_frontend(client) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<!doctype html>" in response.text.lower()

    spa_route = client.get("/conversations/4043901")
    assert spa_route.status_code == 200
    assert "text/html" in spa_route.headers["content-type"]


def test_import_search_messages_and_export(client) -> None:
    import_response = client.post("/api/v1/add", json={"path": "messages"})
    body = import_response.text

    assert import_response.status_code == 200
    assert '"imported":' in body
    assert '"skipped":' in body
    assert "event: done" in body

    conversations = client.get("/api/v1/conversations")
    assert conversations.status_code == 200
    conversation_payload = conversations.json()
    assert conversation_payload["total"] == 3

    search_response = client.post(
        "/api/v1/search",
        json={"query": "github", "mode": "simple", "user_id": 4043901},
    )
    assert search_response.status_code == 200
    search_payload = search_response.json()
    assert search_payload["total"] >= 1

    user_id = 4043901
    messages_response = client.get(
        f"/api/v1/messages/{user_id}",
        params={"around": search_payload["items"][0]["timestamp"], "limit": 2},
    )
    assert messages_response.status_code == 200
    messages_payload = messages_response.json()
    assert messages_payload["context"]["mode"] == "around"
    assert messages_payload["items"]

    export_response = client.post(
        "/api/v1/export",
        json={"format": "jsonl", "user_id": user_id, "limit": 5},
    )
    assert export_response.status_code == 200
    assert export_response.headers["content-disposition"].endswith('messages.jsonl"')
