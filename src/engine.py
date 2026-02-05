import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TextStreamer
import json, re
from pymongo import MongoClient
import urllib.parse
from datetime import datetime, timedelta
import os
import warnings

# --- TẮT CẢNH BÁO ---
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
warnings.filterwarnings("ignore", category=UserWarning)

class ElevatorAI:
    def __init__(self):
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"--- Đang khởi động AI trên thiết bị: {device.upper()} ---")

        # 1. Khởi tạo Model
        self.model_path = r"D:\University\Nam_tu\TTTN\models"
        
        print("Đang load model từ ổ cứng...")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_path, 
            torch_dtype="auto", 
            device_map="auto"
        )
        
        # 2. Cấu hình MongoDB
        USER = "buiminhtai1234"
        PASSWORD = "191104"
        CLUSTER_URL = "cluster0.ydqe2ve.mongodb.net" 
        safe_pass = urllib.parse.quote_plus(PASSWORD)
        self.uri = f"mongodb+srv://{USER}:{safe_pass}@{CLUSTER_URL}/?retryWrites=true&w=majority&appName=test-model"
        
        self.client = MongoClient(self.uri)
        self.db = self.client['iot_project']
        self.collection = self.db['human_behavior']
        print("Trợ lý AI đã sẵn sàng kết nối cơ sở dữ liệu.")

    def _call_ai(self, messages, stream=False):
        text = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)
        
        if stream:
            # Dùng TextStreamer để in trực tiếp
            streamer = TextStreamer(self.tokenizer, skip_prompt=True, skip_special_tokens=True)
            
            # Thay output_ids bằng _ vì chúng ta không cần giữ giá trị trả về
            _ = self.model.generate(
                **inputs, 
                max_new_tokens=512, 
                do_sample=True,
                temperature=0.1,
                top_p=0.9,
                streamer=streamer
            )
            return "" # Streamer đã in rồi nên trả về rỗng
        else:
            # Chế độ bình thường (không stream)
            output_ids = self.model.generate(
                **inputs, 
                max_new_tokens=512, 
                do_sample=True, 
                temperature=0.1
            )
            return self.tokenizer.batch_decode(output_ids, skip_special_tokens=True)[0].split("assistant")[-1].strip()
        
    def _generate_query(self, user_question):
        # Lấy ngày hiện tại hệ thống
        now = datetime.now()
        today_date = now.strftime("%Y-%m-%d")
        now_full = now.strftime("%Y-%m-%dT%H:%M:%S")

        system_prompt = (
            f"BẠN LÀ MÁY CHUYỂN ĐỔI JSON. GIỜ HIỆN TẠI: {now_full}.\n"
            f"NGÀY HÔM NAY: {today_date}.\n"
            "NHIỆM VỤ: Trích xuất thời gian từ câu hỏi và tạo JSON MongoDB.\n"
            "QUY TẮC:\n"
            f"1. Nếu người dùng KHÔNG nói ngày, hãy mặc định dùng ngày hôm nay: {today_date}.\n"
            "2. Nếu người dùng CÓ nói ngày (VD: 03/02, ngày 3 tháng 2), hãy dùng đúng ngày đó.\n"
            "3. LUÔN TRẢ VỀ ĐÚNG ĐỊNH DẠNG: {\"camera_id\": \"CAM_01\", \"timestamp\": {\"$gte\": \"YYYY-MM-DDTHH:mm:ss\", \"$lt\": \"...\"}}\n"
            "4. CHỈ TRẢ VỀ JSON, không giải thích, không văn bản thừa.\n\n"
            "VÍ DỤ:\n"
            "- 'Lúc 16:12 có ai ngồi không?' -> {\"camera_id\": \"CAM_01\", \"timestamp\": {\"$gte\": \"2026-02-05T16:12:00\", \"$lt\": \"2026-02-05T16:13:00\"}}\n"
            "- 'Ngày 03/02 lúc 10 giờ có ai đứng không?' -> {\"camera_id\": \"CAM_01\", \"timestamp\": {\"$gte\": \"2026-02-03T10:00:00\", \"$lt\": \"2026-02-03T11:00:00\"}}"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Chuyển câu sau sang JSON: {user_question}"}
        ]
        
        raw_res = self._call_ai(messages)
        print(f"--- AI RAW RESPONSE: {raw_res} ---")

        try:
            # Làm sạch chuỗi trước khi parse (Xóa các ký tự markdown nếu AI lỡ thêm vào)
                clean_res = re.sub(r'```json|```', '', raw_res).strip()
                
                # Tìm khối { ... }
                match = re.search(r'\{.*\}', clean_res, re.DOTALL)
                if match:
                    json_str = match.group(0)
                    # Thay thế dấu nháy đơn thành nháy đôi để tránh lỗi JSON chuẩn
                    json_str = json_str.replace("'", '"') 
                    return json.loads(json_str)
                return {}
        except Exception as e:
            print(f"Lỗi phân tách JSON: {e}")
            return {}
    def _humanize_response(self, user_question, summary, stream=False):        
        # Chuẩn bị dữ liệu chuỗi để AI không bị khớp khi đọc JSON rỗng
        stat_str = f"""
        - Thời gian: {summary['time_range']['start']} đến {summary['time_range']['end']}
        - Số người đứng (standing): {summary['behaviors'].get('standing', 0)}
        - Số người ngồi (sitting): {summary['behaviors'].get('sitting', 0)}
        - Số người nằm (lying): {summary['behaviors'].get('lying', 0)}
        """
        
        system_prompt = (
            "Bạn là trợ lý ảo báo cáo dữ liệu camera thang máy.\n"
            "Nhiệm vụ: Dựa vào số liệu tôi cung cấp, trả lời câu hỏi của người dùng.\n"
            "QUY TẮC:\n"
            "1. Tuyệt đối không từ chối trả lời. Nếu con số là 0, hãy báo là không ghi nhận được ai.\n"
            "2. Trả lời ngắn gọn, thân thiện.\n"
            "3. Nếu có người nằm (lying > 0), phải cảnh báo an toàn."
        )
        
        user_content = f"Dữ liệu: {stat_str}\nCâu hỏi: {user_question}"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        return self._call_ai(messages, stream=stream)

    def ask(self, user_question, stream=False):
        raw_query = self._generate_query(user_question) 
        query_dict = {}
        
        if isinstance(raw_query, dict) and raw_query:
            query_dict['camera_id'] = raw_query.get('camera_id', 'CAM_01')
            
            if 'timestamp' in raw_query:
                ts = raw_query['timestamp']
                try:
                    if isinstance(ts, dict):
                        # CHUYỂN ĐỔI: Chuyển về datetime rồi cộng 1 giây, sau đó chuyển lại String để khớp DB
                        start_dt = datetime.fromisoformat(str(ts.get('$gte')).replace('Z', ''))
                        # Nếu AI trả về $lt, dùng $lt, nếu không có thì lấy $gte + 1s
                        end_val = ts.get('$lt') or ts.get('$gte')
                        end_dt = datetime.fromisoformat(str(end_val).replace('Z', '')) + timedelta(seconds=1)
                        
                        query_dict['timestamp'] = {
                            "$gte": start_dt.isoformat(),
                            "$lt": end_dt.isoformat()
                        }
                    elif isinstance(ts, str):
                        query_dict['timestamp'] = ts.replace('Z', '')
                except Exception as e:
                    print(f"[Lỗi] Định dạng thời gian: {e}")

        if not query_dict: 
            return "Tôi không xác định được Camera hoặc thời gian bạn cần tra cứu."

        print(f"\n[Hệ thống] Truy vấn thực tế: {query_dict}")

        # 3. Truy xuất và TỔNG HỢP dữ liệu
        # 3. Truy xuất và TỔNG HỢP dữ liệu
        try:
            cursor = self.collection.find(query_dict).sort("timestamp", 1)
            data_found = list(cursor)
            
            if not data_found:
                return "Hệ thống không tìm thấy dữ liệu Camera phù hợp trong khoảng thời gian này."

            summary = {
                "time_range": {
                    "start": str(data_found[0]['timestamp']).split('T')[-1],
                    "end": str(data_found[-1]['timestamp']).split('T')[-1]
                },
                "total_records": len(data_found),
                "behaviors": {}, 
                "warnings": [] 
            }

            for d in data_found:
                ts_short = str(d['timestamp']).split('T')[-1]
                people = d.get("people", [])
                
                for p in people:
                    action = p.get("behavior", "unknown")
                    # Đếm số lượng hành vi
                    summary["behaviors"][action] = summary["behaviors"].get(action, 0) + 1
                    
                    # Nếu có cảnh báo (level: warning) hoặc hành vi nguy hiểm (lying/fallen)
                    if p.get("level") == "warning" or action in ["lying", "fallen"]:
                        msg = f"Lúc {ts_short}: Có người đang {action}"
                        if msg not in summary["warnings"]:
                            summary["warnings"].append(msg)

            # Giới hạn danh sách cảnh báo để AI không bị "loạn"
            summary["warnings"] = summary["warnings"][-5:]

        except Exception as e:
            return f"Lỗi xử lý cấu trúc dữ liệu: {e}"

        # 4. AI Phân tích dựa trên bản tổng hợp
        print(f"[Debug] Dữ liệu gửi cho AI phản hồi: {summary}") # Xem summary có rỗng không
        print("\nAI Agent: ", end="", flush=True) 
        return self._humanize_response(user_question, summary, stream=stream)