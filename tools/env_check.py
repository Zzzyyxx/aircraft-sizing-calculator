# -*- coding: utf-8 -*-
"""
环境检查 · Environment check
=============================
检查 Python 版本、tkinter 可用性、程序文件与计算内核是否就绪。
Check the Python version, tkinter availability, program files and the core.

用法 / Usage:
    python tools\\env_check.py

输出同时写入 环境报告.txt（与本程序同级目录）。
The report is also written to 环境报告.txt next to this package.
"""

import os
import platform
import struct
import sys
import traceback
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIN_VER = (3, 9)

REQUIRED = [
    ("aircraft_sizing_calculator.py", "主程序 / main application"),
    ("calc_core.py", "计算内核 / calculation core"),
    ("launch_calculator.bat", "启动脚本 / launcher"),
    ("check_environment.bat", "环境检查入口 / check entry"),
    ("install_environment.bat", "环境安装入口 / setup entry"),
    ("README.md", "说明书 / manual"),
]

try:                                        # 控制台编码兜底，避免 GBK 下崩
    sys.stdout.reconfigure(errors="replace")
except Exception:                           # noqa: BLE001
    pass

_LINES = []


def out(text=""):
    """同时打到屏幕和报告缓冲 / print to console and to the report buffer."""
    print(text)
    _LINES.append(text)


def head(title):
    out()
    out("=" * 60)
    out("  " + title)
    out("=" * 60)


def _dw(text):
    """显示宽度：中日韩全角算 2 列 / display width, CJK counts as two columns."""
    import unicodedata
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text)


def item(ok, label, detail=""):
    mark = "[OK]" if ok is True else ("[!!]" if ok is None else "[X ]")
    out("  %s %s%s" % (mark, label, " " * max(2, 14 - _dw(label)) + detail))
    return ok is not False


def check_python():
    head("1. Python 解释器 / Interpreter")
    ver = sys.version_info
    ok = (ver.major, ver.minor) >= MIN_VER
    item(ok, "版本 / version",
         "%d.%d.%d  (%s)" % (ver.major, ver.minor, ver.micro,
                             "满足 %d.%d+" % MIN_VER if ok else
                             "需要 %d.%d 及以上" % MIN_VER))
    item(True, "路径 / path", sys.executable)
    item(True, "位数 / bits", "%d-bit" % (struct.calcsize("P") * 8))
    item(True, "系统 / system", "%s %s" % (platform.system(), platform.release()))
    return ok


def check_tkinter():
    head("2. 图形界面依赖 / GUI dependency")
    try:
        import tkinter
        from tkinter import ttk  # noqa: F401
    except Exception as exc:                # noqa: BLE001
        item(False, "tkinter", "导入失败 / import failed: %s" % exc)
        out()
        out("  tkinter 是 Python 自带模块，缺失通常是安装时没勾选 tcl/tk。")
        out("  tkinter ships with Python; a missing copy usually means tcl/tk")
        out("  was unchecked during installation.")
        out("  修复 / fix: 重跑安装包 -> Modify -> 勾选 tcl/tk and IDLE")
        return False

    item(True, "tkinter", "Tk %s" % tkinter.TkVersion)
    try:
        item(True, "Tcl/Tk 补丁", str(tkinter.Tcl().eval("info patchlevel")))
    except Exception:                       # noqa: BLE001
        item(None, "Tcl/Tk 补丁", "读取失败（不影响运行）")

    try:
        root = tkinter.Tk()
        root.withdraw()
        scale = root.winfo_fpixels("1i") / 96.0
        screen = "%dx%d" % (root.winfo_screenwidth(), root.winfo_screenheight())
        root.destroy()
        item(True, "窗口测试 / window", "可以创建 Tk 窗口")
        item(True, "分辨率 / screen", screen)
        item(True, "DPI 缩放 / scale", "%.0f%%" % (scale * 100))
        return True
    except Exception as exc:                # noqa: BLE001
        item(False, "窗口测试 / window", "无法创建窗口: %s" % exc)
        return False


def check_files():
    head("3. 程序文件 / Program files")
    ok_all = True
    for name, desc in REQUIRED:
        path = os.path.join(ROOT, name)
        if os.path.exists(path):
            size = os.path.getsize(path) / 1024.0
            item(True, name, "%.1f KB  ·  %s" % (size, desc))
        else:
            item(False, name, "缺失 / missing  ·  %s" % desc)
            ok_all = False
    return ok_all


def check_core():
    head("4. 计算内核 / Calculation core")
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    try:
        import calc_core as CC
    except Exception:                       # noqa: BLE001
        item(False, "导入 / import", "calc_core 无法导入")
        out()
        out(traceback.format_exc())
        return False

    item(True, "导入 / import", "calc_core 就绪")
    try:
        n_empty = sum(len(v.get("points") or []) for v in CC.DB["emptyFrac"].values())
        n_ld = sum(len(v.get("points") or []) for v in CC.DB["ld"].values())
        item(True, "统计库 / database",
             "%d 组布局 · 空重分数 %d 点 · 升阻比 %d 点"
             % (len(CC.DB["emptyFrac"]), n_empty, n_ld))
        item(True, "动力库 / power", "%d 类动力" % len(CC.DB["power"]))
    except Exception as exc:                # noqa: BLE001
        item(False, "统计库 / database", str(exc))
        return False

    try:
        cfg = {"power": "turboprop", "layout": "normal", "category": "manned",
               "config": "fixedwing",
               "inp": {"WPL": 1500.0, "V": 500.0, "R": 1500.0, "h": 8000.0,
                       "tHover": 20.0, "Vc": 3.0, "NB": 6, "Dr": 0.9},
               "des": {}}
        r = CC.compute_core(cfg)
        item(True, "自检算例 / smoke test",
             "1500 kg / 500 km/h / 1500 km  ->  W_TO %.0f kg，%d 轮迭代"
             % (r["Wto"], len(r.get("iters") or [])))
    except Exception as exc:                # noqa: BLE001
        item(False, "自检算例 / smoke test", "算例失败: %s" % exc)
        return False
    return True


def main(argv=None):
    out("飞机总体参数计算器 · 环境检查")
    out("Aircraft Sizing Calculator - environment check")
    out("时间 / time: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    results = [check_python(), check_tkinter(), check_files(), check_core()]

    head("结论 / Verdict")
    if all(results):
        out("  环境可用，双击 launch_calculator.bat 即可运行。")
        out("  Environment is ready - double-click launch_calculator.bat to run.")
        code = 0
    else:
        out("  环境不完整，请按上面 [X] 的提示处理，或运行 install_environment.bat。")
        out("  Environment is incomplete - follow the [X] items above, or run")
        out("  install_environment.bat (one-click setup).")
        code = 1

    report = os.path.join(ROOT, "环境报告.txt")
    try:
        with open(report, "w", encoding="utf-8") as f:
            f.write("\n".join(_LINES) + "\n")
        out()
        out("  报告已保存 / report saved: " + report)
    except Exception:                       # noqa: BLE001
        pass

    out()
    return code


if __name__ == "__main__":
    sys.exit(main())
