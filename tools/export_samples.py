# -*- coding: utf-8 -*-
"""把统计库导出成 Excel 工作簿（分表：说明 / 空重分数 / 升阻比 / 比油耗 / 功重比 / 九机验证 / 汇总）。

这个脚本是**离线工具**，需要 openpyxl；主程序完全不依赖它。
样本表作静态文件随程序发布，主界面「样本与验证」页签的「打开样本表 Excel」直接打开它。

用法：
    python tools/export_samples.py                # 写到程序同目录的 样本点数据.xlsx
    python tools/export_samples.py D:\\out.xlsx    # 写到指定路径
"""

import datetime
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import calc_core as CC                                    # noqa: E402
from openpyxl import Workbook                             # noqa: E402
from openpyxl.styles import (Alignment, Border, Font,     # noqa: E402
                             PatternFill, Side)
from openpyxl.utils import get_column_letter              # noqa: E402

NAVY = "16324F"
HINT = "8A7355"
HEAD_FILL = PatternFill("solid", fgColor=NAVY)
HEAD_FONT = Font(color="FFFFFF", bold=True, size=11)
TITLE_FONT = Font(color=NAVY, bold=True, size=14)
NOTE_FONT = Font(color=HINT, size=10)
ALT_FILL = PatternFill("solid", fgColor="F4EFE7")
THIN = Side(style="thin", color="E4DDD1")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

GRADE = {"A": "实测", "B": "公开规格", "C": "样本有限"}
LAYOUT_KEYS = ("normal_small_uav", "normal_manned", "canard", "flyingwing", "joined")
POWER_KEYS = ("piston", "turboprop", "turbofan", "electric")


def _head(ws, title, headers, widths, note=""):
    ws["A1"] = title
    ws["A1"].font = TITLE_FONT
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(headers))
    row = 2
    if note:
        ws.cell(row=2, column=1, value=note).font = NOTE_FONT
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=len(headers))
        row = 3
    for i, (h, w) in enumerate(zip(headers, widths), start=1):
        c = ws.cell(row=row, column=i, value=h)
        c.fill, c.font, c.border = HEAD_FILL, HEAD_FONT, BORDER
        c.alignment = Alignment(horizontal="center", vertical="center")
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = ws.cell(row=row + 1, column=1)
    return row + 1


def _body(ws, start_row, rows, fmts, borders=True):
    for r, row in enumerate(rows, start=start_row):
        shade = (r - start_row) % 2 == 1
        for c, val in enumerate(row, start=1):
            cell = ws.cell(row=r, column=c, value=val)
            if borders:
                cell.border = BORDER
            if shade:
                cell.fill = ALT_FILL
            if fmts.get(c):
                cell.number_format = fmts[c]
            if c == 1:
                cell.alignment = Alignment(horizontal="left")
            else:
                cell.alignment = Alignment(horizontal="center")
    ws.auto_filter.ref = "A%d:%s%d" % (start_row - 1,
                                       get_column_letter(len(rows[0]) if rows else 1),
                                       start_row + len(rows) - 1)


def _cover(pts):
    clean = sorted(p[0] for p in pts if p[0] > 0)
    if not clean:
        return "—"
    return "%s – %s" % (_num(clean[0]), _num(clean[-1]))


def _num(v):
    if v >= 1000:
        return "{:,.0f}".format(v)
    return ("%.1f" % v).rstrip("0").rstrip(".")


def _verify_set():
    """从主程序里取 9 架验证样本（两份文件名各兼容一次）。"""
    for name in ("总体参数计算器", "aircraft_sizing_calculator"):
        try:
            mod = importlib.import_module(name)
            data = getattr(mod, "VERIFY_SET", None)
            if data:
                return data
        except Exception:                                   # noqa: BLE001
            continue
    return []


def build(path):
    wb = Workbook()

    # ---------------------------------------------------------------- 说明
    ws = wb.active
    ws.title = "0 说明"
    ws["A1"] = "飞机总体参数计算器 · 统计样本点"
    ws["A1"].font = TITLE_FONT
    ws["A3"] = "生成时间"
    ws["B3"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    ws["A5"] = "这张工作簿是什么"
    ws["A5"].font = Font(bold=True, color=NAVY)
    ws["A6"] = ("程序里每条统计曲线背后的原始样本点，按指标分表排列。"
                "曲线用 log-log 分段插值，严格穿过表里的每一个点。")
    ws.merge_cells("A6:F6")
    ws["A8"] = "分表索引"
    ws["A8"].font = Font(bold=True, color=NAVY)
    index = [
        ("1 空重分数 fE", "按起飞总重的空重分数，五个布局库"),
        ("2 升阻比 LD", "按起飞总重的升阻比，五个布局库"),
        ("3 比油耗 BSFC", "按配平功率的比油耗，四种动力（电机为等效值）"),
        ("4 功重比 Pm", "按配平功率的功重比，四种动力"),
        ("5 九机验证", "9 架实机：输入、真实总重、算出总重、偏差"),
        ("6 汇总", "每个库的点数与覆盖范围、数据来源"),
    ]
    for i, (a, b) in enumerate(index, start=9):
        ws.cell(row=i, column=1, value=a).font = Font(bold=True)
        ws.cell(row=i, column=2, value=b)
    ws["A16"] = "口径提示"
    ws["A16"].font = Font(bold=True, color=NAVY)
    tips = [
        "空重分数 f_E = 空重 / 起飞总重；升阻比库值对应 L/Dmax，重量闭合用设计巡航点（库值 × 0.85，30 t 以下）。",
        "质量全部是 kg，功率是 kW，速度是 km/h；比油耗 kg/(kW·h)，功重比 kW/kg。",
        "样本均取自公开规格资料，等级 A 实测 / B 公开规格 / C 样本有限。",
        "导出脚本：tools/export_samples.py（需要 openpyxl，主程序不依赖）。",
    ]
    for i, t in enumerate(tips, start=17):
        ws.cell(row=i, column=1, value="· " + t).font = NOTE_FONT
        ws.merge_cells(start_row=i, start_column=1, end_row=i, end_column=6)
    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 60

    # ------------------------------------------------------------ 空重分数
    ws = wb.create_sheet("1 空重分数 fE")
    rows = []
    for key in LAYOUT_KEYS:
        e = CC.DB["emptyFrac"].get(key) or {}
        if not e:
            continue
        for w, y in sorted(e.get("points") or [], key=lambda p: p[0]):
            rows.append([e.get("name", key), GRADE.get(e.get("grade", "?"), "—"),
                         w, y, e.get("src", "")])
    start = _head(ws, "空重分数 f_E",
                  ["库 / Library", "等级", "起飞总重 [kg]", "空重分数 f_E", "来源"],
                  [22, 12, 16, 14, 78],
                  "空重分数 = 空重 / 起飞总重，五个布局库各自独立；总表 %d 点。" % len(rows))
    _body(ws, start, rows, {3: "#,##0.0", 4: "0.000"})

    # -------------------------------------------------------------- 升阻比
    ws = wb.create_sheet("2 升阻比 LD")
    rows = []
    for key in LAYOUT_KEYS:
        e = CC.DB["emptyFrac"].get(key) or {}
        d = CC.DB["ld"].get(key) or {}
        for w, y in sorted(d.get("points") or [], key=lambda p: p[0]):
            rows.append([e.get("name", key), GRADE.get(e.get("grade", "?"), "—"),
                         w, y, e.get("src", "")])
    start = _head(ws, "升阻比 L/D",
                  ["库 / Library", "等级", "起飞总重 [kg]", "升阻比 L/D", "来源"],
                  [22, 12, 16, 14, 78],
                  "库值是 L/Dmax；重量闭合时用设计巡航点 L/D = 库值 × 0.85（30 t 以下）。总表 %d 点。" % len(rows))
    _body(ws, start, rows, {3: "#,##0.0", 4: "0.00"})

    # ------------------------------------------------------------ 比油耗
    ws = wb.create_sheet("3 比油耗 BSFC")
    rows = []
    for pk in POWER_KEYS:
        d = CC.DB["power"].get(pk) or {}
        for p, y in d.get("bsfcPts") or []:
            rows.append([d.get("name", pk), GRADE.get(d.get("grade", "?"), "—"),
                         p, y, d.get("src", "")])
    start = _head(ws, "比油耗 BSFC",
                  ["动力 / Powerplant", "等级", "配平功率 [kW]", "BSFC [kg/(kW·h)]", "来源"],
                  [22, 12, 16, 20, 96],
                  "电机没有燃油消耗，表里是等效值（能量口径换算），仅供曲线形状参考。总表 %d 点。" % len(rows))
    _body(ws, start, rows, {3: "#,##0", 4: "0.000"})

    # ------------------------------------------------------------ 功重比
    ws = wb.create_sheet("4 功重比 Pm")
    rows = []
    for pk in POWER_KEYS:
        d = CC.DB["power"].get(pk) or {}
        for p, y in d.get("pwPts") or []:
            rows.append([d.get("name", pk), GRADE.get(d.get("grade", "?"), "—"),
                         p, y, d.get("src", "")])
    start = _head(ws, "功重比 P/m",
                  ["动力 / Powerplant", "等级", "配平功率 [kW]", "P/m [kW/kg]", "来源"],
                  [22, 12, 16, 16, 96],
                  "功重比 = 功率 / 动力系统干重，随功率档位增大而上升。总表 %d 点。" % len(rows))
    _body(ws, start, rows, {3: "#,##0", 4: "0.00"})

    # ------------------------------------------------------------ 九机验证
    vset = _verify_set()
    rows = []
    errs = []
    for (name, pw, WPL, V, R, h, real) in vset:
        cfg = {"power": pw, "layout": "normal", "category": "manned",
               "config": "fixedwing",
               "inp": {"WPL": WPL, "V": V, "R": R, "h": h,
                       "tHover": 0, "Vc": 11}, "des": {}}
        try:
            pred = CC.compute_core(cfg)["Wto"]
            err = (pred - real) / real * 100
        except Exception:                                   # noqa: BLE001
            pred, err = None, None
        if err is not None:
            errs.append(abs(err))
        rows.append([name, (CC.DB["power"].get(pw) or {}).get("name", pw),
                     WPL, real, pred, (err / 100.0 if err is not None else None)])
    ws = wb.create_sheet("5 九机验证")
    note = "9 架实机，商载口径为满油最大商载；平均绝对偏差 %.1f%%，15%% 内 %d 架。" % (
        (sum(errs) / len(errs)) if errs else 0, sum(1 for e in errs if e <= 15))
    start = _head(ws, "9 架实机验证",
                  ["机型 / Aircraft", "动力", "商载 [kg]", "真实总重 [kg]",
                   "算出总重 [kg]", "偏差"],
                  [22, 16, 14, 16, 16, 12], note)
    _body(ws, start, rows, {3: "#,##0", 4: "#,##0", 5: "#,##0", 6: "+0.0%;-0.0%"})

    # ---------------------------------------------------------------- 汇总
    ws = wb.create_sheet("6 汇总")
    rows = []
    for key in LAYOUT_KEYS:
        e = CC.DB["emptyFrac"].get(key) or {}
        d = CC.DB["ld"].get(key) or {}
        if not e:
            continue
        rows.append([e.get("name", key), GRADE.get(e.get("grade", "?"), "—"),
                     len(e.get("points") or []), _cover(e.get("points") or []),
                     len(d.get("points") or []), _cover(d.get("points") or []),
                     e.get("src", "")])
    for pk in POWER_KEYS:
        d = CC.DB["power"].get(pk) or {}
        rows.append([d.get("name", pk), GRADE.get(d.get("grade", "?"), "—"),
                     len(d.get("bsfcPts") or []), _cover(d.get("bsfcPts") or []),
                     len(d.get("pwPts") or []), _cover(d.get("pwPts") or []),
                     d.get("src", "")])
    start = _head(ws, "样本库汇总",
                  ["库 / Library", "等级", "空重分数点数", "总重覆盖 [kg]",
                   "升阻比点数", "升阻比覆盖 [kg]", "来源"],
                  [22, 12, 16, 26, 14, 26, 78])
    _body(ws, start, rows, {})

    wb.save(path)
    return path


def default_path():
    """主程序目录有 data/ 就写 data/sample_points.xlsx，否则写同目录 样本点数据.xlsx。"""
    data_dir = os.path.join(ROOT, "data")
    if os.path.isdir(data_dir):
        return os.path.join(data_dir, "sample_points.xlsx")
    return os.path.join(ROOT, "样本点数据.xlsx")


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else default_path()
    path = build(out)
    print("written:", path)


if __name__ == "__main__":
    main()
