from fastapi import FastAPI, HTTPException
from app.engine.session import create_session, get_session, reset_session, step_session

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


@app.post("/session/{session_id}/step")
def api_step_session(session_id: str):
    session = step_session(session_id)

    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return session


@app.get("/session/{session_id}/ui")
def api_get_ui_state(session_id: str):
    session = get_session(session_id)

    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return session.ui_state


@app.post("/session/{session_id}/value")
def api_set_value(session_id: str, key: str, value: float):
    session = get_session(session_id)

    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if key not in session.ui_state["values"]:
        raise HTTPException(status_code=400, detail=f"Unknown value key: {key}")

    session.ui_state["values"][key] = value

    return {
        "session_id": session_id,
        "key": key,
        "value": value,
        "values": session.ui_state["values"],
    }
