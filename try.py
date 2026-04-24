import json

# 1. Python 对象
person = {
    "name": "Tride",
    "age": 22,
    "hobbies": ["coding", "reading"],
    "email": None,
    "is_student": True
}

# 2. 转成 JSON 字符串看看
json_str = json.dumps(person, indent=2, ensure_ascii=False)
print("=== JSON 字符串 ===")
print(json_str)

# 3. 写到文件
with open("data/try_person.json", "w", encoding="utf-8") as f:
    json.dump(person, f, indent=2, ensure_ascii=False)
print("\n✅ 写入完成，去看 data/try_person.json")

# 4. 再读回来
with open("data/try_person.json", "r", encoding="utf-8") as f:
    loaded = json.load(f)

print("\n=== 读回来的数据 ===")
print(loaded)
print("类型:", type(loaded))   # 应该是 dict