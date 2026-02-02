from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from llama_cpp import Llama
import uvicorn

# --- CẤU HÌNH MODEL ---
MODEL_PATH = "/home/minhthong/Desktop/Chatbot/tinyllama_evn_final.gguf"
llm = Llama(
    model_path=MODEL_PATH,
    n_ctx=2048,
    n_threads=8,
    temperature=0.0,
    top_p=1.0,
    repeat_penalty=1.1,
    verbose=False
)

RAW_SYSTEM_MESSAGE = """Bạn là trợ lý ảo chuyên trách quản lý năng lượng nhà máy. Chỉ sử dụng dữ liệu do người dùng cung cấp để tính toán điện năng tiêu thụ và tiền điện. Không bịa số liệu, không suy đoán. Nếu thiếu thông tin cần thiết để tính toán, hãy lịch sự yêu cầu người dùng cung cấp thêm.
Quy định giá tăng dần theo bậc tiêu thụ: Bậc 1 (0-50kWh) 1.984đ/kWh, Bậc 2 (51-100kWh) 2.050đ/kWh, Bậc 3 (101-200kWh) 2.380đ/kWh, Bậc 4 (201-300kWh) 2.998đ/kWh, Bậc 5 (301-400kWh) 3.350đ/kWh, và Bậc 6 (từ 401kWh trở lên) 3.460đ/kWh, áp dụng theo Quyết định 14/2025/QĐ-TTg của Thủ tướng Chính phủ."""

app = FastAPI()

class ChatInput(BaseModel):
    text: str

def format_prompt(user_input: str):
    return f"<|system|>\n{RAW_SYSTEM_MESSAGE}</s>\n<|user|>\n{user_input}</s>\n<|assistant|>\n"

@app.post("/predict")
def predict(data: ChatInput):
    prompt = format_prompt(data.text)
    # Thêm tham số echo=False để không lặp lại prompt trong kết quả
    output = llm(prompt, max_tokens=512, stop=["</ptys>"], echo=False)
    return {"answer": output["choices"][0]["text"].strip()}

@app.post("/stream")
async def stream_chat(data: ChatInput):
    prompt = format_prompt(data.text)
    
    def generate():
        # Gọi stream trực tiếp từ llm
        for chunk in llm(prompt, max_tokens=512, stop=["</s>"], stream=True, echo=False):
            token = chunk["choices"][0]["text"]
            if token:
                yield token

    return StreamingResponse(generate(), media_type="text/event-stream")

if __name__ == "__main__":
    # Chạy uvicorn trực tiếp
    uvicorn.run(app, host="0.0.0.0", port=8000)