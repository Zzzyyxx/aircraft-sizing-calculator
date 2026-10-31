# -*- coding: utf-8 -*-
"""
一键环境安装 / 修复 · One-click setup
=====================================
先跑一遍环境检查，再针对不满足的项给出可执行的修复动作；
全部通过时可以直接启动计算器。

Run the environment check first, then offer concrete fixes for whatever
fails; when everything passes you can launch the calculator right away.

用法 / Usage:
    python tools\\env_setup.py            # 检查 + 提示修复
    python tools\\env_setup.py --launch   # 检查通过后直接启动
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import env_check                              # noqa: E402  同目录复用检查逻辑

MAIN_APP = "aircraft_sizing_calculator.py"


def _ask(prompt, default=True):
    """Y/n 询问 / yes-no prompt; no input available counts as "no"."""
    tail = "[Y/n]" if default else "[y/N]"
    try:
        ans = input("  %s %s " % (prompt, tail)).strip().lower()
    except EOFError:
        return False
    if not ans:
        return default
    return ans in ("y", "yes", "是", "好")


def _launch():
    exe = sys.executable
    pyw = os.path.join(os.path.dirname(exe), "pythonw.exe")
    runner = pyw if os.path.exists(pyw) else exe
    target = os.path.join(ROOT, MAIN_APP)
    print("  启动 / launching: %s" % target)
    try:
        subprocess.Popen([runner, target], cwd=ROOT)
        return True
    except Exception as exc:                  # noqa: BLE001
        print("  启动失败 / launch failed: %s" % exc)
        return False


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    code = env_check.main()

    env_check.head("修复建议 / How to fix")
    if code == 0:
        env_check.out("  各项检查全部通过，无需要修复的内容。")
        env_check.out("  All checks passed - nothing to repair.")
    else:
        env_check.out("  按上面 [X ] 的条目处理：")
        env_check.out("  Handle the [X ] items above:")
        env_check.out("    · 没有 Python -> 双击 install_environment.bat，或到")
        env_check.out("      https://www.python.org/downloads/windows/ 装 3.12+，")
        env_check.out("      安装时勾选 Add python.exe to PATH。")
        env_check.out("    · 有 Python 但缺 tkinter -> 重跑安装包选 Modify，")
        env_check.out("      勾上 tcl/tk and IDLE 后重装。")
        env_check.out("    · 文件缺失 -> 重新解压完整压缩包。")

    print()
    launched = False
    if code == 0 or "--launch" in argv:
        if _ask("现在启动计算器？ / Launch the calculator now?") or "--launch" in argv:
            launched = _launch()
    if not launched:
        print()
        try:
            input("  按回车退出 / press Enter to close ")
        except EOFError:
            pass
    return code


if __name__ == "__main__":
    sys.exit(main())
