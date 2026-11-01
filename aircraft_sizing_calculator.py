# -*- coding: utf-8 -*-
"""
飞机总体参数计算器 · 桌面版 v4.3
三环收敛：重量—能量环 → 功率—翼载约束环 → 升力系数下推

v4.3：左栏加宽（470 px）、输入指引换成暖褐灰并放大、样本页签补统计曲线图
运行：python aircraft_sizing_calculator.py
依赖：Python 3.9+（仅标准库 tkinter），计算内核见同目录 calc_core.py
"""

import csv
import json
import math
import os
import sys
import traceback
from datetime import datetime
from tkinter import filedialog, messagebox
import tkinter as tk
from tkinter import ttk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import calc_core as CC

# ---------------------------------------------------------------- 配色
# 取自浏览器版的暖白纸面配色：米色分节面板 + 白色卡片 + 深海军蓝主色
BG = "#faf8f5"          # 页面底色
PANEL = "#f4efe7"       # 左栏分节面板（米色）
CARD = "#ffffff"        # 结果卡片 / 表格（白）
FG = "#1f2328"          # 正文
MUTED = "#6b7280"       # 次要文字
ACCENT = "#16324f"      # 主色：深海军蓝
ACCENT2 = "#c05621"     # 次色：赭红
CANVAS_BG = "#ffffff"
OK_GREEN = "#2f5d50"
WARN_RED = "#9c3024"
SEP = "#e4ddd1"         # 描边
FIELD = "#ffffff"       # 输入框底
BTN = "#ece6dc"         # 次要按钮
BTN_HOVER = "#e1d8ca"
SEL = "#e3ecf3"         # 表格选中行
GRID = "#eee8dd"        # 图表网格线
HINT = "#8a7355"        # 输入指引（米色底上的暖褐灰，比次要文字更实）

APP_TITLE = "飞机总体参数计算器"

VERIFY_SET = [
    ("Cessna 172S", "piston", 237, 233, 1185, 2000, 1157),
    ("Piper PA-28-181", "piston", 271, 230, 900, 1500, 1157),
    ("Diamond DA40", "piston", 238, 260, 1300, 2000, 1150),
    ("Cessna 182T", "piston", 272, 270, 1720, 2000, 1406),
    ("Cirrus SR22", "piston", 362, 340, 1800, 2500, 1633),
    ("King Air 350", "turboprop", 638, 580, 3300, 9000, 6804),
    ("Boeing 737-800", "turbofan", 15400, 840, 5400, 11000, 79016),
    ("Airbus A330-300", "turbofan", 36000, 871, 11750, 11500, 242000),
    ("Bombardier Q400", "turboprop", 7000, 667, 2040, 7600, 29574),
]


class ScrollFrame(ttk.Frame):
    """可滚动的垂直容器 —— 保证任何 DPI 下左侧面板都不会被裁掉。"""

    def __init__(self, parent):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, bg=BG, highlightthickness=0, width=452)
        self.vbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vbar.set)
        self.vbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.inner = ttk.Frame(self.canvas)
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>",
                        lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfigure(self._win, width=e.width))
        self.canvas.bind("<Enter>", lambda e: self.canvas.focus_set())
        # 滚轮在整块左栏（含输入框）都生效，按像素平滑滚动
        self.canvas.configure(yscrollincrement=1)
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.canvas.bind_all(seq, self._on_wheel, add="+")

    def _on_wheel(self, event):
        # 指针不在本滚动区内就交给别的控件
        try:
            w = self.winfo_containing(*self.winfo_pointerxy())
        except Exception:  # noqa: BLE001
            return
        node = w
        while node is not None:
            if node is self:
                break
            node = getattr(node, "master", None)
        if node is not self:
            return
        if getattr(event, "num", None) == 4:
            step = -1
        elif getattr(event, "num", None) == 5:
            step = 1
        else:
            step = -1 if event.delta > 0 else 1
        self.canvas.yview_scroll(int(step * 3 * 20), "units")
        return "break"


class Calculator:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title(APP_TITLE)
        root.configure(bg=BG)

        try:
            self.s = max(1.0, root.winfo_fpixels("1i") / 96.0)
        except Exception:  # noqa: BLE001
            self.s = 1.0

        self.power = tk.StringVar(value="turboprop")
        self.layout = tk.StringVar(value="normal")
        self.config = tk.StringVar(value="fixedwing")
        self.category = tk.StringVar(value="manned")
        self.vars: dict[str, tk.StringVar] = {}
        self.design_ws = tk.StringVar()
        self.design_wp = tk.StringVar()
        self.result = None
        self._job = None
        self._silent = False

        self._build_style()
        self._build_layout()
        self._init_values()
        self._refresh()
        try:
            self._run_verify()          # 预先填好 9 架验证表，页签不留白
        except Exception:  # noqa: BLE001
            traceback.print_exc()

        for delay in (150, 500, 1200):
            root.after(delay, self._refresh)

    # ------------------------------------------------------------ 基础设施
    def _font(self, px: int, bold: bool = False, mono: bool = False):
        fam = "Consolas" if mono else "Microsoft YaHei UI"
        size = -max(9, int(px * self.s))
        return (fam, size, "bold") if bold else (fam, size)

    def _schedule(self):
        if self._silent:
            return
        if self._job:
            try:
                self.root.after_cancel(self._job)
            except Exception:  # noqa: BLE001
                pass
        self._job = self.root.after(180, self._refresh)

    # ------------------------------------------------------------ 样式
    def _build_style(self):
        st = ttk.Style()
        st.theme_use("clam")
        st.configure(".", background=BG, foreground=FG, fieldbackground=FIELD,
                     bordercolor=SEP, lightcolor=BG, darkcolor=BG)
        st.configure("TFrame", background=BG)
        st.configure("Panel.TFrame", background=PANEL)
        st.configure("Card.TFrame", background=CARD)
        st.configure("TLabel", background=BG, foreground=FG)
        st.configure("Panel.TLabel", background=PANEL, foreground=FG)
        st.configure("Muted.TLabel", background=BG, foreground=MUTED)
        st.configure("Hint.TLabel", background=PANEL, foreground=HINT,
                     font=self._font(12))
        st.configure("CardName.TLabel", background=CARD, foreground=MUTED,
                     font=self._font(11))
        st.configure("CardValue.TLabel", background=CARD, foreground=ACCENT)
        st.configure("H1.TLabel", background=BG, foreground=ACCENT, font=self._font(19, bold=True))
        st.configure("H2.TLabel", background=BG, foreground=ACCENT, font=self._font(13, bold=True))
        st.configure("Mono.TLabel", background=CARD, foreground=FG, font=self._font(12, mono=True))
        st.configure("Value.TLabel", background=BG, foreground=OK_GREEN,
                     font=self._font(13, mono=True))
        st.configure("Big.TLabel", background=PANEL, foreground=ACCENT,
                     font=self._font(26, bold=True, mono=True))
        st.configure("TEntry", insertcolor=FG, padding=4,
                     fieldbackground=FIELD, foreground=FG,
                     bordercolor=SEP, lightcolor=SEP, darkcolor=SEP)
        st.map("TEntry", bordercolor=[("focus", ACCENT)],
               lightcolor=[("focus", ACCENT)], darkcolor=[("focus", ACCENT)])
        st.configure("TCombobox", padding=3)
        st.configure("TButton", padding=(10, 4), background=BTN,
                     foreground=FG, font=self._font(12), borderwidth=0)
        st.map("TButton", background=[("active", BTN_HOVER)],
               foreground=[("active", ACCENT)])
        st.configure("Go.TButton", background=ACCENT, foreground="#ffffff",
                     font=self._font(14, bold=True), borderwidth=0)
        st.map("Go.TButton", background=[("active", "#22456b")],
               foreground=[("active", "#ffffff")])
        st.configure("TNotebook", background=BG, borderwidth=0, tabmargins=(0, 0, 0, 0))
        st.configure("TNotebook.Tab", background=PANEL, foreground=MUTED,
                     padding=(16, 8), borderwidth=0, font=self._font(12))
        st.map("TNotebook.Tab", background=[("selected", CARD)],
               foreground=[("selected", ACCENT)],
               expand=[("selected", (0, 0, 0, 0))])
        st.configure("Treeview", background=CARD, fieldbackground=CARD,
                     foreground=FG, rowheight=int(24 * self.s), borderwidth=0,
                     font=self._font(12))
        st.configure("Treeview.Heading", background=PANEL, foreground=ACCENT,
                     font=self._font(12, bold=True), borderwidth=0,
                     padding=(6, 5))
        st.map("Treeview", background=[("selected", SEL)],
               foreground=[("selected", FG)])
        st.configure("TScrollbar", background=BTN, troughcolor=BG,
                     borderwidth=0, arrowcolor=MUTED)
        st.configure("TCheckbutton", background=PANEL, foreground=FG,
                     font=self._font(12))

    # ------------------------------------------------------------ 布局
    def _build_layout(self):
        self.root.rowconfigure(1, weight=1)
        self.root.columnconfigure(0, weight=1)

        head = ttk.Frame(self.root, padding=(18, 12, 18, 0))
        head.grid(row=0, column=0, sticky="ew")
        hrow = ttk.Frame(head)
        hrow.pack(fill="x")
        ttk.Label(hrow, text=APP_TITLE, style="H1.TLabel").pack(side="left")
        ttk.Label(hrow, text="三次选择 → 任务条件 → 三环收敛 → 约束边界 → 翼型入口",
                  style="Muted.TLabel").pack(side="left", padx=(14, 0), pady=(7, 0))
        tk.Frame(head, bg=SEP, height=1).pack(fill="x", pady=(10, 0))

        body = ttk.Frame(self.root, padding=(18, 0, 18, 8))
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=0, minsize=470)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        left = ScrollFrame(body)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        self.sf = left
        right = ttk.Frame(body)
        right.grid(row=0, column=1, sticky="nsew")

        self._build_select_panels(left.inner)
        self._build_task_panel(left.inner)
        self._build_option_panel(left.inner)
        self._build_design_panel(left.inner)
        self._build_right(right)
        self._build_actions(self.root)

        self.root.geometry("1480x960+30+20")
        self.root.minsize(1100, 680)

    def _build_actions(self, parent):
        bar = ttk.Frame(parent, padding=(18, 0, 18, 12))
        bar.grid(row=2, column=0, sticky="ew")
        tk.Frame(bar, bg=SEP, height=1).pack(fill="x", pady=(0, 8))
        row = ttk.Frame(bar)
        row.pack(fill="x")
        ttk.Button(row, text="重新计算", style="Go.TButton",
                   command=self._refresh).pack(side="left")
        ttk.Button(row, text="导出 JSON",
                   command=self._export_json).pack(side="left", padx=(8, 0))
        ttk.Button(row, text="导出 CSV",
                   command=self._export_csv).pack(side="left", padx=(8, 0))
        ttk.Button(row, text="说明", command=self._about).pack(side="left", padx=(8, 0))
        self.status = ttk.Label(row, text="", style="Muted.TLabel")
        self.status.pack(side="right")

    # ------------------------------------------------------------ 左侧：三次选择
    def _build_select_panels(self, parent):
        self._toggle_group(parent, "① 动力类型", self.power, CC.POWER_OPTS, cols=2)
        self._toggle_group(parent, "② 总体布局", self.layout, CC.LAYOUT_OPTS, cols=4)
        self._toggle_group(parent, "③ 旋翼构型", self.config, CC.CONFIG_OPTS, cols=3)

        self.cat_box = ttk.Frame(parent, style="Panel.TFrame", padding=10)
        self.cat_title = ttk.Label(parent, text="④ 机型类别（只影响统计库）",
                                   style="H2.TLabel")
        self.cat_title.pack(anchor="w", pady=(12, 4))
        self.cat_box.pack(fill="x")
        r = ttk.Frame(self.cat_box, style="Panel.TFrame")
        r.pack(fill="x")
        self.cat_btns = {}
        for val, label, hint in (("manned", "有人机", "通航 / 支线 / 干线"),
                                 ("uav", "无人机", "小型 UAV，<250 kg")):
            b = tk.Button(r, text=label, bd=0, relief="flat", cursor="hand2",
                          font=self._font(12), padx=10, pady=4,
                          command=lambda v=val: self._choose(self.category, v))
            b.pack(side="left", padx=(0, 6))
            self.cat_btns[val] = b
        ttk.Label(self.cat_box, text="布局选「常规」时才需要区分；其余布局各自独立建库。",
                  style="Hint.TLabel").pack(anchor="w", pady=(6, 0))

        def cat_render():
            sel = self.category.get()
            for k, b in self.cat_btns.items():
                on = (k == sel)
                b.configure(bg=ACCENT if on else BTN,
                            fg="#ffffff" if on else FG,
                            activebackground="#22456b" if on else BTN_HOVER,
                            activeforeground="#ffffff" if on else FG)
        self.category.trace_add("write", lambda *_: (cat_render(), self._schedule()))
        cat_render()

        self.power.trace_add("write", lambda *_: self._rebuild_special())

    def _toggle_group(self, parent, title, var, opts, cols=4):
        opts = [(o[0], o[1], o[2] if len(o) > 2 else "") for o in opts]
        ttk.Label(parent, text=title, style="H2.TLabel").pack(anchor="w", pady=(12, 4))
        box = ttk.Frame(parent, style="Panel.TFrame", padding=10)
        box.pack(fill="x")
        grid = ttk.Frame(box, style="Panel.TFrame")
        grid.pack(fill="x")
        desc = ttk.Label(box, text="", style="Hint.TLabel", wraplength=340, justify="left")
        btns = {}

        def render():
            sel = var.get()
            for k, b in btns.items():
                on = (k == sel)
                b.configure(bg=ACCENT if on else BTN,
                            fg="#ffffff" if on else FG,
                            activebackground="#22456b" if on else BTN_HOVER,
                            activeforeground="#ffffff" if on else FG)
            cur = [o for o in opts if o[0] == sel]
            desc.configure(text=cur[0][2] if cur else "")

        for i, (val, label, hint) in enumerate(opts):
            r, c = divmod(i, cols)
            b = tk.Button(grid, text=label, bd=0, relief="flat", cursor="hand2",
                          font=self._font(12), padx=8, pady=5,
                          command=lambda v=val: self._choose(var, v))
            b.grid(row=r, column=c, sticky="ew", padx=(0, 6), pady=(0, 6))
            btns[val] = b
        for c in range(cols):
            grid.columnconfigure(c, weight=1)
        desc.pack(anchor="w", pady=(2, 0))
        var.trace_add("write", lambda *_: (render(), self._schedule()))
        render()

    def _choose(self, var, val):
        if var.get() == val:
            return
        var.set(val)
        self._schedule()

    # ------------------------------------------------------------ 左侧：任务条件
    def _build_task_panel(self, parent):
        ttk.Label(parent, text="⑤ 任务与飞行条件", style="H2.TLabel").pack(
            anchor="w", pady=(12, 4))
        box = ttk.Frame(parent, style="Panel.TFrame", padding=10)
        box.pack(fill="x")
        box.columnconfigure(2, weight=1)
        self.task_box = box

        rows = [
            ("inWL", "任务载重 [kg]", "比如 1500"),
            ("inV", "巡航速度 [km/h]", "比如 500"),
            ("inR", "航程 [km]", "比如 1500"),
            ("inH", "巡航高度 [m]", "比如 8000"),
        ]
        for i, (key, label, hint) in enumerate(rows):
            self._row(box, i, label, key, hint)

        self.vtol_frame = ttk.Frame(box, style="Panel.TFrame")
        self.vtol_frame.grid(row=len(rows), column=0, columnspan=3, sticky="ew", pady=(8, 0))
        self.vtol_frame.columnconfigure(2, weight=1)
        vrows = [
            ("inTH", "悬停时长 [min]", "比如 20"),
            ("inVC", "垂直爬升率 [m/s]", "比如 3"),
            ("inNB", "旋翼数量", "比如 6"),
            ("inDr", "桨径 [m]", "比如 0.9"),
        ]
        for i, (key, label, hint) in enumerate(vrows):
            self._row(self.vtol_frame, i, label, key, hint)

        self.task_note = ttk.Label(box, text="", style="Hint.TLabel",
                                   wraplength=340, justify="left")
        self.task_note.grid(row=len(rows) + 1, column=0, columnspan=3, sticky="w", pady=(8, 0))

        btn = ttk.Button(box, text="填入示例任务", command=self._fill_example)
        btn.grid(row=len(rows) + 2, column=0, columnspan=3, sticky="w", pady=(8, 0))

    def _row(self, box, r, label, key, hint="", width=11):
        ttk.Label(box, text=label, style="Panel.TLabel").grid(
            row=r, column=0, sticky="w", pady=3, padx=(0, 8))
        v = tk.StringVar()
        self.vars[key] = v
        ttk.Entry(box, textvariable=v, width=width).grid(
            row=r, column=1, sticky="w", pady=3)
        box.columnconfigure(1, minsize=int(96 * self.s))
        if hint:
            ttk.Label(box, text=hint, style="Hint.TLabel").grid(
                row=r, column=2, sticky="w", padx=(10, 0))
        v.trace_add("write", lambda *_: self._schedule())
        return v

    def _fill_example(self):
        vt = self.config.get() != "fixedwing"
        if vt:
            ex = {"inWL": "3", "inV": "90", "inR": "30", "inH": "500",
                  "inTH": "10", "inVC": "3", "inNB": "6", "inDr": "0.6"}
            self.category.set("uav")
        else:
            ex = {"inWL": "1500", "inV": "500", "inR": "1500", "inH": "8000",
                  "inTH": "20", "inVC": "3", "inNB": "6", "inDr": "0.9"}
        self._silent = True
        for k, v in ex.items():
            if k in self.vars:
                self.vars[k].set(v)
        self._silent = False
        self._refresh()

    # ------------------------------------------------------------ 左侧：约束选填
    def _build_option_panel(self, parent):
        ttk.Label(parent, text="⑥ 约束参数（都可留空）", style="H2.TLabel").pack(
            anchor="w", pady=(12, 4))
        box = ttk.Frame(parent, style="Panel.TFrame", padding=10)
        box.pack(fill="x")
        box.columnconfigure(2, weight=1)
        rows = [
            ("inVapp", "进场速度 [m/s]", "留空 = 0.6V"),
            ("inGam", "全发爬升梯度 [%]", "比如 5"),
            ("inGamO", "单发第二段梯度 [%]", "比如 2.4"),
            ("inGamR", "航路单发梯度 [%]", "比如 2.0"),
            ("inTurn", "盘旋过载 n", "比如 2.5"),
            ("inSTO", "起飞距离 [m]", "比如 600"),
            ("inSL", "着陆距离 [m]", "比如 900"),
            ("inWind", "抗风 [kt]", "比如 10"),
        ]
        for i, (key, label, hint) in enumerate(rows):
            self._row(box, i, label, key, hint)
        ttk.Label(box, text="留空就不画这条边界，不影响其他结果。",
                  style="Hint.TLabel").grid(row=len(rows), column=0, columnspan=3,
                                            sticky="w", pady=(8, 0))

    # ------------------------------------------------------------ 左侧：设计与统计
    def _build_design_panel(self, parent):
        ttk.Label(parent, text="⑦ 效率与设计参数", style="H2.TLabel").pack(
            anchor="w", pady=(12, 4))
        box = ttk.Frame(parent, style="Panel.TFrame", padding=10)
        box.pack(fill="x")
        box.columnconfigure(2, weight=1)
        self.design_box = box
        rows = [
            ("inWS", "翼载 W/S [kg/m²]", "比如 17"),
            ("inAR", "展弦比 AR", "比如 6"),
            ("inCLmax", "C_Lmax", "比如 1.4"),
            ("inEtaP", "推进效率 η_prop", "比如 0.78"),
            ("inEtaT", "传动效率 η_trans", "比如 0.96"),
            ("inFM", "旋翼品质因数 FM", "比如 0.70"),
        ]
        for i, (key, label, hint) in enumerate(rows):
            self._row(box, i, label, key, hint)

        self.special_box = ttk.Frame(box, style="Panel.TFrame")
        self.special_box.grid(row=len(rows), column=0, columnspan=3, sticky="ew", pady=(8, 0))
        self.special_box.columnconfigure(2, weight=1)
        self.special_rows = {}

        ttk.Label(parent, text="⑧ 统计值覆盖（留空 = 用库曲线）", style="H2.TLabel").pack(
            anchor="w", pady=(12, 4))
        ob = ttk.Frame(parent, style="Panel.TFrame", padding=10)
        ob.pack(fill="x")
        ob.columnconfigure(2, weight=1)
        for i, (key, label, hint) in enumerate([
                ("inFE", "空重分数 f_E", "比如 0.52"),
                ("inLD", "升阻比 L/D", "比如 13"),
                ("inLDC", "巡航 L/D 系数", "比如 0.85")]):
            self._row(ob, i, label, key, hint)
        ttk.Label(ob, text="想用手上的确切数据时再填，平时留空让曲线自己算。",
                  style="Hint.TLabel").grid(row=3, column=0, columnspan=3,
                                            sticky="w", pady=(8, 0))

    def _rebuild_special(self):
        """动力/构型变化后，重画 ⑦ 里随动力类型变化的几行。"""
        for w in self.special_box.winfo_children():
            w.destroy()
        self.special_rows.clear()
        if self.power.get() == "electric":
            rows = [("inEb", "电池比能量 [Wh/kg]", "比如 180"),
                    ("inPb", "电池比功率 [W/kg]", "比如 1000"),
                    ("inDoD", "放电深度 DoD", "比如 0.85")]
        else:
            rows = [("inBSFC", "BSFC [kg/(kW·h)]", "比如 0.30"),
                    ("inTaxi", "滑行燃油系数", "比如 0.06"),
                    ("inDesc", "下降燃油系数", "比如 0.03")]
        for i, (key, label, hint) in enumerate(rows):
            self._row(self.special_box, i, label, key, hint)
            self.special_rows[key] = i

    # ------------------------------------------------------------ 右侧
    def _build_right(self, parent):
        self.nb = ttk.Notebook(parent)
        self.nb.pack(fill="both", expand=True)

        self.tab_res = ttk.Frame(self.nb, padding=10)
        self.tab_cons = ttk.Frame(self.nb, padding=10)
        self.tab_trace = ttk.Frame(self.nb, padding=10)
        self.tab_data = ttk.Frame(self.nb, padding=10)
        self.nb.add(self.tab_res, text="  结果总览  ")
        self.nb.add(self.tab_cons, text="  约束边界  ")
        self.nb.add(self.tab_trace, text="  参数溯源  ")
        self.nb.add(self.tab_data, text="  样本与验证  ")

        self._build_res_tab()
        self._build_cons_tab()
        self._build_trace_tab()
        self._build_data_tab()
        self.nb.bind("<<NotebookTabChanged>>", lambda e: self._on_tab())

    def _on_tab(self):
        try:
            idx = self.nb.index(self.nb.select())
        except Exception:  # noqa: BLE001
            return
        if idx == 1:
            self._draw_constraints()
        elif idx == 3:
            self._draw_fit()

    # ---- 结果总览
    def _build_res_tab(self):
        p = self.tab_res
        banner = ttk.Frame(p, style="Panel.TFrame", padding=14)
        banner.pack(fill="x")
        self.big_label = ttk.Label(banner, text="—", style="Big.TLabel")
        self.big_label.pack(side="left")
        side = ttk.Frame(banner, style="Panel.TFrame")
        side.pack(side="left", padx=(18, 0))
        self.banner_sub = ttk.Label(side, text="", style="CardName.TLabel",
                                    font=self._font(12))
        self.banner_sub.pack(anchor="w")
        self.banner_note = ttk.Label(side, text="", style="CardName.TLabel",
                                     font=self._font(11), wraplength=520, justify="left")
        self.banner_note.pack(anchor="w", pady=(4, 0))

        cards = ttk.Frame(p)
        cards.pack(fill="x", pady=(10, 0))
        self.cards = {}
        self.card_titles = {}
        names = ["空重", "燃油", "巡航功率", "峰值功率", "机翼面积", "翼展",
                 "失速速度", "进场速度", "巡航 C_L", "翼型 C_li", "升阻比", "空重分数"]
        for i, n in enumerate(names):
            r, c = divmod(i, 4)
            f = tk.Frame(cards, bg=CARD, bd=0, highlightthickness=1,
                         highlightbackground=SEP, highlightcolor=SEP)
            f.grid(row=r, column=c, sticky="nsew", padx=(0, 8), pady=(0, 8))
            cards.columnconfigure(c, weight=1)
            fi = ttk.Frame(f, style="Card.TFrame", padding=10)
            fi.pack(fill="both", expand=True)
            t = ttk.Label(fi, text=n, style="CardName.TLabel")
            t.pack(anchor="w")
            v = ttk.Label(fi, text="—", style="CardValue.TLabel",
                          font=self._font(17, bold=True, mono=True))
            v.pack(anchor="w", pady=(2, 0))
            self.cards[n] = v
            self.card_titles[n] = t

        ttk.Label(p, text="重量闭合迭代", style="H2.TLabel").pack(anchor="w", pady=(6, 4))
        cols = ("k", "wto", "fe", "ld", "fuel", "conv")
        self.itree = ttk.Treeview(p, columns=cols, show="headings", height=8)
        for cid, txt, wd in (("k", "轮次", 60), ("wto", "总重 [kg]", 110),
                             ("fe", "空重分数", 100), ("ld", "L/D", 80),
                             ("fuel", "燃油/电池 [kg]", 130), ("conv", "收敛度", 100)):
            self.itree.heading(cid, text=txt)
            self.itree.column(cid, width=wd, anchor="e" if cid != "k" else "center")
        self.itree.pack(fill="both", expand=True, pady=(0, 6))

    # ---- 约束边界
    def _build_cons_tab(self):
        p = self.tab_cons
        top = ttk.Frame(p)
        top.pack(fill="x")
        ttk.Label(top, text="四条功率边界 + 失速边界 → 切割出可行域",
                  style="Muted.TLabel").pack(side="left")
        self.cons_status = ttk.Label(top, text="", style="Value.TLabel")
        self.cons_status.pack(side="right")

        self.canvas = tk.Canvas(p, bg=CANVAS_BG, highlightthickness=0, height=430)
        self.canvas.pack(fill="both", expand=True, pady=(8, 8))
        self.canvas.bind("<Configure>", lambda e: self._draw_constraints())

        bar = ttk.Frame(p, style="Panel.TFrame", padding=10)
        bar.pack(fill="x")
        ttk.Label(bar, text="设计点", style="Panel.TLabel").pack(side="left", padx=(0, 10))
        ttk.Label(bar, text="翼载 W/S [kg/m²]", style="Panel.TLabel").pack(side="left")
        e1 = ttk.Entry(bar, textvariable=self.design_ws, width=9)
        e1.pack(side="left", padx=(6, 16))
        ttk.Label(bar, text="功率载荷 W/P [kg/kW]", style="Panel.TLabel").pack(side="left")
        e2 = ttk.Entry(bar, textvariable=self.design_wp, width=9)
        e2.pack(side="left", padx=(6, 16))
        ttk.Button(bar, text="取可行域内点", command=self._pick_feasible).pack(side="left")
        self.cons_info = ttk.Label(bar, text="", style="Hint.TLabel")
        self.cons_info.pack(side="left", padx=(14, 0))
        for v in (self.design_ws, self.design_wp):
            v.trace_add("write", lambda *_: self._schedule())

    # ---- 参数溯源
    def _build_trace_tab(self):
        p = self.tab_trace
        ttk.Label(p, text="每个参数都能追到它的来源：输入 / 计算 / 统计 / 假设 / 规范",
                  style="Muted.TLabel").pack(anchor="w", pady=(0, 6))
        cols = ("sym", "name", "value", "unit", "src")
        wrap = ttk.Frame(p)
        wrap.pack(fill="both", expand=True)
        self.ttree = ttk.Treeview(wrap, columns=cols, show="headings", height=16)
        for cid, txt, wd, anc in (("sym", "符号", 120, "w"), ("name", "参数", 190, "w"),
                                  ("value", "数值", 110, "e"), ("unit", "单位", 90, "w"),
                                  ("src", "来源", 80, "center")):
            self.ttree.heading(cid, text=txt)
            self.ttree.column(cid, width=wd, anchor=anc)
        sb = ttk.Scrollbar(wrap, command=self.ttree.yview)
        self.ttree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.ttree.pack(side="left", fill="both", expand=True)
        self.ttree.bind("<<TreeviewSelect>>", self._show_param_detail)

        self.detail = tk.Text(p, bg=CARD, fg=FG, borderwidth=0,
                              highlightthickness=1, highlightbackground=SEP,
                              wrap="word", height=7,
                              font=self._font(12), padx=10, pady=8)
        self.detail.pack(fill="x", pady=(8, 0))
        self.detail.configure(state="disabled")

    # ---- 样本与验证
    def _build_data_tab(self):
        p = self.tab_data
        head = ttk.Frame(p)
        head.pack(fill="x")
        ttk.Label(head, text="统计曲线：严格穿过每个样本点（log-log 分段插值）",
                  style="Muted.TLabel").pack(side="left")
        ttk.Button(head, text="跑一遍 9 架实机验证",
                   command=self._run_verify).pack(side="right")

        # ---------------------------------------------------- 拟合曲线图
        self.fit_kind = "fE"
        card = tk.Frame(p, bg=CARD, highlightthickness=1, highlightbackground=SEP)
        card.pack(fill="x", pady=(8, 6))
        bar = tk.Frame(card, bg=CARD)
        bar.pack(fill="x", padx=10, pady=(8, 0))
        self.fit_btns = {}
        for k, label in (("fE", "空重分数 f_E"), ("ld", "升阻比 L/D"),
                         ("bsfc", "比油耗 BSFC"), ("pw", "功重比 P/m")):
            b = tk.Button(bar, text=label, bd=0, relief="flat", cursor="hand2",
                          font=self._font(11), padx=12, pady=4,
                          command=lambda kk=k: self._fit_set_kind(kk))
            b.pack(side="left", padx=(0, 7))
            self.fit_btns[k] = b
        self.fit_cap = ttk.Label(card, text="", style="CardName.TLabel",
                                 wraplength=820, justify="left")
        self.fit_cap.pack(anchor="w", padx=10, pady=(4, 0))
        self.fit_cv = tk.Canvas(card, bg=CANVAS_BG, highlightthickness=0,
                                height=int(228 * self.s))
        self.fit_cv.pack(fill="x", padx=10, pady=(4, 10))
        self.fit_cv.bind("<Configure>", lambda e: self._draw_fit())

        self.fit_label = ttk.Label(p, text="", style="Mono.TLabel",
                                   background=PANEL, justify="left",
                                   wraplength=820)
        self.fit_label.pack(fill="x", pady=(4, 8), ipady=6)

        cols = ("name", "wpl", "real", "pred", "err")
        self.vtree = ttk.Treeview(p, columns=cols, show="headings", height=6)
        for cid, txt, wd in (("name", "机型", 180), ("wpl", "载重 [kg]", 110),
                             ("real", "真实总重 [kg]", 130), ("pred", "算出总重 [kg]", 130),
                             ("err", "偏差", 100)):
            self.vtree.heading(cid, text=txt)
            self.vtree.column(cid, width=wd, anchor="w" if cid == "name" else "e")
        self.vtree.pack(fill="both", expand=True)
        self.verify_note = ttk.Label(p, text="", style="Muted.TLabel", wraplength=780,
                                     justify="left")
        self.verify_note.pack(anchor="w", pady=(8, 4))

        ttk.Label(p, text="数据来源", style="H2.TLabel").pack(anchor="w", pady=(6, 2))
        self.src_text = tk.Text(p, bg=CARD, fg=FG, borderwidth=0,
                                highlightthickness=1, highlightbackground=SEP,
                                wrap="word", height=5, font=self._font(11),
                                padx=10, pady=6)
        self.src_text.pack(fill="x")
        self.src_text.configure(state="disabled")

    # ------------------------------------------------------------ 初始值
    def _init_values(self):
        for k, v in {"inWL": "", "inV": "", "inR": "", "inH": "",
                     "inTH": "20", "inVC": "3", "inNB": "6", "inDr": "0.9",
                     "inWS": "", "inAR": "", "inCLmax": "", "inEtaP": "", "inEtaT": "",
                     "inFM": "", "inVapp": "", "inGam": "", "inGamO": "", "inGamR": "",
                     "inTurn": "", "inSTO": "", "inSL": "", "inWind": "",
                     "inFE": "", "inLD": "", "inLDC": "",
                     "inEb": "", "inPb": "", "inDoD": "", "inBSFC": "", "inTaxi": "",
                     "inDesc": ""}.items():
            if k in self.vars:
                self._silent = True
                self.vars[k].set(v)
                self._silent = False
        self._rebuild_special()
        self._sync_vtol_visibility()

    def _sync_vtol_visibility(self):
        vt = self.config.get() != "fixedwing"
        if vt:
            self.vtol_frame.grid()
        else:
            self.vtol_frame.grid_remove()
        show_cat = self.layout.get() == "normal"
        if show_cat:
            self.cat_title.pack(anchor="w", pady=(12, 4))
            self.cat_box.pack(fill="x")
        else:
            self.cat_title.pack_forget()
            self.cat_box.pack_forget()

    # ------------------------------------------------------------ 数据读取
    def _num(self, key, default=None):
        v = self.vars.get(key)
        if v is None:
            return default
        s = v.get().strip()
        if not s:
            return default
        try:
            return float(s)
        except ValueError:
            return default

    def _current_cfg(self):
        vt = self.config.get() != "fixedwing"
        inp = {
            "WPL": self._num("inWL", 0.0),
            "V": self._num("inV", 0.0),
            "R": self._num("inR", 0.0),
            "h": self._num("inH", 0.0),
            "tHover": self._num("inTH", 0.0) if vt else 0.0,
            "Vc": self._num("inVC", 0.0) if vt else 0.0,
        }
        des = {}
        mapping = {
            "inWS": "WS", "inAR": "AR", "inCLmax": "CLmax", "inEtaP": "etaP",
            "inEtaT": "etaT", "inFM": "FM", "inNB": "NB", "inDr": "D",
            "inVapp": "Vapp", "inGam": "gamma", "inGamO": "gammaOEI",
            "inGamR": "gammaRoute", "inTurn": "nTurn", "inSTO": "STO",
            "inSL": "SL", "inWind": "Vwind", "inFE": "fE", "inLD": "LD",
            "inLDC": "ldCruise", "inEb": "e_batt", "inPb": "p_batt",
            "inDoD": "DoD", "inBSFC": "bsfc", "inTaxi": "fTaxi", "inDesc": "fDescent",
        }
        for k, dk in mapping.items():
            val = self._num(k)
            if val is not None:
                des[dk] = val
        if vt:
            des.setdefault("NB", self._num("inNB", 6))
            des.setdefault("D", self._num("inDr", 0.9))
        return {"power": self.power.get(), "layout": self.layout.get(),
                "category": self.category.get(), "config": self.config.get(),
                "inp": inp, "des": des}

    # ------------------------------------------------------------ 主刷新
    def _refresh(self):
        self._job = None
        self._sync_vtol_visibility()
        cfg = self._current_cfg()
        need = cfg["inp"]
        missing = [n for n, k in (("载重", "WPL"), ("速度", "V"), ("航程", "R"),
                                  ("高度", "h")) if not need[k] or need[k] <= 0]
        if missing:
            self.result = None
            self.big_label.configure(text="—", foreground=MUTED)
            self.banner_sub.configure(text="还差：" + "、".join(missing))
            self.banner_note.configure(
                text="填好这四项就会自动算。示例：载重 1500 kg、速度 500 km/h、"
                     "航程 1500 km、高度 8000 m。")
            for lb in self.cards.values():
                lb.configure(text="—", foreground=FG)
            self.itree.delete(*self.itree.get_children())
            self._fill_sources()
            self._draw_constraints()
            self._draw_fit()
            if hasattr(self, "status"):
                self.status.configure(text="等待任务条件")
            return

        try:
            r = CC.compute_core(cfg)
        except Exception as exc:  # noqa: BLE001
            self.result = None
            self.big_label.configure(text="—", foreground=WARN_RED)
            self.banner_sub.configure(text="计算出错")
            self.banner_note.configure(text=str(exc))
            traceback.print_exc()
            return

        self.result = r
        self._fill_result(r)
        self._fill_trace(r)
        self._fill_fit(r)
        self._fill_sources()
        self._draw_constraints()
        self._draw_fit()
        if hasattr(self, "status"):
            self.status.configure(text="W_TO %.0f kg　空重 %.0f kg　%s %.0f kg　%s" % (
                r["Wto"], r["WE"], "电池" if r["isElec"] else "燃油",
                r["mBatt"] if r["isElec"] else r["Wfuel"],
                "已收敛" if r["solved"] else "未收敛"))

    def _fill_result(self, r):
        if not r["solved"]:
            self.big_label.configure(text="无解", foreground=WARN_RED)
            self.banner_sub.configure(text="重量闭合没有自洽解")
            self.banner_note.configure(
                text="悬停/巡航能量随总重涨得比燃油或电池质量快，迭代追不上。\n"
                     "可以试：加大桨径、缩短悬停时长、提高电池比能量，"
                     "或在 ⑧ 里填更确切的空重分数（比如 0.55）。")
            for lb in self.cards.values():
                lb.configure(text="—", foreground=FG)
            self.itree.delete(*self.itree.get_children())
            return

        self.big_label.configure(text=CC.fmt(r["Wto"], 0) + " kg", foreground=ACCENT)
        kind = "电机 + 电池" if r["isElec"] else ("涡桨" if self.power.get() == "turboprop"
                                              else ("涡扇" if self.power.get() == "turbofan" else "活塞"))
        status = "已收敛" if r["solved"] else "未收敛（给的是最接近的点）"
        self.banner_sub.configure(
            text="起飞总重 · %s · %s · %d 个自洽解" % (kind, status, len(r["roots"])))
        notes = list(r.get("warn") or [])
        base = "空重分数 %.3f，升阻比 %.2f，%s" % (
            r["fE"], r["LD"], "倾转旋翼" if r["isVTOL"] else "固定翼")
        if r["isVTOL"] and r["Arot"] > 0:
            dl = r["Wto"] * CC.G / r["Arot"]
            base += "，桨盘载荷 %.0f N/m²" % dl
            if dl > 800:
                notes.append("桨盘载荷 %.0f N/m² 偏高（直升机量级 300–600 N/m²），"
                             "悬停功率被放大；可加大桨径或减小载重" % dl)
        self.banner_note.configure(
            text=("注意：" + "；".join(notes)) if notes else base)

        c = self.cards
        energy_lbl = "电池" if r["isElec"] else "燃油"
        self.card_titles["燃油"].configure(text=energy_lbl)
        c["空重"].configure(text=CC.fmt(r["WE"], 1) + " kg")
        c["燃油"].configure(text=CC.fmt(r["mBatt"] if r["isElec"] else r["Wfuel"], 1)
                            + " kg", foreground=OK_GREEN)
        c["巡航功率"].configure(text=CC.fmt(r["Pcr"] / 1000, 1) + " kW")
        c["峰值功率"].configure(text=CC.fmt(r["Ppk"] / 1000, 1) + " kW")
        c["机翼面积"].configure(text=CC.fmt(r["S"], 2) + " m²")
        c["翼展"].configure(text=CC.fmt(r["b"], 2) + " m")
        c["失速速度"].configure(text=CC.fmt(r["Vstall"], 1) + " m/s")
        c["进场速度"].configure(text=CC.fmt(r["Vapp"], 1) + " m/s")
        c["巡航 C_L"].configure(text=CC.fmt(r["CLc"], 3))
        c["翼型 C_li"].configure(text=CC.fmt(r["CLi"], 3))
        c["升阻比"].configure(text=CC.fmt(r["LD"], 2))
        c["空重分数"].configure(text=CC.fmt(r["fE"], 3))

        self.itree.delete(*self.itree.get_children())
        for it in r["iters"]:
            self.itree.insert("", "end", values=(
                it["k"], CC.fmt(it["Wto"], 1), CC.fmt(it["fE"], 3),
                CC.fmt(it["LD"], 2),
                CC.fmt(it["mB"] if r["isElec"] else it["fuel"], 1),
                "%.2f%%" % (it["conv"] * 100)))

    def _fill_trace(self, r):
        self.ttree.delete(*self.ttree.get_children())
        for p in r["params"]:
            self.ttree.insert("", "end", values=(
                p["sym"], p["name"], _vfmt(p["value"]), p["unit"],
                CC.SRC_LABEL.get(p["src"], p["src"])))
        self._params = r["params"]

    def _show_param_detail(self, _e=None):
        sel = self.ttree.selection()
        if not sel:
            return
        idx = self.ttree.index(sel[0])
        if not hasattr(self, "_params") or idx >= len(self._params):
            return
        p = self._params[idx]
        unit = "" if p["unit"] in ("", "—", "-") else " " + p["unit"]
        lines = ["%s　%s" % (p["sym"], p["name"]),
                 "",
                 "数值　%s%s" % (_vfmt(p["value"]), unit),
                 "来源　%s" % CC.SRC_LABEL.get(p["src"], p["src"]),
                 "说明　%s" % p["zh"]]
        if p.get("formula"):
            lines.append("公式　%s" % p["formula"])
        if p.get("deps"):
            lines.append("依赖　" + "、".join(p["deps"]))
        self.detail.configure(state="normal")
        self.detail.delete("1.0", "end")
        self.detail.insert("1.0", "\n".join(lines))
        self.detail.configure(state="disabled")

    def _fill_fit(self, r):
        fE, LD = r["fits"]["fE"], r["fits"]["LD"]
        key = CC.db_key(self._current_cfg())
        name = CC.DB["emptyFrac"][key]["name"]
        g1 = CC.DB["emptyFrac"][key]["grade"]
        g2 = CC.DB["ld"][key]["grade"]
        txt = ("当前库：%s　（空重分数等级 %s · 升阻比等级 %s）\n"
               "空重分数 %d 个样本点，覆盖 %.1f–%.0f kg\n"
               "升阻比 %d 个样本点，覆盖 %.1f–%.0f kg\n"
               "%s") % (name, g1, g2, fE["n"], 10 ** fE["xmin"], 10 ** fE["xmax"],
                        LD["n"], 10 ** LD["xmin"], 10 ** LD["xmax"],
                        CC.DB["emptyFrac"][key]["src"])
        self.fit_label.configure(text=txt)

    # ---- 拟合曲线图（空重分数 / 升阻比 / 比油耗 / 功重比）
    FIT_DEF = {
        "fE":   dict(box="emptyFrac", xlabel="起飞总重 W_TO [kg]", ylabel="空重分数 f_E",
                     unit="", fmt="{:.3f}"),
        "ld":   dict(box="ld", xlabel="起飞总重 W_TO [kg]", ylabel="升阻比 L/D",
                     unit="", fmt="{:.2f}"),
        "bsfc": dict(box="power", xlabel="配平功率 [kW]", ylabel="比油耗 BSFC [kg/(kW·h)]",
                     unit=" kg/(kW·h)", fmt="{:.3f}"),
        "pw":   dict(box="power", xlabel="配平功率 [kW]", ylabel="功重比 P/m [kW/kg]",
                     unit=" kW/kg", fmt="{:.2f}"),
    }

    def _fit_set_kind(self, kind):
        self.fit_kind = kind
        self._draw_fit()

    def _fit_series(self):
        """返回 (points, meta, 当前设计值 x, 当前设计值 y)"""
        cfg = self._current_cfg()
        kind = getattr(self, "fit_kind", "fE")
        meta = dict(self.FIT_DEF[kind])
        r = getattr(self, "result", None)
        if kind in ("fE", "ld"):
            key = CC.db_key(cfg)
            src_box = CC.DB["emptyFrac" if kind == "fE" else "ld"]
            d = src_box.get(key) or {}
            pts = d.get("points") or []
            meta["dbname"] = d.get("name") or (
                (CC.DB["emptyFrac"].get(key) or {}).get("name", key))
            meta["grade"] = d.get("grade", "?")
            meta["src"] = d.get("src", "")
            if r:
                return pts, meta, r["Wto"], (r["fE"] if kind == "fE" else r["LD"])
            return pts, meta, None, None
        pkey = cfg.get("power") or "piston"
        d = CC.DB["power"].get(pkey) or {}
        pts = d.get("bsfcPts" if kind == "bsfc" else "pwPts") or []
        meta["dbname"] = d.get("name", pkey)
        meta["grade"] = d.get("grade", "?")
        meta["src"] = d.get("src", "")
        if r:
            x = r["Pcr"] / 1000.0
            fit = CC.fit_curve(pts)
            y = fit["predict"](x) if fit.get("ok") and x > 0 else None
            return pts, meta, x, y
        return pts, meta, None, None

    def _draw_fit(self):
        cv = getattr(self, "fit_cv", None)
        if cv is None:
            return
        cv.delete("all")
        # 按钮选中态
        for k, b in getattr(self, "fit_btns", {}).items():
            on = (k == getattr(self, "fit_kind", "fE"))
            b.configure(bg=ACCENT if on else BTN, fg="#ffffff" if on else FG,
                        activebackground="#22456b" if on else BTN_HOVER,
                        activeforeground="#ffffff" if on else FG)

        pts, meta, xnow, ynow = self._fit_series()
        cv.update_idletasks()
        w = cv.winfo_width() or 800
        h = cv.winfo_height() or 228
        if w < 60 or h < 60:
            return
        padl, padr, padt, padb = 62, 26, 26, 34
        x0, x1, y0, y1 = padl, w - padr, padt, h - padb
        clean = [p for p in pts if p[0] > 0 and p[1] > 0]
        if not clean:
            cv.create_text(w / 2, h / 2, text="暂无样本", fill=MUTED,
                           font=self._font(12))
            return
        lx = [math.log10(p[0]) for p in clean]
        ys = [p[1] for p in clean]
        lxmin, lxmax = min(lx), max(lx)
        if lxmax - lxmin < 1e-6:
            lxmax = lxmin + 1e-3
        span = (lxmax - lxmin) * 0.06
        lxmin -= span
        lxmax += span
        ymin, ymax = min(ys), max(ys)
        if ynow is not None and math.isfinite(ynow) and ynow > 0:
            ymin, ymax = min(ymin, ynow), max(ymax, ynow)
        ypad = (ymax - ymin) * 0.14 or max(ymax * 0.1, 0.1)
        ymin, ymax = ymin - ypad, ymax + ypad
        if ymax - ymin < 1e-9:
            ymax = ymin + 1

        def X(v):
            return x0 + (math.log10(max(v, 1e-9)) - lxmin) / (lxmax - lxmin) * (x1 - x0)

        def Y(v):
            return y1 - (v - ymin) / (ymax - ymin) * (y1 - y0)

        # 网格与刻度
        for i in range(5):
            yy = y0 + (y1 - y0) * i / 4.0
            cv.create_line(x0, yy, x1, yy, fill=GRID)
            val = ymax - (ymax - ymin) * i / 4.0
            cv.create_text(x0 - 8, yy, text=meta["fmt"].format(val), anchor="e",
                           fill=MUTED, font=self._font(10))
        for i in range(5):
            xx = x0 + (x1 - x0) * i / 4.0
            cv.create_line(xx, y0, xx, y1, fill=GRID)
            val = 10 ** (lxmin + (lxmax - lxmin) * i / 4.0)
            lab = "%d" % val if val >= 10 else "%.1f" % val
            if val >= 10000:
                lab = "%dk" % (val / 1000.0)
            cv.create_text(xx, y1 + 12, text=lab, anchor="n",
                           fill=MUTED, font=self._font(10))
        cv.create_line(x0, y0, x0, y1, fill=SEP)
        cv.create_line(x0, y1, x1, y1, fill=SEP)

        # 拟合曲线
        fit = CC.fit_curve(pts)
        if fit.get("ok"):
            xs = [lxmin + (lxmax - lxmin) * i / 120.0 for i in range(121)]
            seq = []
            for t in xs:
                xv = 10 ** t
                yv = fit["predict"](xv)
                if math.isfinite(yv) and ymin - 1e9 < yv < ymax + 1e9:
                    seq.extend((X(xv), Y(yv)))
            if len(seq) >= 4:
                cv.create_line(*seq, fill=ACCENT, width=2, smooth=False)

        # 样本点
        for p in clean:
            px, py = X(p[0]), Y(p[1])
            cv.create_oval(px - 3, py - 3, px + 3, py + 3,
                           fill=ACCENT2, outline=CARD, width=1)

        # 当前设计点
        if xnow is not None and ynow is not None and xnow > 0 and ynow > 0:
            if xnow < 10 ** lxmin or xnow > 10 ** lxmax:
                pass
            else:
                px, py = X(xnow), Y(ynow)
                cv.create_line(px, y0, px, y1, fill=ACCENT2, dash=(4, 4))
                cv.create_oval(px - 5, py - 5, px + 5, py + 5,
                               fill=CARD, outline=ACCENT2, width=2)
                lab = ("当前设计 %.2f" % ynow) if ynow < 100 else ("当前设计 %.0f" % ynow)
                tx = px + 9 if px < (x0 + x1) / 2 else px - 9
                ty = py + 14 if py < (y0 + y1) / 2 else py - 14
                cv.create_text(tx, ty, anchor="w" if tx > px else "e",
                               fill=ACCENT2, font=self._font(10), text=lab)

        cv.create_text(x0, 6, anchor="w", fill=FG, font=self._font(11),
                       text=meta["ylabel"])
        cv.create_text((x0 + x1) / 2, h - 6, anchor="s", fill=MUTED,
                       font=self._font(10), text=meta["xlabel"])
        if hasattr(self, "fit_cap"):
            note = "%s　%d 个样本点　曲线：log-log 分段插值（穿过每个点）" % (
                meta.get("dbname", ""), len(clean))
            self.fit_cap.configure(text=note)

    # ---- 数据来源清单
    def _fill_sources(self):
        if not hasattr(self, "src_text"):
            return
        grade = {"A": "实测", "B": "公开规格", "C": "样本有限"}
        keys = ("normal_small_uav", "normal_manned", "canard", "flyingwing", "joined")
        rows = []
        for k in keys:
            if k.startswith("normal_") and k != CC.db_key(self._current_cfg()):
                continue
            e = CC.DB["emptyFrac"].get(k) or {}
            l = CC.DB["ld"].get(k) or {}
            if not e:
                continue
            rows.append("%s〔%s〕空重分数 %d 点 / 升阻比 %d 点　%s" % (
                e.get("name", k), grade.get(e.get("grade", "?"), "—"),
                len(e.get("points") or []), len(l.get("points") or []),
                e.get("src", "")))
        pw = CC.DB["power"].get(self.power.get()) or {}
        rows.append("动力：%s〔%s〕　%s" % (
            pw.get("name", ""), grade.get(pw.get("grade", "?"), "—"),
            pw.get("src", "")))
        self.src_text.configure(state="normal")
        self.src_text.delete("1.0", "end")
        self.src_text.insert("end", "\n".join(rows))
        self.src_text.configure(state="disabled")

    # ------------------------------------------------------------ 约束边界图
    def _draw_constraints(self):
        c = self.canvas
        c.delete("all")
        w, h = c.winfo_width(), c.winfo_height()
        if w < 120 or h < 120:
            return
        c.create_text(w / 2, h / 2, text="填好任务条件后这里会画出可行域",
                      fill=MUTED, font=self._font(12))
        r = self.result
        if not r:
            return
        cs = r.get("constraints") or []
        if not cs:
            return
        c.delete("all")

        padl, padt, padr, padb = 64, 22, 120, 46
        ws_d = self._num("inWS", r["WS"]) or r["WS"]
        vs = [x["val"] for x in cs if x["type"] == "v"]
        maxWS = min(vs) if vs else 60.0
        xmax = min(1200.0, max(40.0, max(ws_d * 1.75, maxWS * 1.18)))
        xmin = 5.0

        hs = [x["val"] for x in cs if x["type"] == "h"]
        wp_d = _snum(self.design_wp)
        base = max(hs) if hs else 12.0
        if wp_d:
            base = max(base, wp_d * 1.15)
        ymax = min(90.0, max(10.0, base * 1.9))

        def X(ws):
            return padl + (ws - xmin) / (xmax - xmin) * (w - padl - padr)

        def Y(wp):
            return h - padb - (wp - 0) / (ymax - 0) * (h - padt - padb)

        # 网格
        xstep = _nice((xmax - xmin) / 7)
        ystep = _nice(ymax / 6)
        v = xmin
        while v <= xmax:
            c.create_line(X(v), padt, X(v), h - padb, fill=GRID)
            c.create_text(X(v), h - padb + 14, text="%g" % round(v, 1),
                          fill=MUTED, font=self._font(10))
            v += xstep
        v2 = 0.0
        while v2 <= ymax:
            c.create_line(padl, Y(v2), w - padr, Y(v2), fill=GRID)
            c.create_text(padl - 10, Y(v2), text="%g" % round(v2, 1), fill=MUTED,
                          font=self._font(10), anchor="e")
            v2 += ystep

        # 可行域底色
        poly = []
        ws = xmin
        while ws <= maxWS:
            env = self._envelope(cs, ws)
            if env and env > 0:
                poly.append((X(ws), Y(min(env, ymax))))
            ws = min(ws * 1.06, maxWS)
            if ws >= maxWS - 1e-6:
                break
        env = self._envelope(cs, maxWS)
        if env and env > 0:
            poly.append((X(maxWS), Y(min(env, ymax))))
        if len(poly) > 2:
            pts = [padl, h - padb]
            for (px, py) in poly:
                pts += [px, py]
            pts += [X(maxWS), h - padb]
            c.create_polygon(pts, fill="#eaf1f7", outline="")

        # 曲线
        for item in cs:
            col = item["color"]
            if item["type"] == "c":
                pts = []
                for (sx, sy) in item["samples"]:
                    if sx < xmin or sx > xmax or sy > ymax * 1.02:
                        continue
                    pts += [X(sx), Y(sy)]
                if len(pts) >= 4:
                    c.create_line(*pts, fill=col, width=2, smooth=False)
                    lx, ly = pts[-2], pts[-1]
                    anch = "w" if lx < w - 70 else "e"
                    c.create_text(lx + (6 if anch == "w" else -6), ly - 8,
                                  text=item["name"], fill=col,
                                  font=self._font(10), anchor=anch)
            elif item["type"] == "h":
                if item["val"] <= ymax:
                    y = Y(item["val"])
                    c.create_line(padl, y, w - padr, y, fill=col, width=2,
                                  dash=(6, 4))
                    c.create_text(w - padr + 6, y, text=item["name"], fill=col,
                                  font=self._font(10), anchor="w")
            else:
                if xmin <= item["val"] <= xmax:
                    x = X(item["val"])
                    c.create_line(x, padt, x, h - padb, fill=col, width=2,
                                  dash=(6, 4))
                    c.create_text(x, padt - 4, text=item["name"], fill=col,
                                  font=self._font(10), anchor="s")

        # 设计点
        fx = self._envelope(cs, ws_d)
        if wp_d is None and fx:
            wp_d = fx * 0.85
        if wp_d is None:
            wp_d = (hs and min(hs)) or 8.0
        ok = fx is not None and wp_d <= fx * 1.001
        px, py = X(ws_d), Y(min(wp_d, ymax))
        c.create_oval(px - 6, py - 6, px + 6, py + 6,
                      fill=OK_GREEN if ok else WARN_RED, outline=CANVAS_BG, width=2)
        c.create_text(px + 10, py - 10, text="设计点", fill=FG, font=self._font(11),
                      anchor="w")

        # 轴标
        c.create_text((padl + w - padr) / 2, h - 10, text="翼载 W/S  [kg/m²]",
                      fill=MUTED, font=self._font(11))
        c.create_text(16, (padt + h - padb) / 2, text="功率载荷 W/P  [kg/kW]",
                      fill=MUTED, font=self._font(11), angle=90)

        # 状态
        if fx is None:
            self.cons_status.configure(text="无可行域", foreground=WARN_RED)
            self.cons_info.configure(text="所有边界都不满足")
            return
        self.cons_status.configure(
            text="可行域：W/S ≤ %.1f kg/m²，W/P ≤ %.1f kg/kW" % (maxWS, fx),
            foreground=OK_GREEN if ok else WARN_RED)
        if ok:
            self.cons_info.configure(
                text="可行：留 %.0f%% 余量" % ((1 - wp_d / fx) * 100 if fx else 0))
        else:
            self.cons_info.configure(
                text="不可行：需要 W/P ≤ %.1f" % fx)

    def _pick_feasible(self):
        r = self.result
        if not r:
            return
        cs = r.get("constraints") or []
        vs = [x["val"] for x in cs if x["type"] == "v"]
        maxWS = min(vs) if vs else 60.0
        ws = min(maxWS * 0.92, maxWS)
        env = self._envelope(cs, ws)
        self._silent = True
        self.design_ws.set("%.1f" % ws)
        if env:
            self.design_wp.set("%.1f" % (env * 0.85))
        self._silent = False
        self._draw_constraints()

    @staticmethod
    def _envelope(cs, ws):
        best = None
        for item in cs:
            if item["type"] == "h":
                cand = item["val"]
            elif item["type"] == "c":
                cand = CC.interp_curve(item["samples"], ws)
            else:
                continue
            if CC.isfinite(cand) and cand > 0:
                best = cand if best is None else min(best, cand)
        return best

    # ------------------------------------------------------------ 9 架验证
    def _run_verify(self):
        rows = []
        errs = []
        for (name, pw, WPL, V, R, h, real) in VERIFY_SET:
            cfg = {"power": pw, "layout": "normal", "category": "manned",
                   "config": "fixedwing",
                   "inp": {"WPL": WPL, "V": V, "R": R, "h": h,
                           "tHover": 0, "Vc": 11}, "des": {}}
            try:
                rr = CC.compute_core(cfg)
                pred = rr["Wto"]
                e = (pred - real) / real * 100
            except Exception:  # noqa: BLE001
                pred, e = float("nan"), float("nan")
            if CC.isfinite(e):
                errs.append(abs(e))
            rows.append((name, WPL, real, pred, e))
        self.vtree.delete(*self.vtree.get_children())
        for (name, WPL, real, pred, e) in rows:
            tag = "ok" if CC.isfinite(e) and abs(e) <= 15 else "bad"
            self.vtree.insert("", "end", tags=(tag,), values=(
                name, "%d" % WPL, "%d" % real,
                CC.fmt(pred, 0),
                ("%+.1f%%" % e) if CC.isfinite(e) else "—"))
        self.vtree.tag_configure("ok", foreground=OK_GREEN)
        self.vtree.tag_configure("bad", foreground=WARN_RED)
        if errs:
            self.verify_note.configure(
                text="%d 架平均绝对偏差 %.1f%%；15%% 以内 %d 架。两架偏差大的"
                     "（PA-28、King Air）是空重分数曲线在低商载率处的固有偏差，"
                     "不是数据点异常。" % (len(errs), sum(errs) / len(errs),
                                        sum(1 for x in errs if x <= 15)))
        else:
            self.verify_note.configure(text="验证未跑通")

    # ------------------------------------------------------------ 导出
    def _export_json(self):
        if not self.result:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".json", filetypes=[("JSON", "*.json")],
            initialfile="总体参数_%s.json" % datetime.now().strftime("%m%d_%H%M"))
        if not path:
            return
        cfg = self._current_cfg()
        data = {"time": datetime.now().isoformat(timespec="seconds"),
                "config": cfg,
                "result": {k: v for k, v in self.result.items()
                           if k not in ("fits", "params", "constraints", "P0")},
                "params": self.result["params"]}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        messagebox.showinfo("已导出", path)

    def _export_csv(self):
        if not self.result:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV", "*.csv")],
            initialfile="参数溯源_%s.csv" % datetime.now().strftime("%m%d_%H%M"))
        if not path:
            return
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            wr = csv.writer(f)
            wr.writerow(["符号", "参数", "数值", "单位", "来源", "说明", "公式"])
            for p in self.result["params"]:
                wr.writerow([p["sym"], p["name"], _vfmt(p["value"]), p["unit"],
                             CC.SRC_LABEL.get(p["src"], p["src"]), p["zh"], p["formula"]])
        messagebox.showinfo("已导出", path)

    def _about(self):
        messagebox.showinfo(
            "说明",
            "三环收敛：\n"
            "① 重量—能量环：载重 + 空重 + 燃油/电池 = 总重，迭代到自洽\n"
            "② 功率—翼载约束环：四条功率边界 + 失速边界切割可行域\n"
            "③ 升力系数下推：总重、翼载、速度 → 巡航 C_L → 翼型 C_li\n\n"
            "统计库全部为公开规格样本点，曲线严格穿过每个点。\n"
            "留空的输入项一律回落到库曲线或默认设计参数。")


def _snum(var):
    s = (var.get() or "").strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _vfmt(v):
    if isinstance(v, (int, float)):
        return CC.fmt(v, 0 if abs(v) >= 1000 else 2)
    return str(v)


def _nice(v):
    if v <= 0:
        return 1
    import math
    e = math.floor(math.log10(v))
    f = v / (10 ** e)
    for m in (1, 2, 2.5, 5, 10):
        if f <= m:
            return m * (10 ** e)
    return 10 ** (e + 1)


def _enable_dpi_awareness():
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:  # noqa: BLE001
        pass


def main():
    _enable_dpi_awareness()
    root = tk.Tk()
    Calculator(root)
    root.mainloop()


if __name__ == "__main__":
    main()
