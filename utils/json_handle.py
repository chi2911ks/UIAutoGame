import json
import os
class JSONHandler:
    def __init__(self, file_path):
        self.file_path = file_path
        if not os.path.exists(self.file_path):
            open(self.file_path, 'w', encoding='utf-8').write("{}")
    def read_json(self):
        """Đọc dữ liệu từ file JSON"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            print(f"File {self.file_path} không tồn tại.")
            return None
        except json.JSONDecodeError:
            print("Dữ liệu trong file không phải định dạng JSON hợp lệ.")
            return None

    def write_json(self, data):
        """Ghi dữ liệu vào file JSON"""
        try:
            with open(self.file_path, 'w', encoding='utf-8') as file:
                json.dump(data, file, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Đã xảy ra lỗi khi ghi dữ liệu vào file: {e}")

    def update_json(self, key, value):
        """Cập nhật một khóa giá trị trong file JSON"""
        data = self.read_json()
        data.update({key: value})
        self.write_json(data)

    def delete_key(self, key):
        """Xóa một khóa khỏi file JSON"""
        data = self.read_json()
        if data is not None:
            if key in data:
                del data[key]
                self.write_json(data)
            else:
                print(f"Khóa {key} không tồn tại trong file.")
