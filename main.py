"""
main.py — CLI entrypoint. Database initialize karta hai aur
terminal mein FitCoach agent ke sath chat-loop chalata hai.
"""

from database import init_db
from agent import FitCoachAgent
from reminder_scheduler import start_scheduler   # 👈 NAYI LINE


def main():
    init_db()
    start_scheduler()   # 👈 NAYI LINE — reminder checker background mein start ho jayega
    agent = FitCoachAgent()

    print("=" * 50)
    print("💪 FitCoach — Your AI Fitness Assistant")
    print("Type 'exit' ya 'quit' likh kar chat khatam karein.")
    print("=" * 50)

    while True:
        user_input = input("\nYou: ").strip()
        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            print("FitCoach: Chalo phir, apna khayal rakhna! 💪")
            break

        try:
            reply = agent.chat(user_input)
        except Exception as e:
            reply = f"[Error] Kuch masla ho gaya: {e}"

        print(f"\nFitCoach: {reply}")


if __name__ == "__main__":
    main()