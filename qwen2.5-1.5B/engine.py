import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import json, re

class ElevatorAI:
    def __init__(self):
        self.model_name = "Qwen/Qwen2.5-1.5B-Instruct"
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name, torch_dtype="auto", device_map="auto"
        )
        self.mock_db = [
            {"device_id": "T1", "voltage": 218, "current": 10.5, "floor": 3},
            {"device_id": "T2", "voltage": 220, "current": 12.1, "floor": 1},
            {"device_id": "T2", "voltage": 221, "current": 11.8, "floor": 5},
        ]

    def _call_ai(self, messages):
        text = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)
        ids = self.model.generate(**inputs, max_new_tokens=256, do_sample=False)
        return self.tokenizer.batch_decode(ids, skip_special_tokens=True)[0].split("assistant")[-1].strip()

    def ask(self, user_question):
        # 1. Tạo Query (Ép AI không giải thích)
        q_msg = [{"role": "system", "content": "Trả về JSON MongoDB cho: device_id, voltage, current, floor. Chỉ trả về JSON."},
                 {"role": "user", "content": user_question}]
        raw_query = self._call_ai(q_msg)
        
        # 2. Extract JSON & Query DB
        try:
            json_str = re.search(r'\{.*\}', raw_query, re.DOTALL).group(0)
            query_dict = json.loads(json_str)
            # Giả lập tìm kiếm đơn giản
            target_id = query_dict.get("device_id") or query_dict.get("query", {}).get("device_id")
            data = [d for d in self.mock_db if d["device_id"] == target_id]
        except:
            data = "Không tìm thấy dữ liệu."

        # 3. Trả lời (Sửa lỗi thuật ngữ kỹ thuật bằng System Prompt)
        a_msg = [{"role": "system", "content": "Bạn là kỹ sư điện. Chú ý: Voltage là Điện áp (V), Current là Dòng điện (A). Trả lời ngắn gọn."},
                 {"role": "user", "content": f"Câu hỏi: {user_question}\nDữ liệu: {data}"}]
        return self._call_ai(a_msg)