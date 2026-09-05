"""
agent.py — Agent ka "brain-loop". Yahan LLM (Groq) ko call karte hain,
tool_calls ko detect karte hain, tools.py se respective function chalate hain,
result wapas LLM ko dete hain, jab tak final text answer na mil jaye.

Koi hardcoded if-else business-logic nahi — routing sirf LLM ki reasoning se hoti hai.
"""

import json
from openai import OpenAI

from config import GROQ_API_KEY, GROQ_BASE_URL, MODEL_NAME, MAX_TOKENS
from system_prompt import SYSTEM_PROMPT
from tool_schema import TOOLS
import tools as tools_module

# Groq ka endpoint OpenAI-compatible hai, isliye OpenAI client hi reuse kar sakte hain.
client = OpenAI(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL)

# tool_schema.py mein jo naam likhe hain, unko tools.py ke actual function se map karo.
AVAILABLE_FUNCTIONS = {
    "set_profile": tools_module.set_profile,
    "get_profile": tools_module.get_profile,
    "calculate_calories": tools_module.calculate_calories,
    "generate_workout_plan": tools_module.generate_workout_plan,
    "log_workout": tools_module.log_workout,
    "log_meal": tools_module.log_meal,
    "log_weight": tools_module.log_weight,
    "get_progress_summary": tools_module.get_progress_summary,
    "set_reminder": tools_module.set_reminder,
}

MAX_TOOL_ITERATIONS = 6  # infinite loop se bachne ke liye safety cap


class FitCoachAgent:
    """
    Conversation history ko memory mein rakhta hai (single session ke liye).
    Har `chat()` call ek user message leta hai aur final assistant reply return karta hai.
    """

    def __init__(self):
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

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

            # LLM ne tool(s) call karne ka faisla kiya
            if msg.tool_calls:
                # assistant ka tool_call-wala message history mein daalo
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

                # Har tool_call ko actually run karo
                for tc in msg.tool_calls:
                    fn_name = tc.function.name
                    try:
                        args = json.loads(tc.function.arguments or "{}")
                    except json.JSONDecodeError:
                        args = {}

                    fn = AVAILABLE_FUNCTIONS.get(fn_name)
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

                # loop continue — LLM ko tool results ke sath dobara call karo
                continue

            # Koi tool call nahi — ye final answer hai
            final_text = msg.content or ""
            self.messages.append({"role": "assistant", "content": final_text})
            return final_text

        # Agar loop cap khatam ho gayi (rare edge case)
        return "Sorry, kuch process karne mein masla aa gaya. Dobara try karein."