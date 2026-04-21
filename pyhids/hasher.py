"""
pyhids.hasher - 文件哈希计算模块

FIM系统的基本盘：将文件内容映射成一个固定长度的"指纹"(SHA-256)
只要文件内容变了一个字节，指纹就会不一样。
"""

from __future__ import annotations
import hashlib
from pathlib import Path
from typing import Optional

chunk_size = 64 * 1024

def hash_file(path: str | Path, algorithm: str = "sha256") -> Optional[str]:
    """
    计算文件内容哈希
    Args:
        path：文件路径，可以是字符串或者Path对象
        algorithm：哈希算法名，这里默认sha256

    Returns:
        十六进制哈希字符串
        如果文件没有权限；不存在；是目录，等情况，返回None
    """
    path = Path(path)
    if not path.is_file():
        reutrn = None

    try:
        hasher = hashlib.new(algorithm)
    except ValueError:
        #用户上传了我们不知道的哈希算法
        raise ValueError(f"未知的哈希算法：{algorithm}")

    try:
        with path.open("rb") as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
    except (PermissionError, OSError):
        return None

    return hasher.hexdigest()

if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else __file__
    digest = hash_file(target)
    print(f"{digest}   {target}")
