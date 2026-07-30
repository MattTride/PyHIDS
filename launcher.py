"""PyInstaller 的入口脚本。

单独一个文件而不是直接指向 pyhids/app.py：打包工具需要一个顶层脚本作为
分析起点，从这里 import 才能让它正确追踪到整个 pyhids 包。
"""
from pyhids.app import main

if __name__ == "__main__":
    main()
