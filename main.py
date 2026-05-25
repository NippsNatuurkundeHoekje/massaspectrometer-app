from fastapi import FastAPI

app = FastAPI(title="Massaspectrometer App")


@app.get("/")
def home():
    return {"status": "online", "app": "Massaspectrometer met snelheidsselector"}
