import openai
from sqlalchemy import func, select

from app.models import ChatMessage, MealLog
from tests.conftest import register, text_reply, tool_reply


def test_plain_reply_is_returned_and_persisted(client, fake_llm):
    fake_llm(text_reply("Salam! Apna goal batayein."))
    headers = register(client)
    res = client.post("/chat", json={"message": "hi"}, headers=headers)
    assert res.json() == {"reply": "Salam! Apna goal batayein."}

    history = client.get("/chat/history", headers=headers).json()
    assert [(m["role"], m["text"]) for m in history] == [("user", "hi"), ("coach", "Salam! Apna goal batayein.")]


def test_tool_call_runs_and_result_goes_back_to_model(client, fake_llm, db):
    fake = fake_llm(tool_reply(("log_meal", {"food": "Biryani", "calories": 700})), text_reply("Logged!"))
    headers = register(client)
    res = client.post("/chat", json={"message": "maine biryani khayi 700 cal"}, headers=headers)
    assert res.json()["reply"] == "Logged!"
    assert db.scalar(select(func.count()).select_from(MealLog)) == 1
    tool_message = fake.requests[1][-1]
    assert tool_message["role"] == "tool" and '"status": "logged"' in tool_message["content"]


def test_tool_errors_are_reported_to_model_not_crashed(client, fake_llm):
    fake = fake_llm(tool_reply(("set_reminder", {"time_hhmm": "7pm", "message": "x"})), text_reply("Time?"))
    headers = register(client)
    assert client.post("/chat", json={"message": "remind me 7pm"}, headers=headers).status_code == 200
    assert "HH:MM" in fake.requests[1][-1]["content"]


def test_history_is_sent_on_next_request(client, fake_llm):
    fake = fake_llm(text_reply("first"), text_reply("second"))
    headers = register(client)
    client.post("/chat", json={"message": "one"}, headers=headers)
    client.post("/chat", json={"message": "two"}, headers=headers)
    contents = [m["content"] for m in fake.requests[1]]
    assert contents[1:] == ["one", "first", "two"]


def test_history_window_never_starts_with_orphan_tool_message(client, fake_llm, db, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "history_window", 3)
    fake = fake_llm(tool_reply(("get_progress_summary", {})), text_reply("done"), text_reply("next"))
    headers = register(client)
    client.post("/chat", json={"message": "progress?"}, headers=headers)
    client.post("/chat", json={"message": "and now?"}, headers=headers)
    sent = fake.requests[-1]
    assert sent[1]["role"] != "tool"


def test_llm_outage_returns_503_and_saves_nothing(client, fake_llm, db):
    fake_llm(openai.APIConnectionError(request=None))
    headers = register(client)
    res = client.post("/chat", json={"message": "hi"}, headers=headers)
    assert res.status_code == 503
    assert db.scalar(select(func.count()).select_from(ChatMessage)) == 0


def test_llm_outage_after_a_tool_ran_keeps_the_record(client, fake_llm, db):
    fake_llm(tool_reply(("log_weight", {"weight_kg": 80})), openai.APIConnectionError(request=None))
    headers = register(client)
    res = client.post("/chat", json={"message": "weight 80"}, headers=headers)
    assert res.status_code == 200
    assert "lost connection" in res.json()["reply"]
    roles = db.scalars(select(ChatMessage.role).order_by(ChatMessage.id)).all()
    assert roles == ["user", "assistant", "tool", "assistant"]


def test_users_cannot_see_each_others_history(client, fake_llm):
    fake_llm(text_reply("private"))
    a = register(client, "alice")
    b = register(client, "bobby")
    client.post("/chat", json={"message": "secret"}, headers=a)
    assert client.get("/chat/history", headers=b).json() == []


def test_clear_history(client, fake_llm):
    fake_llm(text_reply("ok"))
    headers = register(client)
    client.post("/chat", json={"message": "hi"}, headers=headers)
    assert client.delete("/chat/history", headers=headers).status_code == 204
    assert client.get("/chat/history", headers=headers).json() == []


def test_message_length_is_limited(client):
    headers = register(client)
    assert client.post("/chat", json={"message": "x" * 2001}, headers=headers).status_code == 422