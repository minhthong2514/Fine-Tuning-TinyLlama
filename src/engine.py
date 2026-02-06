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
        self.model_path = "/home/minhthong/Desktop/Chatbot/models"
        
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
        total_warn = summary.get('total_warnings', 0)
        start_time = summary['time_range']['start']
        end_time = summary['time_range']['end']
        warning_details = "\n".join([f"- {w}" for w in summary.get('warnings', [])])

        # ÉP TRẠNG THÁI NGAY TRONG PYTHON
        status_text = "CẢNH BÁO NGUY HIỂM" if total_warn > 0 else "AN TOÀN"
        event_text = f"Phát hiện {total_warn} đối tượng có hành vi nằm bất thường (lying)" if total_warn > 0 else "Không có sự cố"
        action_text = "YÊU CẦU KIỂM TRA CAMERA VÀ HIỆN TRƯỜNG NGAY LẬP TỨC!" if total_warn > 0 else "Tiếp tục giám sát."

        system_prompt = (
            "BẠN LÀ MÁY PHÁT NGÔN CỦA HỆ THỐNG GIÁM SÁT AN NINH.\n"
            "NHIỆM VỤ: Trình bày dữ liệu dưới đây thành báo cáo đúng định dạng.\n"
            "QUY TẮC CỐT LÕI:\n"
            "1. Tuyệt đối KHÔNG thay đổi kết quả 'Trạng thái' và 'Cụ thể sự cố' mà hệ thống đã cung cấp.\n"
            "2. KHÔNG được phép kết luận 'An toàn' nếu hệ thống ghi nhận có hành vi 'lying'.\n"
            "3. Không sử dụng từ 'nói dối' cho 'lying', phải dùng từ 'nằm bất thường'.\n"
            "4. Định dạng báo cáo phải gồm 4 mục: [Trạng thái an ninh], [Cụ thể sự cố], [Mốc thời gian], [Kiểm tra khẩn cấp]."
        )

        # Cấu trúc lại User Content để AI không còn đường thoái thác
        user_content = (
            f"DỮ LIỆU ĐÃ XỬ LÝ:\n"
            f"- TRẠNG THÁI: {status_text}\n"
            f"- SỰ CỐ: {event_text}\n"
            f"- CHI TIẾT THỜI GIAN: {start_time} đến {end_time}\n"
            f"- DANH SÁCH ĐỐI TƯỢNG:\n{warning_details}\n\n"
            f"Hãy trả lời câu hỏi '{user_question}' theo đúng 4 mục sau:\n"
            f"1. [Trạng thái an ninh]: {status_text}\n"
            f"2. [Cụ thể sự cố]: {event_text} trong khoảng thời gian {start_time} - {end_time}.\n"
            f"3. [Mốc thời gian]: Liệt kê chính xác các mốc thời gian của từng đối tượng từ danh sách chi tiết.\n"
            f"4. [Kiểm tra khẩn cấp]: {action_text}"
        )

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
                        start_dt = datetime.fromisoformat(str(ts.get('$gte')).replace('Z', ''))
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
        try:
            # Sắp xếp theo thời gian tăng dần để bắt được mốc "bắt đầu" chính xác nhất
            cursor = self.collection.find(query_dict).sort("timestamp", 1)
            data_found = list(cursor)
            
            if not data_found:
                return "Hệ thống không tìm thấy dữ liệu Camera phù hợp trong khoảng thời gian này."

            # Dictionary để quản lý đối tượng: { raw_id: {display_id, first_time, behavior} }
            detected_objects = {}
            person_counter = 0
            last_event_time = None

            summary = {
                "time_range": {
                    "start": str(data_found[0]['timestamp']).split('T')[-1].split('.')[0],
                    "end": str(data_found[-1]['timestamp']).split('T')[-1].split('.')[0]
                },
                "total_records": len(data_found),
                "warnings": [] 
            }

            for d in data_found:
                ts_short = str(d['timestamp']).split('T')[-1].split('.')[0] # Định dạng HH:mm:ss
                people = d.get("people", [])
                
                for p in people:
                    action = p.get("behavior", "unknown")
                    level = p.get("level", "normal")
                    raw_id = p.get("object_id", p.get("id", "unknown"))
                    
                    # Điều kiện xác định hành vi bất thường/nguy hiểm
                    if action in ["lying", "fallen"] or level == "warning":
                        
                        # Logic xử lý cho đối tượng có ID là 'unknown'
                        # Nếu ID unknown xuất hiện cách lần cuối > 10s, coi là người mới
                        is_new_person = False
                        if raw_id == "unknown":
                            if last_event_time is None:
                                is_new_person = True
                            else:
                                t1 = datetime.strptime(ts_short, "%H:%M:%S")
                                t2 = datetime.strptime(last_event_time, "%H:%M:%S")
                                if (t1 - t2).total_seconds() > 10:
                                    is_new_person = True
                            
                            if is_new_person:
                                # Tạo một ID tạm thời duy nhất cho 'unknown' này để lưu vào dict
                                person_counter += 1
                                current_temp_id = f"temp_idx_{person_counter}"
                                detected_objects[current_temp_id] = {
                                    "display_id": f"Person {person_counter:02d}",
                                    "first_time": ts_short,
                                    "action": action
                                }
                                last_event_time = ts_short
                        
                        # Logic xử lý cho đối tượng có ID cụ thể (không phải unknown)
                        else:
                            if raw_id not in detected_objects:
                                person_counter += 1
                                detected_objects[raw_id] = {
                                    "display_id": f"Person {person_counter:02d}",
                                    "first_time": ts_short,
                                    "action": action
                                }
                                last_event_time = ts_short

            # Chuyển đổi dictionary thành danh sách chuỗi cảnh báo cho AI
            actual_warnings = []
            for info in detected_objects.values():
                actual_warnings.append(f"{info['display_id']} phát hiện {info['action']} lúc {info['first_time']}")

            summary["total_warnings"] = len(actual_warnings)
            summary["warnings"] = actual_warnings

        except Exception as e:
            return f"Lỗi xử lý cấu trúc dữ liệu: {e}"

        # 4. AI Phân tích dựa trên bản tổng hợp
        print(f"[Debug] Dữ liệu gửi cho AI phản hồi: {summary}")
        print("\nAI Agent: \n", end="", flush=True) 
        return self._humanize_response(user_question, summary, stream=stream)