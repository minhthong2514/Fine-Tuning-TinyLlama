import json
import random
from datetime import datetime, timedelta

# --- Config ---
num_samples = 500

ratios = {
    "valid": 0.65,
    "missing": 0.2,
    "out_of_scope": 0.1,
    "edge_case": 0.05
}

# System prompt theo template Vistral
SYSTEM_PROMPT = (
    "Bạn là chuyên viên phân tích dữ liệu và kiểm toán năng lượng cho hệ thống IoT "
    "sử dụng trong thang máy. Bạn chỉ phân tích dựa trên dữ liệu được cung cấp, "
    "không bịa số liệu. Luôn trả về kết quả dưới dạng JSON đúng cấu trúc: "
    "{\"dow\":..., \"KPIs\":..., \"result\":...}."
)

devices = ["M1", "M2", "M3"]

# helper tạo dữ liệu đo lường
def generate_measurement(device, base_kwh=100):
    times = ["04:03:00","05:00:00","06:00:00"]
    if device == "M1":
        E5 = [round(base_kwh + i*random.uniform(0.5,1.5),1) for i in range(3)]
        return [
            {
                "time": t,
                "E1": round(random.uniform(10,15),1),
                "E2": 220,
                "E3": round(random.uniform(2,3),1),
                "E4": 0.95,
                "E5": k
            } for t,k in zip(times,E5)
        ]
    else:  # M2 or M3
        E5 = [round(base_kwh + i*random.uniform(0.5,1.5),1) for i in range(3)]
        return [
            {
                "time": t,
                "E1": round(random.uniform(10,15),1),
                "E2": round(random.uniform(10,15),1),
                "E3": round(random.uniform(10,15),1),
                "E4": 220,
                "E5": 221,
                "E6": 222,
                "E7": round(random.uniform(2,3),1),
                "E8": 0.95,
                "E9": round(random.uniform(2,3),1),
                "E10": 0.96,
                "E11": round(random.uniform(2,3),1),
                "E12": 0.97,
                "E13": round(sum([random.uniform(2,3) for _ in range(3)]),1),
                "E14": k
            } for t,k in zip(times,E5)
        ]

# câu hỏi mẫu
valid_questions = [
    "Cho tôi biết điện năng tiêu thụ trong khung giờ thấp điểm ban đêm.",
    "Tính tổng điện năng tiêu thụ từ 00:00 đến 04:00 hôm nay.",
    "Khung giờ ban đêm tiêu thụ bao nhiêu kWh?",
    "Hãy phân tích điện năng tiêu thụ M1 trong giờ thấp điểm.",
    "Tính lượng điện năng tiêu thụ của thiết bị này từ 04:00 đến 05:00."
]

missing_questions = [
    "Tính điện năng tiêu thụ hôm qua.",
    "Cho tôi báo cáo tiêu thụ điện năng.",
    "Đánh giá điện năng M2.",
    "Hãy báo cáo điện năng tiêu thụ.",
    "Điện năng tiêu thụ của M3?"
]

out_of_scope_questions = [
    "Hôm nay trời mưa thế nào?",
    "Tình hình giao thông ở Hà Nội?",
    "Thời tiết hôm nay ra sao?",
    "Mua vé máy bay thế nào?",
    "Tôi muốn nghe nhạc."
]

edge_case_questions = [
    "Tính điện năng tiêu thụ từ 03:59 đến 04:03.",
    "Phân tích chủ nhật giờ cao điểm.",
    "Tổng điện năng M3 pha A/B/C.",
    "Kiểm tra dữ liệu M2 với số liệu thiếu.",
    "Điện năng trong giờ lệch khung cao điểm."
]

# phân phối số lượng
num_valid = int(num_samples * ratios["valid"])
num_missing = int(num_samples * ratios["missing"])
num_out = int(num_samples * ratios["out_of_scope"])
num_edge = num_samples - (num_valid + num_missing + num_out)

samples = []

# Ngày bắt đầu
start_date = datetime(2026,2,2)

def weekday_str(date_obj):
    return ["Thứ Hai","Thứ Ba","Thứ Tư","Thứ Năm","Thứ Sáu","Thứ Bảy","Chủ Nhật"][date_obj.weekday()]

def create_result_text(device, measurements):
    if device == "M1":
        return "; ".join(
            [f"Dòng điện: {m['E1']} A; Điện áp: {m['E2']} V; Công suất tức thời: {m['E3']} kW; "
             f"Hệ số công suất: {m['E4']}; Điện năng tiêu thụ: {m['E5']} kWh" for m in measurements]
        )
    else:
        return "; ".join(
            [f"Dòng điện pha A/B/C: {m['E1']}/{m['E2']}/{m['E3']} A; "
             f"Điện áp pha A/B/C: {m['E4']}/{m['E5']}/{m['E6']} V; "
             f"Công suất tức thời pha A/B/C: {m['E7']}/{m['E9']}/{m['E11']} kW; "
             f"Hệ số công suất pha A/B/C: {m['E8']}/{m['E10']}/{m['E12']}; "
             f"Tổng công suất: {m['E13']} kW; "
             f"Điện năng tiêu thụ: {m['E14']} kWh" for m in measurements]
        )

def create_sample(question_type, index):
    device = random.choice(devices)
    current_date = start_date + timedelta(days=index)
    dow = current_date.strftime("%d/%m/%Y") + " là " + weekday_str(current_date)

    if question_type=="valid":
        user_q = random.choice(valid_questions)
        measurements = generate_measurement(device)
        KPIs = measurements
        result = create_result_text(device, measurements)
    elif question_type=="missing":
        user_q = random.choice(missing_questions)
        KPIs = []
        result = "Vui lòng cung cấp thêm thiết bị hoặc khoảng thời gian."
    elif question_type=="out_of_scope":
        user_q = random.choice(out_of_scope_questions)
        KPIs = []
        result = "Câu hỏi không thuộc phạm vi phân tích điện năng."
    else:  # edge_case
        user_q = random.choice(edge_case_questions)
        measurements = generate_measurement(device)
        KPIs = measurements
        result = create_result_text(device, measurements)

    text = (
        f"<s>[INST] <<SYS>>\n"
        f"{SYSTEM_PROMPT}\n"
        f"<</SYS>>\n"
        f"{user_q} [/INST] "
        f"{json.dumps({'dow': dow, 'KPIs': KPIs, 'result': result}, ensure_ascii=False)}"
    )
    return {"text": text}

# generate samples
for i in range(num_valid):
    samples.append(create_sample("valid", i))
for i in range(num_missing):
    samples.append(create_sample("missing", num_valid+i))
for i in range(num_out):
    samples.append(create_sample("out_of_scope", num_valid+num_missing+i))
for i in range(num_edge):
    samples.append(create_sample("edge_case", num_valid+num_missing+num_out+i))

# shuffle
random.shuffle(samples)

# save JSONL
with open("dataset_vistral_final.jsonl","w",encoding="utf-8") as f:
    for s in samples:
        f.write(json.dumps(s, ensure_ascii=False) + "\n")

print("Dataset JSONL ~500 mẫu theo template Vistral (chuẩn hóa dow, KPIs và result) đã tạo xong!")
