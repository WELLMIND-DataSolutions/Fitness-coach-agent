"""
agent.py — Agent ka "brain-loop".
UPDATED: FitCoachAgent ab per-user hai (user_id le kar banta hai).
Har tool function us user ke user_id ke sath 'bind' hota hai
(functools.partial se) — is se LLM ko kabhi user_id dena/dikhna
nahi parta, aur ek user doosray ka data touch nahi kar sakta.
"""

import json
from functools import partial
from openai import OpenAI

from config import GROQ_API_KEY, GROQ_BASE_URL, MODEL_NAME, MAX_TOKENS
from system_prompt import SYSTEM_PROMPT
from tool_schema import TOOLS
import tools as tools_module

client = OpenAI(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL)

MAX_TOOL_ITERATIONS = 6


class FitCoachAgent:
    """
    Ab har instance EK specific user ke liye hoti hai.
    api.py mein user_id se keyed dictionary mein ye instances store hongi.
    """

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # NAYA: har tool ko is user_id ke sath bind kar diya —
        # LLM ko sirf apne schema wale arguments (name, age, exercise, etc.) dene hain,
        # user_id kabhi uske control mein nahi hai.
        self.available_functions = {
            "set_profile": partial(tools_module.set_profile, user_id=user_id),
            "get_profile": partial(tools_module.get_profile, user_id=user_id),
            "calculate_calories": partial(tools_module.calculate_calories, user_id=user_id),
            "generate_workout_plan": partial(tools_module.generate_workout_plan, user_id=user_id),
            "log_workout": partial(tools_module.log_workout, user_id=user_id),
            "log_meal": partial(tools_module.log_meal, user_id=user_id),
            "log_weight": partial(tools_module.log_weight, user_id=user_id),
            "get_progress_summary": partial(tools_module.get_progress_summary, user_id=user_id),
            "set_reminder": partial(tools_module.set_reminder, user_id=user_id),
        }

    def chat(self, user_message: str) -> str:
        self.messages.append({"role": "user", "content": user_message})

        for _ in range(MAX_TOOL_ITERATIONS):
            response = client.chat.completions.create(
                model=MODEL_NAME,
                max_tokens=MAX_TOKENS,
                messages=self.messages,
                tools=TOOLS,
                tool_choice="auto",
            )

            choice = response.choices[0]
            msg = choice.message

            if msg.tool_calls:
                self.messages.append(
                    {
                        "role": "assistant",
                        "content": msg.content or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                },
                            }
                            for tc in msg.tool_calls
                        ],
                    }
                )

                for tc in msg.tool_calls:
                    fn_name = tc.function.name
                    try:
                        args = json.loads(tc.function.arguments or "{}")
                    except json.JSONDecodeError:
                        args = {}

                    fn = self.available_functions.get(fn_name)
                    if fn is None:
                        result = {"error": f"Unknown tool: {fn_name}"}
                    else:
                        try:
                            result = fn(**args)
                        except Exception as e:
                            result = {"error": str(e)}

                    self.messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "name": fn_name,
                            "content": json.dumps(result, default=str),
                        }
                    )

                continue

            final_text = msg.content or ""
            self.messages.append({"role": "assistant", "content": final_text})
            return final_text

        return "Sorry, kuch process karne mein masla aa gaya. Dobara try karein."