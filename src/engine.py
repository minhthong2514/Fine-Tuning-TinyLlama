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
                temperature=0.4
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
        count = summary.get('total_count', 0)
        details = "\n".join([f"- {d}" for d in summary.get('details', [])])
        intent = summary.get('user_intent')
        
        # Format lại ngày từ YYYY-MM-DD sang DD/MM/YYYY
        raw_date = summary.get('date', 'N/A')
        formatted_date = "/".join(raw_date.split("-")[::-1])
        time_info = f"Ngày {formatted_date}, Thời gian: {summary['time_range']['start']} - {summary['time_range']['end']}"

        if intent in ["sitting", "standing"] and not summary['is_emergency']:
            status = "BÌNH THƯỜNG"
            event_text = f"Ghi nhận {count} người đang {intent}"
            action_text = "Không có dấu hiệu bất thường. Tiếp tục theo dõi."
        else:
            status = "CẢNH BÁO NGUY HIỂM"
            event_text = f"Phát hiện {count} trường hợp hành vi {intent if intent != 'warning' else 'bất thường'}"
            action_text = "YÊU CẦU KIỂM TRA CAMERA VÀ ĐẾN HIỆN TRƯỜNG NGAY!"

        system_prompt = (
            "BẠN LÀ TRỢ LÝ GIÁM SÁT CAMERA CHUYÊN NGHIỆP.\n"
            "NHIỆM VỤ: Trình bày báo cáo dựa trên dữ liệu được cung cấp.\n"
            "QUY TẮC MỤC 2:\n"
            "Mục '[Mốc thời gian]' phải hiển thị thông tin Ngày và Khoảng giờ ở dòng đầu tiên, "
            "sau đó mới xuống dòng để liệt kê chi tiết từng Person.\n"
        )

        user_content = (
            f"Dữ liệu: {event_text}, Trạng thái: {status}\n"
            f"Thời gian tổng quát: {time_info}\n"
            f"Chi tiết từng người:\n{details}\n"
            f"Câu hỏi: {user_question}\n"
            f"Hãy xuất báo cáo theo mẫu sau:\n"
            f"1. [Trạng thái an ninh]: {status}\n"
            f"2. [Mốc thời gian]: {time_info}\n"
            f"3. [Cụ thể sự cố/thông tin]: {event_text}\n{details}\n"
            f"4. [Kiểm tra khẩn cấp]: {action_text}"
        )

        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}]
        return self._call_ai(messages, stream=stream)

    def ask(self, user_question, stream=False):
        translate_behavior = {
            "sitting": "đang ngồi",
            "standing": "đang đứng",
            "lying": "đang nằm trên sàn",
            "fallen": "bị ngã",
            "unknown": "không xác định"
        }        
        
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
                        query_dict['timestamp'] = {"$gte": start_dt.isoformat(), "$lt": end_dt.isoformat()}
                    elif isinstance(ts, str):
                        query_dict['timestamp'] = ts.replace('Z', '')
                except Exception as e: print(f"Lỗi: {e}")

        target_behavior = None
        if "ngồi" in user_question.lower() or "sitting" in user_question.lower():
            target_behavior = "sitting"
        elif "đứng" in user_question.lower() or "standing" in user_question.lower():
            target_behavior = "standing"
        elif "nằm" in user_question.lower() or "lying" in user_question.lower():
            target_behavior = "lying"

        try:
            cursor = self.collection.find(query_dict).sort("timestamp", 1)
            data_found = list(cursor)
            if not data_found: return "Không tìm thấy dữ liệu."

            # Lấy ngày từ bản ghi đầu tiên (VD: 2026-02-05)
            record_date = str(data_found[0]['timestamp']).split('T')[0]
            
            warnings_map = {} 
            for d in data_found:
                ts_short = str(d['timestamp']).split('T')[-1].split('.')[0]
                people = d.get("people", [])
                for p in people:
                    p_id = p.get("person_id")
                    level = p.get("level", "normal")
                    behavior = p.get("behavior", "unknown")

                    # Logic lọc target_behavior giữ nguyên
                    if target_behavior:
                        if behavior == target_behavior and p_id not in warnings_map:
                            warnings_map[p_id] = {"time": ts_short, "behavior": behavior, "level": level}
                    else:
                        if level == "warning" and p_id not in warnings_map:
                            warnings_map[p_id] = {"time": ts_short, "behavior": behavior, "level": level}

            actual_results = []
            for p_id in sorted(warnings_map.keys()):
                info = warnings_map[p_id]
                # DỊCH TẠI ĐÂY: Chuyển behavior sang tiếng Việt
                vi_behavior = translate_behavior.get(info['behavior'], info['behavior'])
                actual_results.append(f"Người {p_id:02d} - {vi_behavior} lúc {info['time']}")

            # Cập nhật intent tiếng Việt để AI báo cáo ở mục 3
            vi_intent = translate_behavior.get(target_behavior, "bất thường") if target_behavior else "bất thường"

            summary = {
                "date": record_date,
                "user_intent": vi_intent, # Gửi intent đã dịch
                "time_range": {
                    "start": str(data_found[0]['timestamp']).split('T')[-1].split('.')[0],
                    "end": str(data_found[-1]['timestamp']).split('T')[-1].split('.')[0]
                },
                "total_count": len(actual_results),
                "details": actual_results,
                "is_emergency": any(item['level'] == 'warning' for item in warnings_map.values())
            }

        except Exception as e:
            return f"Lỗi xử lý: {e}"
        print(f"[Debug] Dữ liệu gửi cho AI phản hồi: {summary}")
        print("\nAI Agent: \n", end="", flush=True) 
        return self._humanize_response(user_question, summary, stream=stream)
