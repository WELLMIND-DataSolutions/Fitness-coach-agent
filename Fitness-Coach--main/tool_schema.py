"""
tool_schema.py — Groq (OpenAI-compatible) function-calling ke liye schema definitions.
Har entry `tools.py` ke ek function ko describe karti hai — naam, purpose, parameters.
Ye schema hi LLM ko batata hai ke kaunsa tool kab aur kaise call karna hai.

IMPORTANT: naam yahan aur tools.py mein EXACTLY match hone chahiye,
kyunki agent.py inhi naamon se function lookup karega.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "set_profile",
            "description": (
                "User ka fitness profile save/update karta hai (naam, age, gender, height, weight, goal, activity level). "
                "Jab bhi user apni basic details de ya profile update karna chahe, ye call karo. "
                "Existing profile ko replace kar deta hai (sirf 1 profile store hoti hai)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "User ka naam"},
                    "age": {"type": "integer", "description": "Age in years"},
                    "gender": {"type": "string", "description": "'male' ya 'female'"},
                    "height_cm": {"type": "number", "description": "Height in centimeters"},
                    "weight_kg": {"type": "number", "description": "Weight in kilograms"},
                    "goal": {
                        "type": "string",
                        "description": "Fitness goal, e.g. 'weight loss', 'muscle gain', 'general fitness'",
                    },
                    "activity_level": {
                        "type": "string",
                        "description": "Ek: sedentary, light, moderate, active, very_active",
                    },
                },
                "required": ["name", "age", "gender", "height_cm", "weight_kg", "goal", "activity_level"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_profile",
            "description": "Saved user profile fetch karta hai. Jab bhi profile check karna ho (age, weight, goal, etc), ye call karo.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_calories",
            "description": (
                "User ke saved profile se BMR, TDEE, target daily calories aur macros (protein/fat/carbs) calculate karta hai. "
                "Diet/calorie related koi bhi sawal ho toh pehle ye call karo — khud se calorie calculate mat karo."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_workout_plan",
            "description": (
                "User ke goal ke mutabiq weekly workout plan generate karta hai. "
                "Agar user workout plan maange, ye call karo — khud se exercises invent mat karo."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "goal": {
                        "type": "string",
                        "description": "Optional — na diya jaye toh profile ke goal se le lega. e.g. 'weight loss', 'muscle gain'",
                    },
                    "days_per_week": {
                        "type": "integer",
                        "description": "Kitne din workout karna hai (default 4)",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "log_workout",
            "description": "Aik completed workout exercise ko database mein log karta hai (aaj ki date ke sath).",
            "parameters": {
                "type": "object",
                "properties": {
                    "exercise": {"type": "string", "description": "Exercise ka naam, e.g. 'Squats'"},
                    "sets": {"type": "integer"},
                    "reps": {"type": "integer"},
                    "weight_kg": {"type": "number", "description": "Optional, agar weighted exercise hai"},
                },
                "required": ["exercise", "sets", "reps"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "log_meal",
            "description": "Aik khaya hua meal/food item aur uski calories log karta hai (aaj ki date ke sath).",
            "parameters": {
                "type": "object",
                "properties": {
                    "food": {"type": "string", "description": "Food/meal ka naam"},
                    "calories": {"type": "number", "description": "Calories in kcal"},
                },
                "required": ["food", "calories"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "log_weight",
            "description": "User ka current body weight log karta hai (aaj ki date ke sath) — progress tracking ke liye.",
            "parameters": {
                "type": "object",
                "properties": {
                    "weight_kg": {"type": "number", "description": "Current weight in kilograms"},
                },
                "required": ["weight_kg"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_progress_summary",
            "description": (
                "User ki weight history, pichle 7 din ki calories aur pichle 7 din ke workouts ka summary deta hai. "
                "Jab user progress/trend poochay, ye call karo."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_reminder",
            "description": "Aik reminder set karta hai (e.g. workout ya paani peene ka reminder) given time aur message.",
            "parameters": {
                "type": "object",
                "properties": {
                    "time_str": {"type": "string", "description": "Time, e.g. '18:00' ya 'every day 7am'"},
                    "message": {"type": "string", "description": "Reminder ka text"},
                },
                "required": ["time_str", "message"],
            },
        },
    },
]