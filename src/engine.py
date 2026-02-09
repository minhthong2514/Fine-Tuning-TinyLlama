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
                temperature=0.2,
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
                temperature=0.2,
                top_p=0.9
            )
            return self.tokenizer.batch_decode(output_ids, skip_special_tokens=True)[0].split("assistant")[-1].strip()
        
    def _generate_query(self, user_question):
        now = datetime.now()
        today_date = now.strftime("%Y-%m-%d")
        now_full = now.strftime("%Y-%m-%dT%H:%M:%S")

        system_prompt = (
            f"BẠN LÀ CHUYÊN VIÊN TRÍCH XUẤT DỮ LIỆU CAMERA. GIỜ: {now_full}.\n"
            f"NGÀY HÔM NAY: {today_date}.\n"
            "NHIỆM VỤ: Xác định câu hỏi có thuộc phạm vi camera thang máy hay không và tạo JSON.\n\n"
            "DANH SÁCH CÂU HỎI HỢP LỆ (LUÔN TẠO JSON):\n"
            "- Hỏi về tình hình an ninh, báo cáo, sự cố, CẢNH BÁO (warning/alert).\n"
            "- Hỏi về số lượng (có bao nhiêu người, bao nhiêu vụ, bao nhiêu cảnh báo).\n"
            "- Hỏi về hành vi: nằm, ngồi, đứng, ngã, di chuyển trong thang máy.\n"
            "- Các câu hỏi chứa ngày tháng cụ thể.\n\n"
            "DANH SÁCH CÂU HỎI NGOÀI LỀ (TRẢ VỀ error: out_of_scope):\n"
            "- Chào hỏi, thời tiết, kiến thức phổ thông, toán học, hỏi thăm cá nhân, nấu ăn.\n\n"
            "QUY TẮC TRÍCH XUẤT:\n"
            "1. Nếu câu hỏi HỢP LỆ: Trả về JSON {\"camera_id\": \"CAM_01\", \"timestamp\": {\"$gte\": \"...\", \"$lt\": \"...\"}}\n"
            "2. Nếu câu hỏi NGOÀI LỀ: Trả về JSON {\"error\": \"out_of_scope\"}\n"
            "3. CHỈ TRẢ VỀ JSON, không giải thích."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Chuyển câu sau sang JSON: {user_question}"}
        ]
        
        raw_res = self._call_ai(messages)
        print(f"--- AI RAW RESPONSE: {raw_res} ---")

        try:
            # Làm sạch Markdown triệt để
            clean_res = re.sub(r'```json|```', '', raw_res).strip()
            clean_res = re.sub(r'ISODate\("([^"]+)"\)', r'"\1"', clean_res)
            # Tìm khối { ... }
            match = re.search(r'\{.*\}', clean_res, re.DOTALL)
            if match:
                json_str = match.group(0).replace("'", '"')
                result = json.loads(json_str)
                # Ép kiểu result phải là dict
                return result if isinstance(result, dict) else {"error": "invalid_format"}
            
            # Nếu AI trả về text "out_of_scope" mà không có ngoặc nhọn
            if "out_of_scope" in clean_res.lower():
                return {"error": "out_of_scope"}
                
            return {"error": "no_json_found"}
        except Exception as e:
            print(f"Lỗi phân tách JSON: {e}")
            return {"error": "parse_exception"}
        
    def _humanize_response(self, user_question, summary, stream=False):
        raw_date = summary.get('date', 'N/A')
        # Ép định dạng ngày để AI không tự ý lấy năm 2023
        formatted_date = "/".join(raw_date.split("-")[::-1])
        start_t = summary['time_range']['start']
        end_t = summary['time_range']['end']
        context_data = "\n".join(summary['details'])
        
        is_urgent = summary.get('is_emergency', False)
        status_label = "CẢNH BÁO NGUY HIỂM / BẤT THƯỜNG" if is_urgent else "BÌNH THƯỜNG"

        system_prompt = (
            "BẠN LÀ TRỢ LÝ GIÁM SÁT AN NINH THANG MÁY - NGHIÊM TÚC VÀ CHÍNH XÁC.\n"
            "NHIỆM VỤ: Lập báo cáo dựa trên dữ liệu camera. Tuyệt đối không được mâu thuẫn với dữ liệu.\n"
            # Thêm dòng ràng buộc thời gian ngay tại đây
            f"LƯU Ý THỜI GIAN: Hôm nay là ngày {formatted_date}. Tuyệt đối KHÔNG dùng các năm cũ (2023, 2024).\n"
            f"LOGIC BẮT BUỘC:\n"
            f"1. Nếu trạng thái hệ thống là '{status_label}', bạn KHÔNG ĐƯỢC PHÉP viết là 'bình thường'.\n"
            "2. Mục 4 (Kiểm tra khẩn cấp) KHÔNG ĐƯỢC nói 'không có hành vi bất thường' nếu ở mục 3 đã liệt kê sự cố.\n"
            "3. Loại bỏ hoàn toàn các phần 'THAM KHẢO' hay 'KHÓA TIẾP THEO' rườm rà. Chỉ tập trung vào 4 mục chính.\n"
            "4. Ngôn ngữ phải quyết liệt, yêu cầu con người can thiệp khi có sự cố."
        )

        user_content = (
            f"HÃY LẬP BÁO CÁO CHO SỰ CỐ SAU (YÊU CẦU TRUNG THỰC VỚI DỮ LIỆU):\n"
            f"- TRẠNG THÁI XÁC ĐỊNH: {status_label}\n"
            f"- DỮ LIỆU CHI TIẾT: \n{context_data}\n"
            # Ghi rõ nhãn để AI bốc dữ liệu cho chuẩn
            f"- NGÀY GHI NHẬN: {formatted_date}\n"
            f"- KHUNG GIỜ TRUY XUẤT: {start_t} - {end_t}\n\n"
            "HÃY VIẾT BÁO CÁO THEO CẤU TRÚC 4 MỤC:\n"
            "1. [Trạng thái an ninh]: Phải ghi rõ là CẢNH BÁO NGUY HIỂM nếu có sự cố.\n"
            f"2. [Mốc thời gian]: Ghi chính xác Ngày {formatted_date} và khung giờ {start_t} - {end_t}.\n"
            "3. [Cụ thể sự cố/thông tin]: Diễn giải chi tiết hành vi của từng người dựa trên dữ liệu chi tiết.\n"
            "4. [Kiểm tra khẩn cấp]: Phải yêu cầu nhân viên an ninh đến hiện trường ngay lập tức."
        )

        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}]
        return self._call_ai(messages, stream=stream)

    def ask(self, user_question, stream=False):
        # 1. Lấy Query từ AI
        query_dict = self._generate_query(user_question)

        # CHỐT CHẶN AN TOÀN: Đảm bảo query_dict luôn là Dictionary
        if not isinstance(query_dict, dict):
            # Nếu lỡ là chuỗi chứa out_of_scope thì xử lý luôn
            if isinstance(query_dict, str) and "out_of_scope" in query_dict:
                query_dict = {"error": "out_of_scope"}
            else:
                query_dict = {"error": "unknown_type"}

        # 2. Xử lý trường hợp câu hỏi ngoài phạm vi
        if query_dict.get("error") == "out_of_scope":
            return ("Tôi là trợ lý AI giám sát camera thang máy. Tôi chỉ có thể trả lời các câu hỏi về: "
                    "\n- Tình hình an ninh/sự cố."
                    "\n- Các hành vi bất thường (nằm, ngồi, ngã)."
                    "\n- Kiểm tra dữ liệu theo ngày/giờ cụ thể."
                    "\n\nVui lòng đặt câu hỏi liên quan đến các mục trên.")
        
        # Nếu không có query hợp lệ để tìm DB
        if "timestamp" not in query_dict:
            return "Câu hỏi của bạn không chứa mốc thời gian cụ thể hoặc không đủ dữ liệu để truy xuất."
        
        # --- TIẾP TỤC LOGIC TRUY VẤN DB CỦA BẠN ---
        translate_behavior = {
            "sitting": "đang ngồi",
            "standing": "đang đứng",
            "lying": "đang nằm trên sàn",
            "fallen": "bị ngã",
            "unknown": "không xác định"
        }

        try:
            cursor = self.collection.find(query_dict).sort("timestamp", 1)
            data_found = list(cursor)
            
            if not data_found:
                return f"Hệ thống không tìm thấy dữ liệu camera trong khoảng thời gian được yêu cầu vào ngày {query_dict.get('timestamp', {}).get('$gte', '').split('T')[0]}."

            # 5. Xử lý logic gom nhóm dữ liệu (Người 01, Người 02...)
            record_date = str(data_found[0]['timestamp']).split('T')[0]
            warns_info = {} 

            for d in data_found:
                ts_short = str(d['timestamp']).split('T')[-1].split('.')[0]
                people = d.get("people", [])
                
                for p in people:
                    p_id = p.get("person_id")
                    behavior = p.get("behavior", "unknown")
                    level = p.get("level", "normal")

                    if p_id not in warns_info:
                        warns_info[p_id] = {
                            "first_seen": ts_short,
                            "warning_start": ts_short if level == "warning" else None,
                            "last_seen": ts_short,
                            "behavior": behavior,
                            "is_warning": (level == "warning")
                        }
                    else:
                        warns_info[p_id]["last_seen"] = ts_short
                        if level == "warning":
                            warns_info[p_id]["is_warning"] = True
                            if warns_info[p_id]["warning_start"] is None:
                                warns_info[p_id]["warning_start"] = ts_short

            # 6. Tạo chuỗi chi tiết cho từng đối tượng để gửi cho AI Humanize
            actual_details = []
            for p_id in sorted(warns_info.keys()):
                info = warns_info[p_id]
                vi_behavior = translate_behavior.get(info['behavior'], info['behavior'])
                
                if info['warning_start'] == info['first_seen'] or info['warning_start'] is None:
                    # Trường hợp bất thường ngay từ đầu hoặc không có cảnh báo
                    detail = f"Người {p_id:02d} ({vi_behavior}): Ghi nhận từ {info['first_seen']} đến {info['last_seen']}."
                else:
                    # Trường hợp ngồi/nằm một lúc sau mới tính là bất thường (quy tắc 5s)
                    detail = f"Người {p_id:02d} ({vi_behavior}): Xuất hiện từ {info['first_seen']}, chính thức xác định bất thường từ {info['warning_start']} đến {info['last_seen']}."
                
                actual_details.append(detail)

            # 7. Đóng gói tóm tắt (Summary)
            summary = {
                "date": record_date,
                "time_range": {
                    "start": str(data_found[0]['timestamp']).split('T')[-1].split('.')[0],
                    "end": str(data_found[-1]['timestamp']).split('T')[-1].split('.')[0]
                },
                "details": actual_details,
                "is_emergency": any(item['is_warning'] for item in warns_info.values())
            }

        except Exception as e:
            print(f"Lỗi hệ thống trong hàm ask: {e}")
            return "Đã xảy ra lỗi trong quá trình truy xuất dữ liệu an ninh. Vui lòng thử lại sau."
        
        print(f"[Debug] Dữ liệu gửi cho AI phản hồi: {summary}")
        print("\nAI Agent: \n", end="", flush=True) 
        return self._humanize_response(user_question, summary, stream=stream)
