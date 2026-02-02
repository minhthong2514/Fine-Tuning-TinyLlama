from fastapi import FastAPI
from pydantic import BaseModel
from engine import ElevatorAI
import uvicorn

app = FastAPI()

# Khởi tạo model AI
print("Đang nạp Model Qwen vào RAM/GPU... Vui lòng đợi.")
brain = ElevatorAI() 

class QueryRequest(BaseModel):
    question: str

@app.get("/")
async def root():
    return {"message": "Elevator AI Agent API is running!"}

@app.post("/ask")
async def ask_elevator(req: QueryRequest):
    answer = brain.ask(req.question)
    return {"status": "success", "answer": answer}

if __name__ == "__main__":
    print("Khởi động Server tại cổng 8080...")
    uvicorn.run(app, host="0.0.0.0", port=8080)