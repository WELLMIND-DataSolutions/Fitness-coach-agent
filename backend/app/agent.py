"""Agent loop.

Stateless: every request rebuilds context from the chat_messages table, so the API can
restart or run as several instances without losing conversations, and memory use does
not grow with the number of users.
"""

import json
import logging
from functools import lru_cache

import openai
from openai import OpenAI
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import ChatMessage, User
from app.prompts import SYSTEM_PROMPT
from app.tools import TOOLS, ToolContext, ToolError, openai_tool_specs

log = logging.getLogger(__name__)

INTERRUPTED_REPLY = (
    "I lost connection to the AI service before I could finish. "
    "Anything I confirmed above is saved; please send your message again to continue."
)
LOOP_LIMIT_REPLY = "That took too many steps for me to finish. Could you break it into a smaller request?"


class LLMUnavailable(Exception):
    """The LLM provider failed before any state changed; safe for the client to retry."""


@lru_cache
def get_llm_client() -> OpenAI:
    s = get_settings()
    return OpenAI(
        api_key=s.groq_api_key,
        base_url=s.groq_base_url,
        timeout=s.llm_timeout_seconds,
        max_retries=s.llm_max_retries,
    )


def _to_api_message(row: ChatMessage) -> dict:
    if row.role == "tool":
        return {"role": "tool", "tool_call_id": row.tool_call_id, "content": row.content}
    message = {"role": row.role, "content": row.content}
    if row.tool_calls:
        message["tool_calls"] = row.tool_calls
    return message


def load_history(db: Session, user_id: int, window: int) -> list[dict]:
    rows = list(
        db.scalars(
            select(ChatMessage).where(ChatMessage.user_id == user_id).order_by(ChatMessage.id.desc()).limit(window)
        )
    )
    rows.reverse()
    # A cut-off window may start in the middle of a tool exchange; the API rejects
    # tool results without their assistant call, so start at the first user turn.
    while rows and rows[0].role != "user":
        rows.pop(0)
    return [_to_api_message(r) for r in rows]


def _run_tool(ctx: ToolContext, name: str, raw_args: str | None) -> dict:
    tool = TOOLS.get(name)
    if tool is None:
        return {"error": f"Unknown tool: {name}"}
    try:
        args = json.loads(raw_args or "{}")
        if not isinstance(args, dict):
            raise ValueError
    except ValueError:
        return {"error": "Arguments were not a valid JSON object"}
    try:
        return tool.fn(ctx, **args)
    except ToolError as exc:
        return {"error": str(exc)}
    except TypeError:
        return {"error": f"Invalid or missing arguments for {name}"}
    except Exception:
        log.exception("Tool %s failed for user %s", name, ctx.user.id)
        ctx.db.rollback()
        return {"error": "Internal error while running the tool"}


def run_chat(db: Session, user: User, text: str, client: OpenAI | None = None) -> str:
    settings = get_settings()
    client = client or get_llm_client()
    ctx = ToolContext(db=db, user=user)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += load_history(db, user.id, settings.history_window)
    messages.append({"role": "user", "content": text})
    new_rows = [ChatMessage(user_id=user.id, role="user", content=text)]
    tools_ran = False

    def finish(reply: str) -> str:
        new_rows.append(ChatMessage(user_id=user.id, role="assistant", content=reply))
        db.add_all(new_rows)
        db.commit()
        return reply

    for _ in range(settings.max_tool_iterations):
        try:
            response = client.chat.completions.create(
                model=settings.model_name,
                max_tokens=settings.max_tokens,
                messages=messages,
                tools=openai_tool_specs(),
                tool_choice="auto",
            )
        except openai.OpenAIError:
            log.exception("LLM request failed for user %s", user.id)
            if tools_ran:
                # Tools already changed data; record what happened so a retry does not repeat it.
                return finish(INTERRUPTED_REPLY)
            raise LLMUnavailable from None

        msg = response.choices[0].message
        if not msg.tool_calls:
            return finish(msg.content or "I could not put together a reply. Please try again.")

        calls = [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.function.name, "arguments": tc.function.arguments},
            }
            for tc in msg.tool_calls
        ]
        messages.append({"role": "assistant", "content": msg.content or "", "tool_calls": calls})
        new_rows.append(ChatMessage(user_id=user.id, role="assistant", content=msg.content or "", tool_calls=calls))

        for tc in msg.tool_calls:
            result = _run_tool(ctx, tc.function.name, tc.function.arguments)
            tools_ran = True
            log.info("tool=%s user=%s ok=%s", tc.function.name, user.id, "error" not in result)
            content = json.dumps(result, default=str)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": content})
            new_rows.append(
                ChatMessage(
                    user_id=user.id, role="tool", content=content, tool_call_id=tc.id, tool_name=tc.function.name
                )
            )

    return finish(LOOP_LIMIT_REPLY)