import json
import os
from types import SimpleNamespace

os.environ.update(
    {
        "ENVIRONMENT": "test",
        "GROQ_API_KEY": "test-key",
        "JWT_SECRET": "test-secret-that-is-long-enough-0123456789",
        "DATABASE_URL": "sqlite:///./test_fitcoach.db",
        "LOG_LEVEL": "WARNING",
    }
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import agent  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.deps import limiter  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    limiter.enabled = False
    limiter.reset()
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


@pytest.fixture
def client():
    return TestClient(app)


def register(client, username="alice", password="password123", tz="Asia/Karachi"):
    res = client.post("/auth/register", json={"username": username, "password": password, "timezone": tz})
    assert res.status_code == 201, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


# ------------------------------------------------------------------ fake LLM


def text_reply(content):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content, tool_calls=None))])


def tool_reply(*calls):
    tool_calls = [
        SimpleNamespace(id=f"call_{i}", function=SimpleNamespace(name=name, arguments=json.dumps(args)))
        for i, (name, args) in enumerate(calls)
    ]
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="", tool_calls=tool_calls))])


class FakeLLM:
    """Returns scripted responses in order and records every request."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.requests.append(json.loads(json.dumps(kwargs["messages"], default=str)))
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


@pytest.fixture
def fake_llm(monkeypatch):
    def install(*responses):
        fake = FakeLLM(responses)
        monkeypatch.setattr(agent, "get_llm_client", lambda: fake)
        return fake

    return install