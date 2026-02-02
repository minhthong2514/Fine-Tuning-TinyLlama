from fastapi import FastAPI
from pydantic import BaseModel
from engine import ElevatorAI

app = FastAPI()
brain = ElevatorAI() # Khởi tạo model một lần duy nhất khi chạy server

class QueryRequest(BaseModel):
    question: str

@app.post("/ask")
async def ask_elevator(req: QueryRequest):
    answer = brain.ask(req.question)
    return {"status": "success", "answer": answer}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)