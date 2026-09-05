"""
api.py — FastAPI backend jo agent.py ko HTTP endpoints ke zariye expose karta hai.
Flutter app isi se baat karega (POST requests bhejega, JSON replies milengi).

Run: uvicorn api:app --host 0.0.0.0 --port 8000 --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import init_db
from agent import FitCoachAgent
from reminder_scheduler import start_scheduler

app = FastAPI(title="FitCoach API")

# CORS — Flutter app (mobile/emulator) se requests allow karne ke liye.
# Production mein allow_origins ko apni app ke actual domain/IP tak limit karo.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# NOTE: Abhi ek hi global agent instance hai — matlab sab users ka context
# mix ho jayega. Multi-user support ke liye session/user_id based agent
# instances chahiye honge (aage discuss karenge jab multi-user pe aayenge).
init_db()
start_scheduler()
agent = FitCoachAgent()


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


@app.get("/")
def health_check():
    return {"status": "FitCoach API is running"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    reply = agent.chat(request.message)
    return ChatResponse(reply=reply)