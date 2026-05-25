from fastapi import FastAPI, HTTPException
from app.engine.session import create_session, get_session, reset_session

app = FastAPI(title="Massaspectrometer App")


@app.get("/")
def home():
    return {"status": "online", "app": "Massaspectrometer met snelheidsselector"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/session/create")
def api_create_session(level: str = "beginner"):
    session = create_session(level)
    return session


@app.get("/session/{session_id}")
def api_get_session(session_id: str):
    session = get_session(session_id)

    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return session


@app.post("/session/{session_id}/reset")
def api_reset_session(session_id: str):
    session = reset_session(session_id)

    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return session
