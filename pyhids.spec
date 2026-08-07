# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置。

构建：pyinstaller pyhids.spec --noconfirm
产物：dist/PyHIDS.app（macOS）/ dist/PyHIDS/（其他平台）
"""
import sys

from PyInstaller.utils.hooks import collect_submodules

VERSION = "1.2.0"

# uvicorn 用字符串按名字动态 import 它的 loop / protocol 实现，静态分析看不见，
# 必须整包收进来；watchdog 同理（不同平台用不同的 observer 后端）。
hidden = collect_submodules("uvicorn") + collect_submodules("watchdog")

a = Analysis(
    ["launcher.py"],
    pathex=[],
    binaries=[],
    # App 首次启动要把这份默认配置复制到用户数据目录，必须打进包里
    datas=[("config/watchlist.default.yaml", "config")],
    hiddenimports=hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=["pytest", "PyInstaller"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PyHIDS",
    debug=False,
    strip=False,
    upx=False,
    # False = 不弹终端窗口。从终端运行内部二进制时 stdout 仍然正常输出，
    # 所以 `PyHIDS.app/Contents/MacOS/PyHIDS check` 这种 CLI 用法不受影响。
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="PyHIDS",
)

# BUNDLE 只在 macOS 上有意义（.app 是 macOS 特有的目录结构）。
# Windows / Linux 上产物就是 COLLECT 出来的 dist/PyHIDS/ 目录。
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="PyHIDS.app",
        icon=None,
        bundle_identifier="com.matttride.pyhids",
        version=VERSION,
        info_plist={
            "CFBundleName": "PyHIDS",
            "CFBundleDisplayName": "PyHIDS",
            "CFBundleShortVersionString": VERSION,
            "CFBundleVersion": VERSION,
            "NSHighResolutionCapable": True,
            # 后台没有窗口，但保留 Dock 图标，用户才有地方退出它
            "LSUIElement": False,
        },
    )
