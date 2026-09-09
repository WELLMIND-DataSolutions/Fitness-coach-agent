"""
api.py — FastAPI backend, AB AUTHENTICATION KE SATH.
Naye endpoints: /register aur /login. /chat ab protected hai —
JWT token ke bagair chalega nahi.
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from database import init_db, get_connection
from agent import FitCoachAgent
from reminder_scheduler import start_scheduler
from auth import hash_password, verify_password, create_access_token, decode_access_token

app = FastAPI(title="FitCoach API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()
start_scheduler()

# CHANGED: ab ek global agent nahi, balke user_id -> FitCoachAgent dictionary.
# Naya user pehli baar chat kare to yahan uski agent instance ban ke store ho jati hai.
agents = {}

security = HTTPBearer()


def get_agent(user_id: int) -> FitCoachAgent:
    if user_id not in agents:
        agents[user_id] = FitCoachAgent(user_id=user_id)
    return agents[user_id]


def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    """
    Ye function har protected endpoint (jaise /chat) se pehle chalta hai.
    Request ke 'Authorization: Bearer <token>' header se token nikalta hai,
    verify karta hai, aur asli user_id return karta hai.
    """
    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid ya expired token — dobara login karein.",
        )
    return user_id


class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


@app.get("/")
def health_check():
    return {"status": "FitCoach API is running"}


@app.post("/register", response_model=TokenResponse)
def register(request: RegisterRequest):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username=?", (request.username,))
    if c.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Ye username pehle se maujood hai.")

    hashed = hash_password(request.password)
    c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (request.username, hashed))
    conn.commit()
    user_id = c.lastrowid
    conn.close()

    token = create_access_token(user_id, request.username)
    return TokenResponse(access_token=token)


@app.post("/login", response_model=TokenResponse)
def login(request: LoginRequest):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, password_hash FROM users WHERE username=?", (request.username,))
    row = c.fetchone()
    conn.close()

    if not row or not verify_password(request.password, row[1]):
        raise HTTPException(status_code=401, detail="Username ya password ghalat hai.")

    token = create_access_token(row[0], request.username)
    return TokenResponse(access_token=token)


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, user_id: int = Depends(get_current_user_id)):
    agent = get_agent(user_id)
    reply = agent.chat(request.message)
    return ChatResponse(reply=reply)