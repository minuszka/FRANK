from app.services.history_service import HistoryService


def test_history_append_and_clear() -> None:
    history = HistoryService(max_messages_per_session=3)
    history.append("s1", "user", "Hello")
    history.append("s1", "assistant", "Hi")

    entries = history.get("s1")
    assert len(entries) == 2
    assert entries[0].content == "Hello"

    removed = history.clear("s1")
    assert removed is True
    assert history.get("s1") == []

