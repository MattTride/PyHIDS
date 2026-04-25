# 模拟 checker 的核心逻辑
old_files = {"passwd", "hosts", "authorized_keys"}
new_files = {"passwd", "hosts", "malware"}

# 被删除的 = 旧有 新无
deleted = old_files - new_files
print(f"被删除: {deleted}")

# 新增的 = 新有 旧无
added = new_files - old_files
print(f"新增: {added}")

# 两边都有 → 候选"修改"（还要进一步对比哈希）
common = old_files & new_files
print(f"两边都有: {common}")