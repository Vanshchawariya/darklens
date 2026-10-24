
from fastapi import FastAPI

app = FastAPI(title="DarkLens API")


@app.get("/")
def home():
    return {
        "message": "Welcome to DarkLens API!",
        "status": "running"
    }
