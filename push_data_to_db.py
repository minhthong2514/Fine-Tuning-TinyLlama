import json
import urllib.parse
from pymongo import MongoClient
from datetime import datetime

# Cấu hình kết nối
USER = "boybit2504_db_user"
PASSWORD = "abc123456"
CLUSTER_URL = "test-model.xawqqta.mongodb.net"
uri = f"mongodb+srv://{USER}:{urllib.parse.quote_plus(PASSWORD)}@{CLUSTER_URL}/?retryWrites=true&w=majority"

client = MongoClient(uri)
db = client['ElevatorDB']
col = db['elevator_logs']

# Đọc và convert timestamp sang kiểu Date của MongoDB
with open('history_data.json', 'r') as f:
    raw_data = json.load(f)
    for item in raw_data:
        item['timestamp'] = datetime.fromisoformat(item['timestamp'])

# Đẩy dữ liệu
col.insert_many(raw_data)
print("Đã hoàn tất đưa dữ liệu lịch sử tháng 01/2026 lên Cloud!")