from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from graph import graph


app = FastAPI()
FRONTEND_PATH = Path(__file__).resolve().parent / "static" / "index.html"


class ChatRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(FRONTEND_PATH)


@app.post("/chat")
def chat(request: ChatRequest):
    result = graph.invoke(
        {"current_input": request.text, "messages": []},
        context={"profile": None},
    )
    return {"response": result.get("response", "")}
