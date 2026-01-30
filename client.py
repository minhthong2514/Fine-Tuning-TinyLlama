import requests
import sys

# THAY ĐỊA CHỈ IP DƯỚI ĐÂY BẰNG IP CỦA MÁY A (SERVER)
SERVER_IP = "" 
URL = f"http://{SERVER_IP}:8000/stream"

print("=== Kết nối tới Chatbot EVN Server ===")

while True:
    print("\n[Mời bạn nhập nội dung]:")
    lines = []
    while True:
        line = input()
        if line.strip() == "" and len(lines) > 0: break
        if line.lower() in ["exit", "quit"]: sys.exit()
        lines.append(line)
    
    user_input = "\n".join(lines)

    # Gửi yêu cầu tới Server dưới dạng stream
    print("\n" + "-"*15 + " PROCESSING " + "-"*15 + "\n")
    
    try:
        with requests.post(URL, json={"text": user_input}, stream=True) as r:
            if r.status_code == 200:
                for chunk in r.iter_content(chunk_size=None):
                    if chunk:
                        print(chunk.decode("utf-8"), end="", flush=True)
            else:
                print(f"Lỗi Server: {r.status_code}")
    except Exception as e:
        print(f"Không thể kết nối tới Server: {e}")

    print("\n\n" + "="*50)