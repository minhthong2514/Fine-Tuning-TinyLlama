from pymongo import MongoClient
from datetime import datetime

# Thay bằng chuỗi Connection String của bạn
uri = "mongodb+srv://admin:123456@cluster0.xxx.mongodb.net/"
client = MongoClient(uri)

db = client['ElevatorDB']
collection = db['elevator_logs']

# Dữ liệu mẫu
sample_data = [
    {"device_id": "T1", "voltage": 218, "current": 10.5, "floor": 3, "status": "Moving", "timestamp": datetime.now()},
    {"device_id": "T2", "voltage": 225, "current": 15.2, "floor": 1, "status": "Idle", "timestamp": datetime.now()},
    {"device_id": "T2", "voltage": 210, "current": 11.0, "floor": 8, "status": "Moving", "timestamp": datetime.now()},
]

collection.insert_many(sample_data)
print("✅ Đã nạp dữ liệu mẫu thành công!")