import threading
import time
from engine import ElevatorAI

class InteractiveAgent:
    def __init__(self):
        print("--- Đang khởi động AI Agent. Vui lòng đợi ---")
        # Khởi tạo bộ não AI (Đã bao gồm cấu hình MongoDB và Model Qwen)
        self.agent = ElevatorAI()
        
        # MƯỢN collection từ agent
        self.collection = self.agent.collection
        
        # Lấy ID của bản ghi cuối cùng để bắt đầu giám sát từ mốc này
        last_doc = list(self.collection.find().sort("timestamp", -1).limit(1))
        self.last_seen_id = last_doc[0]['_id'] if last_doc else None
        
        self.running = True

    def monitor_stream(self):
        """Luồng chạy ngầm để theo dõi dữ liệu Camera mới"""
        print("--- Chế độ giám sát Camera thực tế đã bật ---")
        while self.running:
            try:
                # Tìm bản ghi mới nhất dựa trên thời gian
                latest_doc = list(self.collection.find().sort("timestamp", -1).limit(1))
                
                if latest_doc:
                    d = latest_doc[0]
                    current_id = d['_id']
                    
                    if current_id != self.last_seen_id:
                        self.last_seen_id = current_id
                        
                        # Trích xuất thông tin hành vi từ dữ liệu camera
                        people = d.get('people', [])
                        count = len(people)
                        behaviors = [p.get('behavior', 'không xác định') for p in people]
                        behavior_str = ", ".join(behaviors) if behaviors else "Không có hành động"
                        time_str = d.get('timestamp')
                        if isinstance(time_str, str): # Nếu là ISO string thì cắt lấy giờ
                             time_str = time_str.split('T')[-1]

                        # In thông báo dữ liệu mới ra màn hình
                        print(f"\n[CAMERA MỚI] Lúc: {time_str} | Số người: {count} | Hành vi: [{behavior_str}]")
                        print("Bạn: ", end="", flush=True) 
                
                time.sleep(2) # Quét mỗi 2 giây để tránh spam database
            except Exception as e:
                print(f"\n[LỖI STREAM]: {e}")
                time.sleep(5)

    def start(self):
        # Chạy luồng monitor ngầm
        stream_thread = threading.Thread(target=self.monitor_stream, daemon=True)
        stream_thread.start()

        print("\n" + "="*50)
        print("HỆ THỐNG GIÁM SÁT CAMERA THANG MÁY THÔNG MINH")
        print("Nhập câu hỏi (VD: 'Lúc 16:13:53 có mấy người đứng?')")
        print("Gõ 'exit' để thoát")
        print("="*50)

        while True:
            try:
                user_input = input("Bạn: ")
                
                if user_input.lower() in ['exit', 'quit', 'thoát']:
                    self.running = False
                    print("Đang tắt hệ thống...")
                    break
                    
                if not user_input.strip():
                    continue
                
                print("AI đang phân tích dữ liệu camera...\n", end='\r')
                
                # Gọi hàm ask từ engine.py
                # Lưu ý: engine.py của bạn đang print kết quả trực tiếp nếu stream=True
                response = self.agent.ask(user_input, stream=True)
                
                # Nếu stream=False thì mới cần print response ở đây
                if response:
                    print(response)
                    
                print("\n" + "-" * 30)
                
            except EOFError:
                break
            except Exception as e:
                print(f"Lỗi hệ thống: {e}")

if __name__ == "__main__":
    app = InteractiveAgent()
    app.start()