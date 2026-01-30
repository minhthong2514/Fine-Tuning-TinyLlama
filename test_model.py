from llama_cpp import Llama
import sys

# 1. Cấu hình Model
MODEL_PATH = "/home/minhthong/Desktop/code/tinyllama_evn_final.gguf"

llm = Llama(
    model_path=MODEL_PATH,
    n_ctx=2048,
    n_threads=8,
    temperature=0.0,   
    top_p=1.0,
    repeat_penalty=1.1,
    verbose=False
)

# Nội dung hệ thống (giữ nguyên như dataset)
RAW_SYSTEM_MESSAGE = """Bạn là trợ lý ảo chuyên trách quản lý năng lượng nhà máy. Chỉ sử dụng dữ liệu do người dùng cung cấp để tính toán điện năng tiêu thụ và tiền điện. Không bịa số liệu, không suy đoán. Nếu thiếu thông tin cần thiết để tính toán, hãy lịch sự yêu cầu người dùng cung cấp thêm.
\nQuy định giá tăng dần theo bậc tiêu thụ: Bậc 1 (0-50kWh) 1.984đ/kWh, Bậc 2 (51-100kWh) 2.050đ/kWh, Bậc 3 (101-200kWh) 2.380đ/kWh, Bậc 4 (201-300kWh) 2.998đ/kWh, Bậc 5 (301-400kWh) 3.350đ/kWh, và Bậc 6 (từ 401kWh trở lên) 3.460đ/kWh, áp dụng theo Quyết định 14/2025/QĐ-TTg của Thủ tướng Chính phủ."""

print("=== Nhập 'exit' để thoát | Nhấn Enter 2 lần để gửi tin nhắn ===")

while True:
    print("\n[Mời bạn nhập nội dung]:")
    
    # Nhận toàn bộ nội dung (hỗ trợ xuống dòng nhiều dòng)
    lines = []
    while True:
        line = input()
        if line.strip() == "" and len(lines) > 0: # Nhấn Enter dòng trống để kết thúc
            break
        if line.lower() in ["exit", "quit"]:
            sys.exit()
        lines.append(line)
    
    user_full_input = "\n".join(lines)

    # 2. TỰ ĐỘNG FORMAT: Ghép vào template chuẩn dataset
    # Mọi thứ người dùng nhập sẽ nằm trọn trong thẻ <|user|>
    prompt = (
        f"<|system|>\n{RAW_SYSTEM_MESSAGE}</s>\n"
        f"<|user|>\n{user_full_input}</s>\n"
        f"<|assistant|>\n"
    )

    print("\n" + "-"*20 + " ĐANG TÍNH TOÁN " + "-"*20 + "\n")

    # 3. Stream output
    stream = llm(
        prompt,
        max_tokens=512,
        stop=["</s>"],
        stream=True
    )
    
    for output in stream:
        token = output["choices"][0]["text"]
        print(token, end="", flush=True)

    print("\n\n" + "="*50)