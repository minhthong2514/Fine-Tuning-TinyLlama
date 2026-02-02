import threading
import time
from engine import ElevatorAI

class InteractiveAgent:
    def __init__(self):
        print("--- Đang khởi động AI Agent. Vui lòng đợi ---")
        # Khởi tạo bộ não AI (Trong này đã có sẵn kết nối MongoDB rồi)
        self.agent = ElevatorAI()
        
        # MƯỢN luôn collection từ agent, không cần đăng nhập lại ở đây
        self.collection = self.agent.collection
        
        # Lấy ID của bản ghi cuối cùng để bắt đầu giám sát
        last_doc = list(self.collection.find().sort("_id", -1).limit(1))
        self.last_seen_id = last_doc[0]['_id'] if last_doc else None
        
        self.running = True

    def monitor_stream(self):
        """Luồng chạy ngầm để theo dõi dữ liệu mới"""
        print("--- Chế độ giám sát dữ liệu thực tế đã bật ---")
        while self.running:
            try:
                # Dùng chung collection với AI để quét dữ liệu mới
                latest_doc = self.collection.find().sort("_id", -1).limit(1)
                doc_list = list(latest_doc)
                
                if doc_list:
                    current_id = doc_list[0]['_id']
                    if current_id != self.last_seen_id:
                        self.last_seen_id = current_id
                        d = doc_list[0]
                        print(f"\n[DỮ LIỆU MỚI] Thang: {d.get('device_id')} | Tầng: {d.get('floor')} | Điện áp: {d.get('voltage')}V")
                        print("Bạn: ", end="", flush=True) 
                
                time.sleep(1)
            except Exception as e:
                print(f"\n[LỖI STREAM]: {e}")
                time.sleep(5)

    def start(self):
        stream_thread = threading.Thread(target=self.monitor_stream, daemon=True)
        stream_thread.start()

        print("\n" + "="*50)
        print("HỆ THỐNG GIÁM SÁT THANG MÁY THÔNG MINH")
        print("Nhập câu hỏi để tương tác hoặc đợi dữ liệu mới...")
        print("Gõ 'exit' để thoát")
        print("="*50)

        while True:
            try:
                user_input = input("Bạn: ")
                if user_input.lower() in ['exit', 'quit', 'thoát']:
                    self.running = False
                    break
                if not user_input.strip():
                    continue

                print("AI đang phân tích dữ liệu...")
                response = self.agent.ask(user_input)
                print(f"AI Agent: {response}")
            except EOFError:
                break
            except Exception as e:
                print(f"Lỗi: {e}")

if __name__ == "__main__":
    app = InteractiveAgent()
    app.start()