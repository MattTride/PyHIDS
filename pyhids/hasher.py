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
        return None

    try:
        hasher = hashlib.new(algorithm)
    except ValueError:
        #用户上传了我们不知道的哈希算法
        raise ValueError(f"未知的哈希算法：{algorithm}")

    try:
        with path.open("rb") as f:
            # ↑ with ... as f: 是"上下文管理器"语法。
            #   效果：进入 with 块时打开文件，退出时（无论正常还是异常）
            #   自动关闭文件。相当于 Java 的 try-with-resources。
            #
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
    except (PermissionError, OSError):
        return None

    return hasher.hexdigest()

if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else __file__
    # ↑ sys.argv 是命令行参数列表。
    #   运行 `python -m pyhids.hasher /etc/hosts` 时：
    #     sys.argv[0] = "pyhids.hasher"（模块名）
    #     sys.argv[1] = "/etc/hosts"（我们传的参数）
    #
    #   这行是"三元表达式"：条件成立取前面，不成立取后面。
    #   含义："如果有命令行参数，就哈希用户指定的文件；否则哈希当前文件（__file__）"
    #
    #   __file__ 是 Python 的内置变量，指向当前这个 .py 文件的路径。

    digest = hash_file(target)
    print(f"{digest}   {target}")
