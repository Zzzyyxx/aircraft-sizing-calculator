# -*- coding: utf-8 -*-
"""
calc_core.py —— 飞机总体参数计算内核（纯函数，无 UI 依赖）
由 总体参数计算器.html v3.2 的计算链逐条移植而来。

三环：重量—能量环 → 功率—翼载约束环 → 升力系数下推。
"""

import math

G = 9.80665
RHO0 = 1.225


def rho_hw(h):
    """ISA 标准大气：ρ = ρ0·(1 − 2.2557e-5·h)^4.2559"""
    return RHO0 * max(0.05, 1.0 - 2.2557e-5 * h) ** 4.2559


def fmt(v, n=2):
    if v is None or not isfinite(v):
        return "—"
    return ("%.0f" % v) if abs(v) >= 10000 else ("%.*f" % (n, v))


def fmtg(v, n=3):
    if v is None or not isfinite(v):
        return "—"
    return "%.*g" % (n, v)


def isfinite(v):
    try:
        return v is not None and math.isfinite(v)
    except (TypeError, ValueError):
        return False


# ============================================================
# 统计库
# ============================================================
DB = {
    "emptyFrac": {
        "normal_small_uav": {
            "name": "常规 · 小型无人机", "grade": "B",
            "src": "公开规格：DJI 系列 / 小型固定翼与多旋翼 UAV（<250 kg）；大型无人机真实样本不足 10 个，未建库",
            "points": [
                [0.72, 0.76], [0.895, 0.742], [1.2, 0.68], [1.4, 0.7], [1.6, 0.64],
                [2.0, 0.62], [2.8, 0.6], [3, 0.58], [4, 0.55], [4.5, 0.55],
                [5, 0.54], [6, 0.52], [7.0, 0.53], [8, 0.5], [9.5, 0.51],
                [10, 0.5], [12, 0.48], [14, 0.49], [15, 0.47], [18, 0.48],
                [20, 0.47], [25, 0.45], [28, 0.46], [30, 0.44], [35, 0.42],
                [40, 0.44], [45, 0.3], [60, 0.38], [70, 0.41], [90, 0.4],
                [110, 0.42], [120, 0.41], [150, 0.42], [165, 0.44], [200, 0.45],
                [230, 0.46], [250, 0.47],
            ]},
        "normal_manned": {
            "name": "常规 · 有人机", "grade": "B",
            "src": "公开规格：Cessna / Piper / Cirrus / Tecnam / Beech / ATR / CRJ / A320 / B737 / B777 / A380 / C-130 / C-17",
            "points": [
                [1055, 0.6], [1080, 0.6], [1111, 0.663], [1157, 0.663], [1200, 0.5],
                [1230, 0.67], [1315, 0.58], [1385, 0.6], [1406, 0.636], [1450, 0.62],
                [1500, 0.64], [1524, 0.58], [1542, 0.58], [1633, 0.45], [1720, 0.6],
                [1785, 0.7], [1794, 0.58], [1999, 0.7], [2087, 0.62], [2130, 0.58],
                [2155, 0.6], [2177, 0.62], [2400, 0.62], [2500, 0.6], [2727, 0.56],
                [3000, 0.6], [3500, 0.62], [3629, 0.591], [3935, 0.55], [3969, 0.59],
                [4200, 0.6], [4581, 0.6], [4740, 0.593], [4750, 0.55], [4950, 0.69],
                [5500, 0.58], [6300, 0.63], [6804, 0.663], [8000, 0.59], [8100, 0.62],
                [10000, 0.57], [12000, 0.6], [17960, 0.61], [18000, 0.58], [23000, 0.587],
                [26000, 0.58], [29574, 0.581], [33000, 0.57], [38317, 0.56], [45000, 0.56],
                [45132, 0.53], [52290, 0.553], [60000, 0.54], [70307, 0.488], [70900, 0.522],
                [75500, 0.54], [78000, 0.546], [79016, 0.524], [82190, 0.548], [97000, 0.517],
                [115680, 0.505], [141000, 0.539], [186880, 0.46], [190000, 0.484], [242000, 0.514],
                [254000, 0.507], [265350, 0.483], [280000, 0.509], [351530, 0.477], [575000, 0.481],
            ]},
        "canard": {
            "name": "鸭翼布局", "grade": "C", "src": "样本有限：Rutan 系列 + 鸭翼 UAV",
            "points": [[0.4, 0.72], [1.1, 0.65], [2.3, 0.61], [6.5, 0.58],
                       [18, 0.56], [100, 0.535], [600, 0.62], [3000, 0.50]]},
        "flyingwing": {
            "name": "飞翼布局", "grade": "C", "src": "样本有限：小型飞翼 UAV + BWB 概念",
            "points": [[0.3, 0.72], [1.2, 0.67], [5, 0.62], [20, 0.58],
                       [100, 0.54], [650, 0.51], [3000, 0.49], [20000, 0.46]]},
        "joined": {
            "name": "连翼布局", "grade": "C", "src": "样本有限：连翼 UAV + 箱式翼概念",
            "points": [[0.35, 0.74], [1.5, 0.65], [6.8, 0.59], [32, 0.55],
                       [300, 0.505], [2700, 0.475], [20000, 0.46]]},
    },
    "ld": {
        "normal_small_uav": {
            "grade": "B", "src": "公开规格：小型 UAV 8–15",
            "points": [
                [0.72, 8], [0.895, 8], [1.2, 10], [1.4, 9], [1.6, 11],
                [2.0, 11], [2.8, 11], [3, 10], [4, 10], [4.5, 12],
                [5, 11], [6, 11], [7.0, 12], [8, 12], [9.5, 12],
                [10, 12], [12, 12], [14, 13], [15, 13], [18, 13],
                [20, 13], [25, 13], [28, 13], [30, 13], [35, 12],
                [40, 13], [45, 10], [60, 11], [70, 12], [90, 9],
                [110, 11], [120, 10], [150, 10], [165, 11], [200, 11],
                [230, 11], [250, 11],
            ]},
        "normal_manned": {
            "grade": "B", "src": "公开规格：通航 11–15 / 支线 14–16 / 窄体 16–17 / 宽体 18–19",
            "points": [
                [1055, 12], [1080, 12], [1111, 12], [1157, 12], [1200, 11],
                [1230, 14], [1315, 13], [1385, 12], [1406, 12], [1450, 12],
                [1500, 13], [1524, 12], [1542, 12], [1633, 11], [1720, 12],
                [1785, 15], [1794, 13], [1999, 15], [2087, 11], [2130, 14],
                [2155, 12], [2177, 12], [2400, 14], [2500, 12], [2727, 14],
                [3000, 13], [3500, 14], [3629, 13], [3935, 14], [3969, 13],
                [4200, 13], [4581, 14], [4740, 14], [4750, 15], [4950, 15],
                [5500, 14], [6300, 16], [6804, 14], [8000, 14], [8100, 15],
                [10000, 14], [12000, 15], [17960, 16], [18000, 14], [23000, 15],
                [26000, 15], [29574, 15], [33000, 15], [38317, 16], [45000, 16],
                [45132, 17], [52290, 16], [60000, 16], [70307, 15], [70900, 17],
                [75500, 17], [78000, 17], [79016, 17], [82190, 17], [97000, 17],
                [115680, 17], [141000, 16], [186880, 18], [190000, 17], [242000, 18],
                [254000, 19], [265350, 16], [280000, 19], [351530, 19], [575000, 19],
            ]},
        "canard": {"grade": "C", "src": "样本有限",
                   "points": [[0.4, 9], [1.6, 11], [6.5, 12.3], [25, 13],
                              [100, 13.5], [600, 13], [3000, 14.5]]},
        "flyingwing": {"grade": "C", "src": "样本有限（飞翼升阻比优势）",
                       "points": [[0.3, 10], [1.2, 13], [5, 15], [20, 16.5],
                                  [100, 17.6], [650, 18.7], [3000, 19.4], [20000, 20.5]]},
        "joined": {"grade": "C", "src": "样本有限",
                   "points": [[0.35, 10], [1.5, 11.9], [6.8, 13.3], [32, 14],
                              [300, 14.7], [2700, 15.35], [20000, 16]]},
    },
    "power": {
        "piston": {"name": "活塞发动机", "grade": "B", "kind": "fuel",
                   "bsfc": 0.30, "bsfcUnit": "kg/(kW·h)", "pw": 1.1, "pwUnit": "kW/kg",
                   "src": "典型型号：Rotax 912/914、Lycoming IO-360、Continental IO-550、Jabiru 2200",
                   "bsfcPts": [[60, 0.35], [84, 0.33], [135, 0.29], [160, 0.28], [225, 0.27]],
                   "pwPts": [[60, 0.85], [84, 0.95], [135, 1.15], [200, 1.25], [225, 1.30]]},
        "turboprop": {"name": "涡桨发动机", "grade": "B", "kind": "fuel",
                      "bsfc": 0.28, "bsfcUnit": "kg/(kW·h)", "pw": 4.5, "pwUnit": "kW/kg",
                      "src": "典型型号：PT6A-67、PW127、AE2100、TPE331",
                      "bsfcPts": [[500, 0.32], [1000, 0.29], [1500, 0.27], [2000, 0.26], [3400, 0.25]],
                      "pwPts": [[500, 3.6], [1000, 4.4], [1500, 4.9], [2000, 5.2], [3400, 5.8]]},
        "turbofan": {"name": "涡扇 / 涡喷", "grade": "B", "kind": "fuel",
                     "bsfc": 0.27, "bsfcUnit": "kg/(kW·h) 等效", "pw": 6.5, "pwUnit": "kW/kg",
                     "src": "典型型号：CFM56-7、LEAP-1A、PW1000G、GE90-115B",
                     "bsfcPts": [[5000, 0.31], [10000, 0.29], [20000, 0.28], [60000, 0.26], [120000, 0.24]],
                     "pwPts": [[5000, 5.0], [10000, 5.8], [20000, 6.4], [60000, 7.6], [120000, 8.8]]},
        "electric": {"name": "电机 + 电池", "grade": "B", "kind": "elec",
                     "e_batt": 180, "eUnit": "Wh/kg", "pw_motor": 8, "pmUnit": "kW/kg",
                     "p_batt": 1000, "pbUnit": "W/kg",
                     "src": "NASA NTRS 20180005327（电芯 ≤200 Wh/kg）、20200007148（250 Wh/kg @2C；电机 6.6–9.9 kW/kg）",
                     "bsfcPts": [[10, 0.06], [100, 0.07], [500, 0.08], [1000, 0.08]],
                     "pwPts": [[10, 5.5], [100, 7.5], [500, 9.5], [1000, 11.0]]},
    },
}

POWER_OPTS = [
    ("piston", "活塞", "BSFC 0.25–0.35，闭式解"),
    ("turboprop", "涡桨", "BSFC 0.24–0.32"),
    ("turbofan", "涡扇 / 涡喷", "等效 BSFC 0.22–0.34"),
    ("electric", "电机 + 电池", "质量不变 → 迭代解"),
]
LAYOUT_OPTS = [
    ("normal", "常规布局", "机身 + 机翼 + 尾翼，通航运载效率的基准"),
    ("canard", "鸭翼布局", "前翼配平，机身短；升阻比与配平代价互相牵制"),
    ("flyingwing", "飞翼布局", "升阻比高、内部容积大，俯仰配平最难"),
    ("joined", "连翼布局", "箱式连翼，结构效率高，干扰阻力要单独算"),
]
CONFIG_OPTS = [
    ("fixedwing", "固定翼", "无悬停能力"),
    ("multirotor", "多旋翼", "纯旋翼升力"),
    ("tiltrotor", "倾转旋翼", "悬停 + 巡航"),
]


# ============================================================
# 曲线：log-log 分段插值（严格穿过每个样本点）
# ============================================================
def fit_curve(pts):
    clean = sorted([p for p in pts if p[0] > 0 and p[1] > 0], key=lambda p: p[0])
    n = len(clean)
    if n < 4:
        return {"ok": False, "n": n, "msg": "样本不足（<4 点）"}

    xs = [math.log10(p[0]) for p in clean]
    ys = [math.log10(p[1]) for p in clean]

    def predict(w):
        x = math.log10(max(w, 1e-6))
        if x <= xs[0]:
            k = (ys[1] - ys[0]) / ((xs[1] - xs[0]) or 1e-9)
            y = ys[0] + k * (x - xs[0])
        elif x >= xs[n - 1]:
            k = (ys[n - 1] - ys[n - 2]) / ((xs[n - 1] - xs[n - 2]) or 1e-9)
            y = ys[n - 1] + k * (x - xs[n - 1])
        else:
            lo, hi = 0, n - 1
            while hi - lo > 1:
                mid = (lo + hi) >> 1
                if xs[mid] <= x:
                    lo = mid
                else:
                    hi = mid
            t = (x - xs[lo]) / ((xs[hi] - xs[lo]) or 1e-9)
            y = ys[lo] + t * (ys[hi] - ys[lo])
        return 10 ** y

    return {"ok": True, "n": n, "interp": True,
            "xmin": xs[0], "xmax": xs[n - 1], "predict": predict}


# ============================================================
# 主计算
# ============================================================
def db_key(cfg):
    lay = cfg["layout"]
    if lay != "normal":
        return lay
    return "normal_small_uav" if cfg.get("category") == "uav" else "normal_manned"


def compute_core(cfg):
    """cfg = {power, layout, category, config, inp{WPL,V,R,h,tHover,Vc}, des{...}}"""
    I = cfg["inp"]
    O = cfg.get("des", {})
    P0 = DB["power"][cfg["power"]]
    rho = rho_hw(I["h"])
    V = (I.get("V") or 0) / 3.6
    # 构型：fixedwing / multirotor / tiltrotor
    # 倾转旋翼的悬停只是起降与转换，通常 1–2 min；持续垂直爬升是直升机指标，不该套在它头上。
    kind = cfg.get("config") or "fixedwing"
    is_elec = cfg["power"] == "electric"
    is_vtol = kind != "fixedwing"
    is_multi = kind == "multirotor"
    is_tilt = kind == "tiltrotor"
    Vc = float(I.get("Vc") or 0)            # 爬升率，m/s
    if Vc <= 0.1:
        Vc = 0.0
    hTrans = float(I.get("hTrans") or 0)    # 倾转旋翼完成转换的高度，m

    fEf = fit_curve(DB["emptyFrac"][db_key(cfg)]["points"])
    LDf = fit_curve(DB["ld"][db_key(cfg)]["points"])

    etaP = O.get("etaP") or 0.78
    etaT = O.get("etaT") or 0.96
    FM = O.get("FM") or 0.70
    AR = O.get("AR") or 6.0
    reserve = O.get("reserve")
    reserve = 0.20 if reserve is None else reserve
    CLmax = O.get("CLmax") or 1.4
    NB = O.get("NB") or 6
    Dr = O.get("D") or 0.38
    Arot = NB * math.pi / 4 * Dr * Dr
    ldCruise = O.get("ldCruise")
    ldCruise = 0.85 if ldCruise is None else ldCruise
    fTaxi = O.get("fTaxi")
    fTaxi = 0.06 if fTaxi is None else fTaxi
    fDescent = O.get("fDescent")
    fDescent = 0.03 if fDescent is None else fDescent

    WPL = I["WPL"]
    res = {"warn": [], "iters": [], "profile": []}

    # ---- 过渡段功率系数与机载设备功率：都是可核对的显式假设，不再是藏在公式里的常数
    kTrans = 1.15 if O.get("kTrans") is None else float(O["kTrans"])
    pAux = 40.0 if O.get("P_aux") is None else float(O["P_aux"])

    # ---- 剖面时间：一次算好，能量、燃油、界面显示全部用它，不再各算一套
    tCr = I["R"] * 1000 / V if V > 0 else 0.0
    if is_tilt:
        tHov = float(I.get("tHover") or 0) * 60.0     # 起降悬停 + 转换 + 进近，通常 1–2 min
        tTrans = 20.0                                 # 转换段按 20 s 估
        tClimb = max(0.0, I["h"] - hTrans) / Vc if Vc > 0 else 0.0
    elif is_multi:
        tHov = float(I.get("tHover") or 0) * 60.0
        tTrans = 20.0
        tClimb = I["h"] / Vc if Vc > 0 else 0.0
    else:
        tHov = 0.0
        tTrans = 0.0
        tClimb = I["h"] / Vc if Vc > 0 else 0.0
    tMission = tHov + tTrans + tClimb + tCr

    def state(Wt):
        if O.get("fE"):
            fe = O["fE"]
        else:
            fe = min(0.85, max(0.12, fEf["predict"](Wt)))
        if O.get("LD"):
            ld = O["LD"]
        else:
            ld = max(4.0, LDf["predict"](Wt)) * (ldCruise if Wt < 30000 else 1.0)
        W = Wt * G
        # 悬停功率：理想诱导功率 ÷ 品质因数 FM（FM 已含诱导 + 型阻损失），再除传动与电调效率。
        # 悬停时旋翼不产生前飞推力，乘螺旋桨推进效率 η_prop 属于重复计入损失。
        ph = (W ** 1.5 / math.sqrt(2 * rho * Arot) / FM / etaT) if is_vtol else 0.0
        pcr = W * V / (ld * etaP * etaT)
        pcl_inc = W * Vc / (etaP * etaT)
        # 机翼模式爬升（固定翼 / 倾转旋翼转换之后）与直升机式垂直爬升（多旋翼）是两件事
        pcl_fwd = pcr + pcl_inc
        pcl_vt = ph + pcl_inc
        pc = pcl_vt if is_multi else pcl_fwd
        ptr = ph * kTrans if is_vtol else 0.0
        if is_multi:
            cases = (ph, pcl_vt, pcr)
        elif is_tilt:
            cases = (ph, ptr, pcl_fwd, pcr)
        else:
            cases = (pcl_fwd, pcr)
        ppk = max([v for v in cases if v > 0] or [0])

        # ---- 剖面：功率 × 时长 = 能量。界面与重量闭合共用这张表
        segs = []
        if is_vtol and ph > 0 and tHov > 0:
            segs.append(("悬停", ph, tHov, "起降悬停与进近"))
        if is_vtol and ptr > 0 and tTrans > 0:
            segs.append(("过渡", ptr, tTrans, "≈%.2f×悬停功率" % kTrans))
        if pc > 0 and tClimb > 0:
            segs.append(("爬升", pc, tClimb,
                         "竖直爬升" if is_multi else "机翼模式爬升"))
        if pcr > 0 and tCr > 0:
            segs.append(("巡航", pcr, tCr, "重量×速度÷(L/D×效率)"))
        if pAux > 0 and tMission > 0:
            segs.append(("机载设备", pAux, tMission, "航电/任务载荷常开"))
        E_task_Wh = sum(p * t for _, p, t, _ in segs) / 3600.0

        fuel = batt = ff = 0.0
        if is_elec:
            Et = E_task_Wh * (1 + reserve)
            m1 = Et / ((O.get("DoD") or 0.85) * (O.get("e_batt") or P0.get("e_batt", 180)))
            m2 = ppk / (O.get("p_batt") or 1000)
            batt = max(m1, m2)
        else:
            bsfc = (O.get("bsfc") or P0["bsfc"]) / 3.6e6      # kg/J
            lnR = (I["R"] * 1000) * G * bsfc / (etaP * ld)
            ffCruise = 1 - math.exp(-lnR)
            # 爬升油耗只计"把重量举上去"的那一份（势能项），与已验证的 9 架口径一致
            fuelClimb = (Wt * G * Vc / (etaP * etaT)) * tClimb * bsfc
            fuelVTOL = (ph * tHov + ptr * tTrans) * bsfc       # J × kg/J
            fuelAux = pAux * tMission * bsfc
            fuelDescent = fDescent * ffCruise * Wt
            fuelTaxi = fTaxi * ffCruise * Wt
            reserveHold = W * V / ld * 2700 * bsfc
            reservePct = 0.05 * ffCruise * Wt
            reserveFair = max(reserveHold, reservePct)
            fuelTask0 = (ffCruise * Wt + fuelClimb + fuelVTOL + fuelAux
                         + fuelDescent + fuelTaxi + reserveFair)
            bigCorr = (30000.0 / Wt) ** 0.20 if Wt > 30000 else 1.0
            fuel = fuelTask0 * bigCorr
            ff = fuel / Wt
            # 燃油剖面：与重量闭合用的是同一批项，逐条相加就等于 fuel
            fsegs = []
            if fuelVTOL > 0:
                if is_tilt and ph * tHov > 0 and ptr * tTrans > 0:
                    fsegs.append(("悬停", ph * tHov * bsfc))
                    fsegs.append(("过渡", ptr * tTrans * bsfc))
                else:
                    fsegs.append(("悬停/过渡", fuelVTOL))
            if fuelClimb > 0:
                fsegs.append(("爬升", fuelClimb))
            fsegs.append(("巡航", ffCruise * Wt))
            if fuelAux > 0:
                fsegs.append(("机载设备", fuelAux))
            if fuelDescent > 0:
                fsegs.append(("下降", fuelDescent))
            if fuelTaxi > 0:
                fsegs.append(("滑行", fuelTaxi))
            if reserveFair > 0:
                fsegs.append(("备份", reserveFair))
            if bigCorr != 1.0:
                fsegs.append(("大机修正 ×%.2f" % bigCorr,
                              (bigCorr - 1.0) * fuelTask0))
        return {"fe": fe, "ld": ld, "ph": ph, "pc": pc, "pcr": pcr, "ptr": ptr,
                "ppk": ppk, "fuel": fuel, "batt": batt, "ff": ff,
                "segs": segs, "E_Wh": E_task_Wh,
                "fsegs": fsegs if not is_elec else None,
                "Et": Et if is_elec else 0.0,
                "m1": m1 if is_elec else 0.0, "m2": m2 if is_elec else 0.0}

    def resid(Wt):
        s = state(Wt)
        return Wt - (WPL + s["fe"] * Wt + (s["batt"] if is_elec else s["fuel"]))

    # 多根扫描：插值曲线非单调时 resid 可能有多个零点
    roots = []
    brackets = []
    prevW = WPL * 1.02
    prevR = resid(prevW)
    w = WPL * 1.06
    while w <= WPL * 60:
        rr = resid(w)
        if isfinite(rr) and isfinite(prevR) and rr * prevR < 0:
            a, b = prevW, w
            for _ in range(70):
                m = (a + b) / 2
                if resid(m) * resid(a) <= 0:
                    b = m
                else:
                    a = m
            roots.append((a + b) / 2)
            brackets.append((prevW, w))
        prevW, prevR = w, rr
        w *= 1.06

    solved = False
    Wto = WPL / 0.45
    if not roots:
        res["warn"].append("重量闭合无解：在载重的 1–60 倍范围内找不到自洽总重")
        # 兜底：找一个残差最小的点（结果标记为无效，不当作方案）
        best, bestv = WPL / 0.45, 1e18
        w = WPL * 1.1
        while w <= WPL * 40:
            v = abs(resid(w))
            if v < bestv:
                bestv, best = v, w
            w *= 1.03
        Wto = best
    else:
        valid = [x for x in roots if 0.10 < WPL / x < 0.50]
        pool = valid if valid else roots
        target = 0.38 if (cfg["layout"] == "normal" and cfg.get("category") == "uav") else 0.22
        Wto = min(pool, key=lambda x: abs(WPL / x - target))
        solved = True
        # 求解记录：把二分法真实的区间收缩过程记下来（不是围绕结果编的数字）
        idx = roots.index(Wto) if Wto in roots else 0
        a, b = brackets[idx]
        for k in range(1, 13):
            m = (a + b) / 2
            rm = resid(m)
            st = state(m)
            res["iters"].append({
                "k": k, "Wto": m, "fE": st["fe"], "LD": st["ld"],
                "fuel": st["fuel"], "mB": st["batt"],
                "conv": abs(b - a) / 2.0,
                "resid": rm,
            })
            if resid(m) * resid(a) <= 0:
                b = m
            else:
                a = m

    fin = state(Wto)
    fE, LD = fin["fe"], fin["ld"]
    WE = fE * Wto
    # 翼载是设计变量：没给时按「失速速度 ≈ 0.35V」反推一个量级合理的起点
    ws_def = min(900.0, max(15.0, 0.5 * RHO0 * (0.35 * V) ** 2 * CLmax / G)) if V > 0 else 17.0
    WS = O.get("WS") or ws_def
    Sw = Wto / WS
    bs = math.sqrt(AR * Sw)
    Vapp = (O.get("Vapp") / 3.6) if O.get("Vapp") else V * 0.6
    Vstall = math.sqrt(2 * WS * G / (RHO0 * CLmax))
    CLc = 2 * (Wto * 0.98) * G / (rho * V * V * Sw) if V > 0 and Sw > 0 else 0
    CLi = CLc / 0.95 / 0.90

    r = {
        "Wto": Wto, "fE": fE, "LD": LD, "rho": rho, "WS": WS, "S": Sw, "b": bs,
        "WE": WE, "Wfuel": fin["fuel"], "mBatt": fin["batt"], "fF": fin["ff"],
        "Phov": fin["ph"], "Pcl": fin["pc"], "Pcr": fin["pcr"], "Ppk": fin["ppk"],
        "Ptr": fin["ptr"], "Vstall": Vstall, "Vapp": Vapp,
        "CLc": CLc, "CLi": CLi, "isElec": is_elec, "isVTOL": is_vtol,
        "isMulti": is_multi, "isTilt": is_tilt,
        "tHoverMin": float(I.get("tHover") or 0), "hTrans": hTrans, "kind": kind,
        "AR": AR, "CLmax": CLmax, "etaP": etaP, "etaT": etaT, "FM": FM,
        "NB": NB, "D": Dr, "Arot": Arot, "reserve": reserve if is_elec else None,
        "solved": solved, "valid": solved, "roots": roots, "V": V, "Vc": Vc,
        "fits": {"fE": fEf, "LD": LDf},
        "bsfc": (O.get("bsfc") or P0["bsfc"]) if not is_elec else None,
        "P0": P0, "iters": res["iters"], "warn": res["warn"],
        # 剖面：与重量闭合同一套数字，界面直接展示，不再另算
        "profile": fin["segs"], "E_task": fin["E_Wh"] if is_elec else None,
        "fuelSegs": fin["fsegs"], "Et": fin["Et"],
        "mBattE": fin["m1"], "mBattP": fin["m2"],
        "P_aux": pAux, "kTrans": kTrans,
        "tSeg": {"hover": tHov, "trans": tTrans, "climb": tClimb, "cruise": tCr},
    }
    r["constraints"] = build_constraints(r, cfg)
    r["params"] = build_params(r, cfg)
    return r


# ============================================================
# 约束边界（9 类）
# ============================================================
def build_constraints(res, cfg):
    I = cfg["inp"]
    O = cfg.get("des", {})
    Wto, rho = res["Wto"], res["rho"]
    V = (I.get("V") or 0) / 3.6
    CLmax = O.get("CLmax") or 1.4
    etaP = O.get("etaP") or 0.78
    etaT = O.get("etaT") or 0.96
    ARc = O.get("AR") or 6
    eO = O.get("eOswald") or 0.85
    W = Wto * G
    out = []
    if Wto <= 0 or V <= 0:
        return out

    # 把阻力极线标定到重量闭合用的升阻比上：在设计翼载处极线给出的 L/D 与统计 L/D 相等，
    # 这样约束图与重量闭合用的是同一套阻力模型（此前是两套，图上可行不等于闭合可行）。
    CLd = 2 * res["WS"] * G / (rho * V * V) if res["WS"] > 0 else 0.3
    cdInd = CLd * CLd / (math.pi * eO * ARc)
    Cd0 = O.get("Cd0")
    if Cd0 is None:
        Cd0 = CLd / max(2.0, res["LD"]) - cdInd
        Cd0 = max(0.006, min(0.08, Cd0))
    res["Cd0"] = Cd0
    res["CLd"] = CLd

    def p_cruise(ws):
        S = Wto / ws
        CL = 2 * ws * G / (rho * V * V)
        Cd = Cd0 + CL * CL / (math.pi * eO * ARc)
        return 0.5 * rho * V * V * V * S * Cd / (etaP * etaT)

    def to_wp(pw):        # W → W/P (kg/kW)
        return Wto * 1000.0 / pw if pw > 0 else None

    def curve(cid, name, fn, color, zh):
        samples = []
        ws = 5.0
        while ws <= 1200:
            pw = fn(ws)
            if isfinite(pw) and pw > 0:
                wpv = to_wp(pw)
                if isfinite(wpv) and wpv > 0:
                    samples.append((ws, wpv))
            ws *= 1.18
        if len(samples) > 4:
            out.append({"id": cid, "name": name, "type": "c",
                        "samples": samples, "color": color, "zh": zh})

    def hline(cid, name, pw, color, zh):
        if pw > 0 and isfinite(pw):
            v = to_wp(pw)
            if isfinite(v) and v > 0:
                out.append({"id": cid, "name": name, "type": "h", "val": v,
                            "color": color, "zh": zh})

    def vline(cid, name, ws, color, zh):
        if ws > 0 and isfinite(ws):
            out.append({"id": cid, "name": name, "type": "v", "val": ws,
                        "color": color, "zh": zh})

    curve("cruise", "巡航平飞", p_cruise, "#4ea1d3",
          "巡航平飞功率随翼载变化：型阻 ∝ 1/(W/S)，诱导 ∝ (W/S)")
    if O.get("gamma"):
        g = O["gamma"] / 100.0
        curve("fwdclimb", "全发爬升 %g%%" % O["gamma"],
              lambda ws: p_cruise(ws) + W * V * g / (etaP * etaT),
              "#d08a4a", "巡航功率 + 爬升梯度所需功率")
    if O.get("gammaOEI"):
        g = O["gammaOEI"] / 100.0
        curve("oei", "单发第二段 %g%%" % O["gammaOEI"],
              lambda ws: (p_cruise(ws) + W * V * g / (etaP * etaT)) * 1.9,
              "#d96b6b", "单发后剩余功率需维持的梯度")
    if O.get("gammaRoute"):
        g = O["gammaRoute"] / 100.0
        curve("route", "航路单发 %g%%" % O["gammaRoute"],
              lambda ws: (p_cruise(ws) + W * V * g / (etaP * etaT)) * 2.0,
              "#9b8ad6", "航路单发失效的最小梯度")

    if res["isVTOL"]:
        hline("hover", "悬停", res["Phov"], "#5fbf8f", "悬停功率")
        hline("trans", "过渡", res["Ptr"], "#c9a227",
              "倾转过渡段（%.2f×悬停功率）" % res.get("kTrans", 1.15))
        if O.get("Vwind"):
            Vw = O["Vwind"] * 0.5144
            hline("wind", "抗风 %g kt" % O["Vwind"],
                  res["Phov"] + W * Vw / (etaP * etaT) * 0.5, "#4a9c9c", "抗风悬停余量")

    if O.get("SL"):
        ws = O["SL"] * rho * G * CLmax * 0.30 / 1.9
        vline("sl", "着陆 %g m" % O["SL"], ws, "#8a7a5a", "着陆距离反推的翼载上限")
    if O.get("STO"):
        TWR = O.get("TWR") or (0.50 if res["isVTOL"] else 0.30)
        ws = O["STO"] * rho * G * CLmax * TWR / 1.44
        vline("sto", "起飞 %g m" % O["STO"], ws, "#7a6a99", "起飞滑跑距离反推的翼载上限")
    vline("stall", "失速 V=%.0f" % res["Vapp"],
          0.5 * RHO0 * res["Vapp"] ** 2 * CLmax / G, "#d96b6b",
          "由进场速度与最大升力系数反推的翼载上界")
    if O.get("nTurn"):
        ws = 0.5 * rho * V * V * CLmax / (O["nTurn"] * G)
        vline("turn", "盘旋 n=%g" % O["nTurn"], ws, "#6b8e5a", "盘旋过载下的翼载上限")
    return out


def interp_curve(pts, x):
    if not pts or len(pts) < 2:
        return float("nan")
    if x <= pts[0][0]:
        return pts[0][1]
    for i in range(1, len(pts)):
        if x <= pts[i][0]:
            x0, y0 = pts[i - 1]
            x1, y1 = pts[i]
            return y0 + (y1 - y0) * (x - x0) / ((x1 - x0) or 1e-9)
    return pts[-1][1]


def feasible(res, ws, wp):
    cs = res.get("constraints") or []
    max_ws = min([c["val"] for c in cs if c["type"] == "v"] + [1e9])
    max_wp = min([c["val"] for c in cs if c["type"] == "h"] + [1e9])
    for c in [x for x in cs if x["type"] == "c"]:
        v = interp_curve(c["samples"], ws)
        if isfinite(v) and v > 0:
            max_wp = min(max_wp, v)
    return {"maxWS": max_ws, "maxWP": max_wp,
            "ok": ws <= max_ws * 1.001 and wp <= max_wp * 1.001}


# ============================================================
# 参数溯源表
# ============================================================
SRC_LABEL = {"input": "输入", "calc": "计算", "stat": "统计",
             "assume": "假设", "spec": "规范"}


def build_params(res, cfg):
    I = cfg["inp"]
    rows = []

    def add(sym, name, val, unit, src, zh, formula="", deps=None):
        rows.append({"sym": sym, "name": name, "value": val, "unit": unit,
                     "src": src, "zh": zh, "formula": formula, "deps": deps or []})

    add("W_PL", "任务载重", I["WPL"], "kg", "input", "任务要求")
    add("W_TO", "起飞总重", res["Wto"], "kg", "calc",
        "三环收敛后的总重；无解时该值无效",
        "W_TO = W_PL + W_E + m_batt", ["W_PL", "f_E", "m_batt"])
    add("f_E", "空重分数", res["fE"], "—", "stat",
        "空重 ÷ 起飞总重。样本口径：OEW/MTOW，不含燃油与电池；若方案把电池计入结构重，需自行扣减",
        "f_E(W_TO)", ["W_TO"])
    add("L/D", "升阻比", res["LD"], "—", "stat",
        "库值 × 巡航系数（30 t 以下）；约束图的阻力极线按此值标定", "L/D(W_TO)×0.85", ["W_TO"])
    add("W_E", "空重", res["WE"], "kg", "calc", "空重 = 空重分数 × 起飞总重",
        "W_E = f_E·W_TO", ["f_E", "W_TO"])
    if res["isElec"]:
        add("m_batt", "电池质量", res["mBatt"], "kg", "calc",
            "能量管航程，功率管 2C", "m_batt = max(E/(DoD·e), P_peak/(P/m))", ["P_peak"])
    else:
        add("W_fuel", "燃油重量", res["Wfuel"], "kg", "calc",
            "各段燃油求和（Breguet + 爬升 + 滑行 + 备份）", "W_fuel = Σ各段", ["W_TO"])
        add("f_fuel", "燃油分数", res["fF"], "—", "calc", "燃油 ÷ 起飞总重", "f_fuel = W_fuel/W_TO")
    add("V", "巡航速度", I.get("V", 0), "km/h", "input", "任务要求")
    add("R", "航程", I.get("R", 0), "km", "input", "任务要求")
    add("h", "巡航高度", I.get("h", 0), "m", "input", "任务要求")
    add("ρ", "空气密度", res["rho"], "kg/m³", "calc",
        "ISA：ρ = ρ0(1−2.2557e-5·h)^4.2559", "ρ = ρ0·(1−2.2557e-5·h)^4.2559", ["h"])
    add("P_cruise", "巡航功率", res["Pcr"], "W", "calc",
        "巡航功率 = 重量×速度 ÷ (L/D·η)", "P = W·V/((L/D)·η_prop·η_trans)", ["W_TO", "L/D"])
    if res["isVTOL"]:
        add("A_rotor", "总桨盘面积", res["Arot"], "m²", "calc",
            "桨盘面积 = 旋翼数 × π/4 × 桨径²", "A = N·π/4·D²")
        add("P_hover", "悬停功率", res["Phov"], "W", "calc",
            "动量理论理想功率 ÷ 品质因数（FM 已含诱导与型阻损失）÷ 传动电调效率",
            "P_hover = W^1.5/√(2ρA)/FM/η_trans", ["W_TO", "A_rotor", "FM"])
        add("P_trans", "过渡功率", res["Ptr"], "W", "calc",
            "倾转过渡段功率，按悬停功率乘过渡系数（假设值，可按构型标定）",
            "P_trans = %.2f×P_hover" % res.get("kTrans", 1.15), ["P_hover"])
        if res.get("isMulti"):
            add("P_climb", "垂直爬升功率", res["Pcl"], "W", "calc",
                "悬停功率 + 竖直爬升增量", "P_climb = P_hover + W·V_c/η", ["P_hover"])
        else:
            add("P_climb", "机翼模式爬升功率", res["Pcl"], "W", "calc",
                "转换完成后由机翼承重，按固定翼爬升算", "P_climb = P_cruise + W·V_c/η", ["P_cruise"])
        if res.get("isTilt"):
            add("t_hover", "悬停与过渡时间", res.get("tHoverMin", 0), "min", "input",
                "起降悬停 + 转换 + 进近，倾转旋翼通常 1–2 min")
            add("h_trans", "转换高度", res.get("hTrans", 0), "m", "input",
                "从离地到完成倾转、进入机翼模式的高度")
    add("P_aux", "机载设备功率", res.get("P_aux", 40.0), "W", "assume",
        "航电与任务载荷常开功率，全程计入能量；默认 40 W，可在设计参数里改")
    if res["isElec"]:
        add("E_task", "任务能量", res.get("E_task") or 0, "Wh", "calc",
            "各段功率×时长之和（含机载设备），与剖面表逐行对应",
            "E = Σ P_i·t_i", ["P_hover", "P_cruise", "P_aux"])
    add("P_peak", "峰值功率", res["Ppk"], "W", "calc",
        "各剖面功率最大值", "P_peak = max(P_hover,P_climb,P_cruise,P_trans)")
    add("W/S", "翼载", res["WS"], "kg/m²", "input", "设计变量，在约束可行域内选")
    add("S", "机翼面积", res["S"], "m²", "calc", "机翼面积 = 起飞总重 ÷ 翼载",
        "S = W_TO/(W/S)", ["W_TO", "W/S"])
    add("b", "翼展", res["b"], "m", "calc", "翼展 = √(展弦比 × 机翼面积)",
        "b = √(AR·S)", ["AR", "S"])
    add("C_Lmax", "最大升力系数", res["CLmax"], "—", "spec", "翼型能力上限")
    add("V_s", "失速速度", res["Vstall"], "m/s", "calc",
        "失速速度 = √(2·(W/S)·g/(ρ0·C_Lmax))", "V_s = √(2·(W/S)·g/(ρ0·C_Lmax))", ["W/S", "C_Lmax"])
    add("V_app", "进场速度", res["Vapp"], "m/s", "calc",
        "默认取 0.6V，也可直接给定", "V_app = 0.6V")
    add("C_Lc", "巡航升力系数", res["CLc"], "—", "calc",
        "巡航升力系数 = 2·W_c/(ρ·V²·S)", "C_Lc = 2·W_c/(ρ·V²·S)", ["W_TO", "V", "S"])
    add("C_li", "翼型设计升力系数", res["CLi"], "—", "calc",
        "翼型设计升力系数 = 巡航升力系数 ÷ 0.95 ÷ 0.90", "C_li = C_Lc/0.95/0.90", ["C_Lc"])
    add("η_prop", "推进效率", res["etaP"], "—", "spec", "螺旋桨把轴功率转成推进功率的效率")
    add("η_trans", "传动效率", res["etaT"], "—", "spec", "传动与电调损失")
    add("FM", "旋翼品质因数", res["FM"], "—", "stat", "理想悬停功率与实际功率之比")
    return rows
