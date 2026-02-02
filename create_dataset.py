import json
import random
from datetime import datetime, timedelta

def generate_history():
    data = []
    start_date = datetime(2026, 1, 1, 0, 0, 0)
    devices = ["T1", "T2", "T3"]

    # Chạy vòng lặp 31 ngày
    for day in range(31):
        # Chạy vòng lặp 24 giờ mỗi ngày
        for hour in range(24):
            current_time = start_date + timedelta(days=day, hours=hour)
            
            for device in devices:
                # Tạo logic dữ liệu giả lập
                voltage = round(random.uniform(210.0, 230.0), 1)
                current = round(random.uniform(10.0, 15.0), 2)
                floor = random.randint(1, 20)
                
                record = {
                    "device_id": device,
                    "voltage": voltage,
                    "current": current,
                    "floor": floor,
                    "timestamp": current_time.isoformat()
                }
                data.append(record)

    # Ghi ra file JSON
    with open('history_data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    print(f"Thành công! Đã tạo {len(data)} bản ghi vào file history_data.json")

if __name__ == "__main__":
    generate_history()