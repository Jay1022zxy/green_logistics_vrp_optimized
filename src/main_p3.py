# === Project path bootstrap ===
from pathlib import Path
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
# ==============================

import os
import ast
import time
import math
import random
import warnings
from copy import deepcopy

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401


# =========================================================
# 文件路径
# =========================================================
P2_ROUTES_PATH = "results/problem2/problem2_routes.csv"
P2_SUMMARY_PATH = "results/problem2/problem2_summary.csv"

DISTANCE_MATRIX_PATH = "data/raw/距离矩阵.xlsx"
TIME_WINDOW_PATH = "data/raw/时间窗.xlsx"
ORDER_PATH = "data/raw/订单信息.xlsx"

OUTPUT_RESULT_PATH = "results/problem3/problem3_event_results.csv"
OUTPUT_ROUTES_PATH = "results/problem3/problem3_event_routes.csv"
OUTPUT_ANALYSIS_PATH = "results/problem3/problem3_result_analysis.txt"
OUTPUT_FIG_DIR = "figures/problem3"


def resolve_file_path(filename):
    if os.path.exists(filename):
        return filename

    candidates = [
        os.path.join(".", filename),
        os.path.join("data", filename),
        os.path.join("附件", filename),
        os.path.join("数据", filename),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path

    for root, _, files in os.walk("."):
        for f in files:
            if f == filename:
                return os.path.join(root, f)

    return filename


# =========================================================
# 动态调度参数
# =========================================================
RANDOM_SEED = 66
P3_SEEDS = [1, 7, 21, 42, 66]

EVENT_TIME_MINUTE = 180.0       # 以 8:00 为 0，180 表示 11:00
SERVICE_TIME = 20.0

WAIT_COST_PER_MIN = 20.0 / 60.0
LATE_COST_PER_MIN = 50.0 / 60.0
CARBON_COST_PER_UNIT = 0.65

# 扰动惩罚参数
LAMBDA_ASSIGN = 35.0
LAMBDA_ARC = 8.0
LAMBDA_ROUTE = 120.0
LAMBDA_CAPACITY = 10000.0

# ALNS-VNS 参数：如果想更精细，可把 ALNS_TIME_LIMIT 调大
ALNS_ITER = 220
ALNS_TIME_LIMIT = 35.0          # 单个 seed 的时间上限，秒
REMOVE_RATIO_MIN = 0.08
REMOVE_RATIO_MAX = 0.25
START_TEMPERATURE = 1800.0
COOLING_RATE = 0.988

NEIGHBOR_ROUTE_COUNT = 6
MONTE_CARLO_SAMPLES = 50


# =========================================================
# 车辆参数
# =========================================================
VEHICLE_SPECS = {
    "fuel_3000": {"type": "fuel", "weight_cap": 3000.0, "volume_cap": 13.5, "fixed": 400.0},
    "fuel_1500": {"type": "fuel", "weight_cap": 1500.0, "volume_cap": 10.8, "fixed": 400.0},
    "fuel_1250": {"type": "fuel", "weight_cap": 1250.0, "volume_cap": 6.5, "fixed": 400.0},
    "ev_3000": {"type": "ev", "weight_cap": 3000.0, "volume_cap": 15.0, "fixed": 400.0},
    "ev_1250": {"type": "ev", "weight_cap": 1250.0, "volume_cap": 8.5, "fixed": 400.0},
}

FUEL_PRICE = 7.61
ELECTRIC_PRICE = 1.64
FUEL_CARBON_FACTOR = 2.547
ELECTRIC_CARBON_FACTOR = 0.501

COLORS = {
    "base": "#3B6EA8",
    "initial": "#8A8A8A",
    "event": "#E68632",
    "green": "#4F9D69",
    "red": "#C44E52",
    "purple": "#8E6BBE",
    "teal": "#5DA5A4",
    "grid": "#D9DEE7",
    "text": "#222222",
}


# =========================================================
# 字体
# =========================================================
def setup_chinese_font():
    candidates = ["Microsoft YaHei", "SimHei", "SimSun", "Arial Unicode MS"]
    available_fonts = {f.name for f in font_manager.fontManager.ttflist}
    for font in candidates:
        if font in available_fonts:
            plt.rcParams["font.sans-serif"] = [font]
            break
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.facecolor"] = "white"
    plt.rcParams["axes.facecolor"] = "white"
    plt.rcParams["savefig.facecolor"] = "white"


def style_axis(ax, grid_axis="y"):
    ax.grid(axis=grid_axis, linestyle="--", alpha=0.3, color=COLORS["grid"])
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


# =========================================================
# 基础读取
# =========================================================
def find_col(df, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None


def read_summary():
    if not os.path.exists(P2_SUMMARY_PATH):
        raise FileNotFoundError(f"找不到 {P2_SUMMARY_PATH}，请先运行问题二代码。")
    df = pd.read_csv(P2_SUMMARY_PATH, encoding="utf-8-sig")
    if df.empty:
        raise ValueError(f"{P2_SUMMARY_PATH} 为空。")
    return df.iloc[0].to_dict()


def read_routes():
    if not os.path.exists(P2_ROUTES_PATH):
        raise FileNotFoundError(f"找不到 {P2_ROUTES_PATH}，请先运行问题二代码。")
    df = pd.read_csv(P2_ROUTES_PATH, encoding="utf-8-sig")
    if df.empty:
        raise ValueError(f"{P2_ROUTES_PATH} 为空。")
    return df


def read_distance_matrix():
    path = resolve_file_path(DISTANCE_MATRIX_PATH)
    if not os.path.exists(path):
        warnings.warn(f"未找到 {DISTANCE_MATRIX_PATH}，距离计算将退化为 0。")
        return None
    try:
        df = pd.read_excel(path, index_col=0)
        df.index = df.index.astype(str)
        df.columns = df.columns.astype(str)
        print(f"距离矩阵已读取：{path}")
        return df
    except Exception:
        raw = pd.read_excel(path, header=None)
        raw.index = raw.index.astype(str)
        raw.columns = raw.columns.astype(str)
        print(f"距离矩阵已读取：{path}")
        return raw


def parse_time_to_minute(value):
    if pd.isna(value):
        return None
    if hasattr(value, "hour") and hasattr(value, "minute"):
        return float(value.hour * 60 + value.minute - 8 * 60)
    if isinstance(value, str):
        s = value.strip()
        if ":" in s:
            try:
                h, m = s.split(":")[:2]
                return float(int(h) * 60 + int(float(m)) - 8 * 60)
            except Exception:
                return None
        try:
            num = float(s)
            return num * 60 - 8 * 60 if num <= 24 else num
        except Exception:
            return None
    try:
        num = float(value)
        return num * 60 - 8 * 60 if num <= 24 else num
    except Exception:
        return None


def read_time_windows():
    time_windows = {}
    path = resolve_file_path(TIME_WINDOW_PATH)
    if not os.path.exists(path):
        warnings.warn(f"未找到 {TIME_WINDOW_PATH}，将使用默认时间窗 [0, 540]。")
        return time_windows

    df = pd.read_excel(path)
    print(f"时间窗已读取：{path}")

    id_col = find_col(df, ["客户编号", "客户ID", "customer_id", "CustomerID", "节点", "节点编号", "id"])
    early_col = find_col(df, ["最早到达时间", "最早时间", "最早服务时间", "start", "earliest", "a_i"])
    late_col = find_col(df, ["最晚到达时间", "最晚时间", "最晚服务时间", "end", "latest", "b_i"])

    if id_col is None:
        id_col = df.columns[0]
    if early_col is None or late_col is None:
        if len(df.columns) >= 3:
            early_col, late_col = df.columns[1], df.columns[2]
        else:
            return time_windows

    for _, row in df.iterrows():
        cid = str(row[id_col]).strip()
        if cid == "" or cid.lower() == "nan":
            continue
        a = parse_time_to_minute(row[early_col])
        b = parse_time_to_minute(row[late_col])
        time_windows[cid] = (float(0.0 if a is None else a), float(540.0 if b is None else b))
    return time_windows


def read_customer_demands():
    demands = {}
    path = resolve_file_path(ORDER_PATH)
    if not os.path.exists(path):
        warnings.warn(f"未找到 {ORDER_PATH}，将使用默认需求。")
        return demands

    df = pd.read_excel(path)
    print(f"订单信息已读取：{path}")

    id_col = find_col(df, ["客户编号", "客户ID", "customer_id", "CustomerID", "节点", "节点编号", "id"])
    weight_col = find_col(df, ["重量", "总重量", "需求重量", "weight", "重量需求"])
    volume_col = find_col(df, ["体积", "总体积", "需求体积", "volume", "体积需求"])

    if id_col is None:
        id_col = df.columns[0]
    if weight_col is None:
        for c in df.columns:
            if "重" in str(c):
                weight_col = c
                break
    if volume_col is None:
        for c in df.columns:
            if "体" in str(c):
                volume_col = c
                break

    for _, row in df.iterrows():
        cid = str(row[id_col]).strip()
        if cid == "" or cid.lower() == "nan":
            continue
        try:
            w = float(row[weight_col]) if weight_col is not None and not pd.isna(row[weight_col]) else 0.0
        except Exception:
            w = 0.0
        try:
            v = float(row[volume_col]) if volume_col is not None and not pd.isna(row[volume_col]) else 0.0
        except Exception:
            v = 0.0
        demands[cid] = (w, v)
    return demands


# =========================================================
# 路径解析
# =========================================================
def parse_nodes(value):
    if isinstance(value, list):
        return value
    if pd.isna(value):
        return []
    s = str(value).strip()
    if s.startswith("[") and s.endswith("]"):
        try:
            obj = ast.literal_eval(s)
            if isinstance(obj, list):
                return obj
        except Exception:
            pass
    if "->" in s:
        parts = s.split("->")
    elif "," in s:
        parts = s.split(",")
    else:
        parts = s.split()
    nodes = []
    for p in parts:
        p = str(p).strip().strip("'").strip('"')
        if p == "":
            continue
        nodes.append(0 if p in ["0", "0.0"] else p)
    return nodes


def get_customer_id(node):
    if node == 0 or str(node) == "0":
        return "0"
    s = str(node)
    if s.startswith("NEW_"):
        return s.replace("NEW_", "").split("_")[0]
    if s.startswith("ADDR_") and "_TO_" in s:
        return s.split("_TO_")[-1].split("_")[0]
    if "_" in s:
        return s.split("_")[0]
    return s


def route_to_string(nodes):
    return " -> ".join(str(x) for x in nodes)


def normalize_vehicle_type(v):
    name = str(v).strip()
    for key in VEHICLE_SPECS:
        if key.lower() in name.lower():
            return key
    if "3000" in name and ("ev" in name.lower() or "新能源" in name):
        return "ev_3000"
    if "1250" in name and ("ev" in name.lower() or "新能源" in name):
        return "ev_1250"
    if "3000" in name:
        return "fuel_3000"
    if "1500" in name:
        return "fuel_1500"
    if "1250" in name:
        return "fuel_1250"
    return "fuel_1500"


def normalize_routes_df(routes_df):
    node_col = find_col(routes_df, ["nodes", "节点", "路径", "route", "node_sequence", "节点序列"])
    vehicle_col = find_col(routes_df, ["vehicle_type", "车型", "车辆类型", "type"])
    route_id_col = find_col(routes_df, ["route_id", "车辆序号", "路径编号", "vehicle_id", "车辆编号"])

    if node_col is None:
        raise ValueError("problem2_routes.csv 中找不到路径节点列，请检查是否包含 nodes 或 路径 字段。")

    rows = []
    for idx, row in routes_df.iterrows():
        route_id = row[route_id_col] if route_id_col is not None else idx + 1
        vehicle_type = normalize_vehicle_type(row[vehicle_col]) if vehicle_col is not None else "fuel_1500"
        nodes = parse_nodes(row[node_col])
        if not nodes:
            continue
        if str(nodes[0]) != "0":
            nodes = [0] + nodes
        if str(nodes[-1]) != "0":
            nodes = nodes + [0]
        rows.append({"route_id": route_id, "vehicle_type": vehicle_type, "nodes": nodes})
    return pd.DataFrame(rows)


def get_non_depot_nodes(routes_df):
    items = []
    for idx, row in routes_df.iterrows():
        for pos, node in enumerate(row["nodes"]):
            if str(node) != "0":
                items.append((idx, pos, node))
    return items


# =========================================================
# 距离、速度、成本
# =========================================================
def lookup_distance(distance_df, a, b):
    if distance_df is None:
        return 0.0
    ca, cb = str(get_customer_id(a)), str(get_customer_id(b))
    if ca == cb:
        return 0.0
    keys_a, keys_b = [ca], [cb]
    try:
        keys_a.append(str(int(float(ca))))
    except Exception:
        pass
    try:
        keys_b.append(str(int(float(cb))))
    except Exception:
        pass

    for ka in keys_a:
        for kb in keys_b:
            try:
                return float(distance_df.loc[ka, kb])
            except Exception:
                pass
    try:
        ia, ib = int(float(ca)), int(float(cb))
        return float(distance_df.iloc[ia, ib])
    except Exception:
        return 0.0


def mean_speed(t):
    t = float(t)
    if 0 <= t < 60:
        return 9.8
    if 60 <= t < 120:
        return 55.3
    if 120 <= t < 210:
        return 35.4
    if 210 <= t < 300:
        return 9.8
    if 300 <= t < 420:
        return 55.3
    if 420 <= t < 540:
        return 35.4
    return 35.4


def speed_std(t):
    t = float(t)
    if 0 <= t < 60:
        return 4.7
    if 60 <= t < 120:
        return 0.1
    if 120 <= t < 210:
        return 5.2
    if 210 <= t < 300:
        return 4.7
    if 300 <= t < 420:
        return 0.1
    if 420 <= t < 540:
        return 5.2
    return 5.2


def period_end(t):
    for b in [60, 120, 210, 300, 420, 540]:
        if t < b:
            return b
    return float(t) + 10**6


def travel_time_by_distance(distance, start_time, stochastic=False, rng=None):
    if distance <= 1e-9:
        return 0.0, mean_speed(start_time)
    remain = float(distance)
    t = float(start_time)
    weighted_speed_sum = 0.0
    total_drive_time = 0.0

    while remain > 1e-9:
        v = mean_speed(t)
        if stochastic:
            if rng is None:
                rng = np.random.default_rng()
            v = float(rng.normal(v, speed_std(t)))
            v = max(v, 4.0)
        end_t = period_end(t)
        available_time = max(end_t - t, 1e-6)
        max_dist = v * available_time / 60.0
        if max_dist >= remain:
            dt = remain / v * 60.0
            weighted_speed_sum += v * dt
            total_drive_time += dt
            t += dt
            remain = 0.0
        else:
            dt = available_time
            weighted_speed_sum += v * dt
            total_drive_time += dt
            t = end_t
            remain -= max_dist
    avg_speed = weighted_speed_sum / max(total_drive_time, 1e-9)
    return total_drive_time, avg_speed


def fuel_fpk(v):
    return 0.0025 * v * v - 0.2554 * v + 31.75


def ev_epk(v):
    return 0.001 * v * v - 0.1 * v + 36.194


def node_demand(node, demand_map):
    cid = get_customer_id(node)
    if str(node).startswith("NEW_"):
        base_w, base_v = demand_map.get(cid, (240.0, 1.2))
        return max(base_w * 0.18, 80.0), max(base_v * 0.18, 0.35)
    if str(node).startswith("ADDR_"):
        base_w, base_v = demand_map.get(cid, (180.0, 0.8))
        return max(base_w * 0.20, 60.0), max(base_v * 0.20, 0.25)
    base_w, base_v = demand_map.get(cid, (0.0, 0.0))
    return max(base_w * 0.20, 0.0), max(base_v * 0.20, 0.0)


def route_schedule_and_cost(nodes, vehicle_type, distance_df, time_windows, demand_map,
                            stochastic=False, rng=None):
    spec = VEHICLE_SPECS.get(vehicle_type, VEHICLE_SPECS["fuel_1500"])
    total_weight = sum(node_demand(n, demand_map)[0] for n in nodes if str(n) != "0")
    total_volume = sum(node_demand(n, demand_map)[1] for n in nodes if str(n) != "0")

    capacity_penalty = 0.0
    if total_weight > spec["weight_cap"] + 1e-9:
        capacity_penalty += (total_weight - spec["weight_cap"]) / spec["weight_cap"] * LAMBDA_CAPACITY
    if total_volume > spec["volume_cap"] + 1e-9:
        capacity_penalty += (total_volume - spec["volume_cap"]) / spec["volume_cap"] * LAMBDA_CAPACITY

    current_time = 0.0
    current_weight = total_weight
    current_volume = total_volume

    total_dist = fixed_cost = energy_cost = carbon_cost = wait_cost = late_cost = 0.0
    arrival_records = []

    for i in range(len(nodes) - 1):
        a, b = nodes[i], nodes[i + 1]
        d = lookup_distance(distance_df, a, b)
        total_dist += d
        travel_time, avg_v = travel_time_by_distance(d, current_time, stochastic=stochastic, rng=rng)

        load_ratio = max(
            current_weight / max(spec["weight_cap"], 1e-9),
            current_volume / max(spec["volume_cap"], 1e-9),
            0.0,
        )
        load_ratio = min(load_ratio, 1.0)

        if spec["type"] == "fuel":
            factor = 1.0 + 0.4 * load_ratio
            fpk = max(fuel_fpk(avg_v), 0.0)
            energy_cost += d / 100.0 * fpk * factor * FUEL_PRICE
            carbon_cost += d / 100.0 * fpk * factor * FUEL_CARBON_FACTOR * CARBON_COST_PER_UNIT
        else:
            factor = 1.0 + 0.35 * load_ratio
            epk = max(ev_epk(avg_v), 0.0)
            energy_cost += d / 100.0 * epk * factor * ELECTRIC_PRICE
            carbon_cost += d / 100.0 * epk * factor * ELECTRIC_CARBON_FACTOR * CARBON_COST_PER_UNIT

        current_time += travel_time

        if str(b) != "0":
            cid = get_customer_id(b)
            tw_a, tw_b = time_windows.get(cid, (0.0, 540.0))
            start_service = max(current_time, tw_a)
            wait = max(0.0, tw_a - current_time)
            late = max(0.0, start_service - tw_b)
            wait_cost += wait * WAIT_COST_PER_MIN
            late_cost += late * LATE_COST_PER_MIN
            arrival_records.append({"node": b, "arrival": current_time, "start_service": start_service, "wait": wait, "late": late})
            dw, dv = node_demand(b, demand_map)
            current_weight = max(0.0, current_weight - dw)
            current_volume = max(0.0, current_volume - dv)
            current_time = start_service + SERVICE_TIME

    fixed_cost = spec["fixed"] if any(str(n) != "0" for n in nodes) else 0.0
    total_cost = fixed_cost + energy_cost + carbon_cost + wait_cost + late_cost + capacity_penalty
    return {
        "distance": total_dist,
        "fixed_cost": fixed_cost,
        "energy_cost": energy_cost,
        "carbon_cost": carbon_cost,
        "wait_cost": wait_cost,
        "late_cost": late_cost,
        "capacity_penalty": capacity_penalty,
        "return_time": current_time,
        "arrival_records": arrival_records,
        "total_cost": total_cost,
    }


# =========================================================
# 冻结与路径状态
# =========================================================
def build_full_nodes(route_state):
    nodes = list(route_state["prefix"])
    suffix = list(route_state["suffix"])
    if not nodes:
        nodes = [0]
    if str(nodes[0]) != "0":
        nodes = [0] + nodes
    for n in suffix:
        if str(n) != "0":
            nodes.append(n)
    if str(nodes[-1]) != "0":
        nodes.append(0)
    return nodes


def split_route_by_event(nodes, vehicle_type, distance_df, time_windows, demand_map):
    current_time = 0.0
    prefix = [0]
    remaining = []
    for idx in range(1, len(nodes) - 1):
        prev, node = nodes[idx - 1], nodes[idx]
        d = lookup_distance(distance_df, prev, node)
        travel_time, _ = travel_time_by_distance(d, current_time)
        current_time += travel_time
        cid = get_customer_id(node)
        tw_a, _ = time_windows.get(cid, (0.0, 540.0))
        start_service = max(current_time, tw_a)
        finish_service = start_service + SERVICE_TIME
        if finish_service <= EVENT_TIME_MINUTE:
            prefix.append(node)
            current_time = finish_service
        else:
            remaining = [n for n in nodes[idx:-1] if str(n) != "0"]
            break
    return prefix, remaining


def route_arcs(nodes):
    return set((str(nodes[i]), str(nodes[i + 1])) for i in range(len(nodes) - 1))


def original_assignment_map(routes_df):
    mp = {}
    for _, row in routes_df.iterrows():
        for node in row["nodes"]:
            if str(node) != "0":
                mp[str(node)] = row["route_id"]
    return mp


def evaluate_disturbance(base_routes_df, current_routes_df, original_assign):
    changed_routes = 0
    arc_change = 0
    assign_change = 0
    base_by_id = {str(row["route_id"]): row["nodes"] for _, row in base_routes_df.iterrows()}

    for _, row in current_routes_df.iterrows():
        rid = str(row["route_id"])
        nodes = row["nodes"]
        base_nodes = base_by_id.get(rid, [0, 0])
        if [str(x) for x in nodes] != [str(x) for x in base_nodes]:
            changed_routes += 1
        arc_change += len(route_arcs(nodes).symmetric_difference(route_arcs(base_nodes)))
        for node in nodes:
            if str(node) == "0":
                continue
            old_rid = original_assign.get(str(node))
            if old_rid is not None and str(old_rid) != rid:
                assign_change += 1
    return changed_routes, assign_change, arc_change


# =========================================================
# 子问题评价器
# =========================================================
class DynamicEvaluator:
    def __init__(self, base_routes_df, distance_df, time_windows, demand_map, original_assign):
        self.base_routes_df = base_routes_df
        self.distance_df = distance_df
        self.time_windows = time_windows
        self.demand_map = demand_map
        self.original_assign = original_assign

    def states_to_df(self, states):
        rows = []
        for st in states:
            rows.append({"route_id": st["route_id"], "vehicle_type": st["vehicle_type"], "nodes": build_full_nodes(st)})
        return pd.DataFrame(rows)

    def operational_eval(self, states):
        total_distance = fixed_cost = energy_cost = carbon_cost = wait_cost = late_cost = cap_penalty = 0.0
        for st in states:
            cost = route_schedule_and_cost(
                build_full_nodes(st), st["vehicle_type"], self.distance_df, self.time_windows, self.demand_map
            )
            total_distance += cost["distance"]
            fixed_cost += cost["fixed_cost"]
            energy_cost += cost["energy_cost"]
            carbon_cost += cost["carbon_cost"]
            wait_cost += cost["wait_cost"]
            late_cost += cost["late_cost"]
            cap_penalty += cost["capacity_penalty"]
        return {
            "总距离": total_distance,
            "固定成本": fixed_cost,
            "能耗成本": energy_cost,
            "碳排成本": carbon_cost,
            "等待成本": wait_cost,
            "迟到成本": late_cost,
            "容量惩罚": cap_penalty,
            "运营成本": fixed_cost + energy_cost + carbon_cost + wait_cost + late_cost + cap_penalty,
        }

    def objective(self, states):
        op = self.operational_eval(states)
        cur_df = self.states_to_df(states)
        changed_routes, assign_change, arc_change = evaluate_disturbance(
            self.base_routes_df, cur_df, self.original_assign
        )
        disturbance_cost = LAMBDA_ROUTE * changed_routes + LAMBDA_ASSIGN * assign_change + LAMBDA_ARC * arc_change
        return op["运营成本"] + disturbance_cost, {
            **op,
            "调整路径数": changed_routes,
            "改派客户数": assign_change,
            "弧段扰动数": arc_change,
            "扰动惩罚": disturbance_cost,
        }


# =========================================================
# ALNS-VNS 操作
# =========================================================
def all_suffix_tasks(states):
    tasks = []
    for r_idx, st in enumerate(states):
        for pos, node in enumerate(st["suffix"]):
            tasks.append((r_idx, pos, node))
    return tasks


def greedy_insert(states, task, evaluator):
    best = None
    for r_idx, st in enumerate(states):
        for pos in range(len(st["suffix"]) + 1):
            cand = deepcopy(states)
            cand[r_idx]["suffix"].insert(pos, task)
            obj, _ = evaluator.objective(cand)
            if best is None or obj < best["obj"]:
                best = {"obj": obj, "states": cand}
    return best["states"] if best is not None else states


def regret_insert(states, removed_tasks, evaluator, regret_k=2):
    cur = deepcopy(states)
    tasks = list(removed_tasks)
    while tasks:
        best_task, best_state, best_score = None, None, None
        for task in tasks:
            options = []
            for r_idx, st in enumerate(cur):
                for pos in range(len(st["suffix"]) + 1):
                    cand = deepcopy(cur)
                    cand[r_idx]["suffix"].insert(pos, task)
                    obj, _ = evaluator.objective(cand)
                    options.append((obj, cand))
            options.sort(key=lambda x: x[0])
            if len(options) == 1:
                score = options[0][0]
            else:
                k_idx = min(regret_k - 1, len(options) - 1)
                score = options[k_idx][0] - options[0][0]
            if best_score is None or score > best_score:
                best_score = score
                best_task = task
                best_state = options[0][1]
        cur = best_state
        tasks.remove(best_task)
    return cur


def low_disturbance_insert(states, removed_tasks, evaluator, original_assign):
    cur = deepcopy(states)
    route_id_to_idx = {str(st["route_id"]): idx for idx, st in enumerate(cur)}
    for task in removed_tasks:
        preferred = original_assign.get(str(task))
        inserted = False
        if preferred is not None and str(preferred) in route_id_to_idx:
            r_idx = route_id_to_idx[str(preferred)]
            best = None
            for pos in range(len(cur[r_idx]["suffix"]) + 1):
                cand = deepcopy(cur)
                cand[r_idx]["suffix"].insert(pos, task)
                obj, _ = evaluator.objective(cand)
                if best is None or obj < best["obj"]:
                    best = {"obj": obj, "states": cand}
            if best is not None:
                cur = best["states"]
                inserted = True
        if not inserted:
            cur = greedy_insert(cur, task, evaluator)
    return cur


def destroy_random(states, evaluator):
    tasks = all_suffix_tasks(states)
    if not tasks:
        return deepcopy(states), []
    q = max(1, int(len(tasks) * random.uniform(REMOVE_RATIO_MIN, REMOVE_RATIO_MAX)))
    selected = random.sample(tasks, min(q, len(tasks)))
    selected = sorted(selected, key=lambda x: (x[0], x[1]), reverse=True)
    new_states = deepcopy(states)
    removed = []
    for r_idx, pos, _ in selected:
        if pos < len(new_states[r_idx]["suffix"]):
            removed.append(new_states[r_idx]["suffix"].pop(pos))
    return new_states, removed


def destroy_high_cost(states, evaluator):
    base_obj, _ = evaluator.objective(states)
    scores = []
    for r_idx, st in enumerate(states):
        for pos, node in enumerate(st["suffix"]):
            cand = deepcopy(states)
            cand[r_idx]["suffix"].pop(pos)
            obj, _ = evaluator.objective(cand)
            scores.append((base_obj - obj, r_idx, pos, node))
    if not scores:
        return deepcopy(states), []
    scores.sort(reverse=True, key=lambda x: x[0])
    q = max(1, int(len(scores) * random.uniform(REMOVE_RATIO_MIN, REMOVE_RATIO_MAX)))
    selected = sorted(scores[:q], key=lambda x: (x[1], x[2]), reverse=True)
    new_states = deepcopy(states)
    removed = []
    for _, r_idx, pos, _ in selected:
        if pos < len(new_states[r_idx]["suffix"]):
            removed.append(new_states[r_idx]["suffix"].pop(pos))
    return new_states, removed


def destroy_related(states, evaluator):
    tasks = all_suffix_tasks(states)
    if not tasks:
        return deepcopy(states), []
    _, _, seed_node = random.choice(tasks)
    seed_cid = get_customer_id(seed_node)
    scored = []
    for r_idx, pos, node in tasks:
        d = lookup_distance(evaluator.distance_df, seed_cid, get_customer_id(node))
        scored.append((d, r_idx, pos, node))
    scored.sort(key=lambda x: x[0])
    q = max(1, int(len(scored) * random.uniform(REMOVE_RATIO_MIN, REMOVE_RATIO_MAX)))
    selected = sorted(scored[:q], key=lambda x: (x[1], x[2]), reverse=True)
    new_states = deepcopy(states)
    removed = []
    for _, r_idx, pos, _ in selected:
        if pos < len(new_states[r_idx]["suffix"]):
            removed.append(new_states[r_idx]["suffix"].pop(pos))
    return new_states, removed


def repair_greedy(states, removed, evaluator):
    cur = deepcopy(states)
    for task in removed:
        cur = greedy_insert(cur, task, evaluator)
    return cur


def repair_regret2(states, removed, evaluator):
    return regret_insert(states, removed, evaluator, regret_k=2)


def repair_regret3(states, removed, evaluator):
    return regret_insert(states, removed, evaluator, regret_k=3)


def repair_low_disturbance(states, removed, evaluator):
    return low_disturbance_insert(states, removed, evaluator, evaluator.original_assign)


def vns_relocate(states, evaluator):
    best = deepcopy(states)
    best_obj, _ = evaluator.objective(best)
    tasks = all_suffix_tasks(best)
    if len(tasks) <= 1:
        return best
    random.shuffle(tasks)
    for r_idx, pos, node in tasks[:24]:
        cur = deepcopy(best)
        if pos >= len(cur[r_idx]["suffix"]):
            continue
        task = cur[r_idx]["suffix"].pop(pos)
        for rr in range(len(cur)):
            for pp in range(len(cur[rr]["suffix"]) + 1):
                cand = deepcopy(cur)
                cand[rr]["suffix"].insert(pp, task)
                obj, _ = evaluator.objective(cand)
                if obj < best_obj:
                    return cand
    return best


def vns_swap(states, evaluator):
    best = deepcopy(states)
    best_obj, _ = evaluator.objective(best)
    tasks = all_suffix_tasks(best)
    if len(tasks) <= 1:
        return best
    for _ in range(30):
        a, b = random.sample(tasks, 2)
        r1, p1, _ = a
        r2, p2, _ = b
        if p1 >= len(best[r1]["suffix"]) or p2 >= len(best[r2]["suffix"]):
            continue
        cand = deepcopy(best)
        cand[r1]["suffix"][p1], cand[r2]["suffix"][p2] = cand[r2]["suffix"][p2], cand[r1]["suffix"][p1]
        obj, _ = evaluator.objective(cand)
        if obj < best_obj:
            return cand
    return best


def vns_2opt(states, evaluator):
    best = deepcopy(states)
    best_obj, _ = evaluator.objective(best)
    candidate_routes = list(range(len(best)))
    random.shuffle(candidate_routes)
    for r_idx in candidate_routes:
        suffix = best[r_idx]["suffix"]
        if len(suffix) < 4:
            continue
        for _ in range(16):
            i, j = sorted(random.sample(range(len(suffix)), 2))
            if j - i < 2:
                continue
            cand = deepcopy(best)
            cand[r_idx]["suffix"][i:j + 1] = reversed(cand[r_idx]["suffix"][i:j + 1])
            obj, _ = evaluator.objective(cand)
            if obj < best_obj:
                return cand
    return best


def apply_vns(states, evaluator):
    cur = vns_relocate(states, evaluator)
    cur = vns_swap(cur, evaluator)
    cur = vns_2opt(cur, evaluator)
    return cur


def run_alns_vns(initial_states, evaluator):
    destroy_ops = [destroy_random, destroy_high_cost, destroy_related]
    repair_ops = [repair_greedy, repair_regret2, repair_regret3, repair_low_disturbance]

    cur = deepcopy(initial_states)
    cur_obj, _ = evaluator.objective(cur)
    best = deepcopy(cur)
    best_obj = cur_obj

    temperature = START_TEMPERATURE
    start_time = time.time()
    history = []

    for _ in range(1, ALNS_ITER + 1):
        if time.time() - start_time > ALNS_TIME_LIMIT:
            break
        destroy = random.choice(destroy_ops)
        repair = random.choice(repair_ops)
        partial, removed = destroy(cur, evaluator)
        cand = repair(partial, removed, evaluator) if removed else partial
        cand = apply_vns(cand, evaluator)
        cand_obj, _ = evaluator.objective(cand)
        delta = cand_obj - cur_obj
        if delta <= 0 or random.random() < math.exp(-delta / max(temperature, 1e-9)):
            cur = cand
            cur_obj = cand_obj
        if cand_obj < best_obj:
            best = deepcopy(cand)
            best_obj = cand_obj
        history.append(best_obj)
        temperature *= COOLING_RATE

    return best, best_obj, history, time.time() - start_time


def run_alns_vns_multiseed(initial_states, evaluator, seeds=P3_SEEDS):
    best_pack = None
    for seed in seeds:
        random.seed(seed)
        np.random.seed(seed)
        states, obj, history, runtime = run_alns_vns(initial_states, evaluator)
        if best_pack is None or obj < best_pack["best_obj"]:
            best_pack = {
                "seed": seed,
                "states": deepcopy(states),
                "best_obj": obj,
                "history": history,
                "runtime": runtime,
            }
        print(f"    seed={seed} 完成：best_obj={obj:.2f}，runtime={runtime:.2f}s")
    return (
        best_pack["states"],
        best_pack["best_obj"],
        best_pack["history"],
        best_pack["runtime"],
        best_pack["seed"],
    )


# =========================================================
# 动态事件构造
# =========================================================
def route_center_distance(route_nodes, target_node, distance_df):
    non_depot = [n for n in route_nodes if str(n) != "0"]
    if not non_depot:
        return 1e18
    return min(lookup_distance(distance_df, n, target_node) for n in non_depot)


def pick_affected_routes(routes_df, target_nodes, distance_df, k=NEIGHBOR_ROUTE_COUNT):
    scored = []
    for idx, row in routes_df.iterrows():
        dist = min(route_center_distance(row["nodes"], t, distance_df) for t in target_nodes)
        scored.append((dist, idx))
    scored.sort(key=lambda x: x[0])
    return [idx for _, idx in scored[:min(k, len(scored))]]


def build_subproblem_states(routes_df, affected_idx, distance_df, time_windows, demand_map):
    states = []
    for idx in affected_idx:
        row = routes_df.loc[idx]
        prefix, suffix = split_route_by_event(row["nodes"], row["vehicle_type"], distance_df, time_windows, demand_map)
        states.append({"route_id": row["route_id"], "vehicle_type": row["vehicle_type"], "prefix": prefix, "suffix": suffix})
    return states


def merge_states_to_routes(base_routes_df, optimized_states):
    result = base_routes_df.copy(deep=True)
    for st in optimized_states:
        rid = str(st["route_id"])
        matched_indices = result.index[result["route_id"].astype(str) == rid].tolist()
        if not matched_indices:
            continue
        result.at[matched_indices[0], "nodes"] = build_full_nodes(st)
    return result


def available_unfrozen_tasks(routes_df, distance_df, time_windows, demand_map):
    items = []
    for idx, row in routes_df.iterrows():
        _, suffix = split_route_by_event(row["nodes"], row["vehicle_type"], distance_df, time_windows, demand_map)
        for node in suffix:
            items.append((idx, node))
    return items


def prepare_event_scenario(event_id, routes_df, distance_df, time_windows, demand_map):
    unfrozen = available_unfrozen_tasks(routes_df, distance_df, time_windows, demand_map)
    if not unfrozen:
        unfrozen = [(idx, node) for idx, _, node in get_non_depot_nodes(routes_df)]

    if event_id == "E1":
        _, target = unfrozen[len(unfrozen) // 3]
        affected = pick_affected_routes(routes_df, [target], distance_df)
        states = build_subproblem_states(routes_df, affected, distance_df, time_windows, demand_map)
        for st in states:
            st["suffix"] = [n for n in st["suffix"] if str(n) != str(target)]
        return {
            "事件编号": "E1",
            "事件类型": "订单取消",
            "事件描述": f"事件时刻后，任务 {target} 被取消，冻结已完成部分后对受影响路径进行重优化。",
            "affected": affected,
            "states": states,
            "time_windows": deepcopy(time_windows),
        }

    if event_id == "E2":
        _, ref = unfrozen[len(unfrozen) // 2]
        cid = get_customer_id(ref)
        new_node = f"NEW_{cid}"
        affected = pick_affected_routes(routes_df, [ref], distance_df)
        states = build_subproblem_states(routes_df, affected, distance_df, time_windows, demand_map)
        if states:
            states[0]["suffix"].append(new_node)
        return {
            "事件编号": "E2",
            "事件类型": "新增订单",
            "事件描述": f"事件时刻后，客户 {cid} 产生新增任务 {new_node}，采用低扰动滚动重优化插入。",
            "affected": affected,
            "states": states,
            "time_windows": deepcopy(time_windows),
        }

    if event_id == "E3":
        _, old_node = unfrozen[len(unfrozen) // 4]
        _, ref_node = unfrozen[len(unfrozen) * 3 // 4]
        old_cid = get_customer_id(old_node)
        new_cid = get_customer_id(ref_node)
        changed_node = f"ADDR_{old_cid}_TO_{new_cid}"
        affected = pick_affected_routes(routes_df, [old_node, ref_node], distance_df)
        states = build_subproblem_states(routes_df, affected, distance_df, time_windows, demand_map)
        for st in states:
            st["suffix"] = [changed_node if str(n) == str(old_node) else n for n in st["suffix"]]
        return {
            "事件编号": "E3",
            "事件类型": "配送地址变更",
            "事件描述": f"任务 {old_node} 的地址由客户 {old_cid} 变更为客户 {new_cid}，转换为新任务 {changed_node}。",
            "affected": affected,
            "states": states,
            "time_windows": deepcopy(time_windows),
        }

    if event_id == "E4":
        t1 = unfrozen[len(unfrozen) // 5][1]
        t2 = unfrozen[len(unfrozen) * 2 // 5][1]
        targets = [t1, t2]
        new_tw = deepcopy(time_windows)
        for node in targets:
            cid = get_customer_id(node)
            a, b = new_tw.get(cid, (0.0, 540.0))
            new_tw[cid] = (a, max(a + 20.0, b - 70.0))
        affected = pick_affected_routes(routes_df, targets, distance_df)
        states = build_subproblem_states(routes_df, affected, distance_df, new_tw, demand_map)
        return {
            "事件编号": "E4",
            "事件类型": "时间窗收紧",
            "事件描述": f"任务 {t1} 与 {t2} 的服务时间窗临时收紧，触发滚动重优化。",
            "affected": affected,
            "states": states,
            "time_windows": new_tw,
        }

    raise ValueError(f"未知事件编号：{event_id}")


# =========================================================
# 全局方案评价
# =========================================================
def evaluate_full_routes(routes_df, distance_df, time_windows, demand_map):
    total_distance = fixed_cost = energy_cost = carbon_cost = wait_cost = late_cost = cap_penalty = 0.0
    for _, row in routes_df.iterrows():
        cost = route_schedule_and_cost(row["nodes"], row["vehicle_type"], distance_df, time_windows, demand_map)
        total_distance += cost["distance"]
        fixed_cost += cost["fixed_cost"]
        energy_cost += cost["energy_cost"]
        carbon_cost += cost["carbon_cost"]
        wait_cost += cost["wait_cost"]
        late_cost += cost["late_cost"]
        cap_penalty += cost["capacity_penalty"]
    return {
        "车辆数": len(routes_df),
        "总距离": total_distance,
        "固定成本": fixed_cost,
        "能耗成本": energy_cost,
        "碳排成本": carbon_cost,
        "等待成本": wait_cost,
        "迟到成本": late_cost,
        "容量惩罚": cap_penalty,
        "总成本": fixed_cost + energy_cost + carbon_cost + wait_cost + late_cost + cap_penalty,
    }


def safe_improve_rate(before, after):
    if abs(before) < 1e-9:
        return 0.0
    return (before - after) / abs(before) * 100.0


def monte_carlo_risk(routes_df, distance_df, time_windows, demand_map, samples=MONTE_CARLO_SAMPLES):
    rng = np.random.default_rng(RANDOM_SEED + 100)
    total_costs = []
    for _ in range(samples):
        fixed_cost = energy_cost = carbon_cost = wait_cost = late_cost = cap_penalty = 0.0
        for _, row in routes_df.iterrows():
            cost = route_schedule_and_cost(
                row["nodes"], row["vehicle_type"], distance_df, time_windows, demand_map,
                stochastic=True, rng=rng
            )
            fixed_cost += cost["fixed_cost"]
            energy_cost += cost["energy_cost"]
            carbon_cost += cost["carbon_cost"]
            wait_cost += cost["wait_cost"]
            late_cost += cost["late_cost"]
            cap_penalty += cost["capacity_penalty"]
        total_costs.append(fixed_cost + energy_cost + carbon_cost + wait_cost + late_cost + cap_penalty)
    arr = np.array(total_costs, dtype=float)
    return {
        "鲁棒均值成本": float(np.mean(arr)),
        "鲁棒成本标准差": float(np.std(arr)),
        "鲁棒95分位成本": float(np.percentile(arr, 95)),
        "风险成本": float(np.percentile(arr, 95) - np.mean(arr)),
    }


# =========================================================
# 导出与绘图
# =========================================================
def export_event_routes(event_route_map):
    rows = []
    for event_id, routes_df in event_route_map.items():
        for _, row in routes_df.iterrows():
            rows.append({"事件编号": event_id, "路径编号": row["route_id"], "车型": row["vehicle_type"], "路径": route_to_string(row["nodes"])})
    pd.DataFrame(rows).to_csv(OUTPUT_ROUTES_PATH, index=False, encoding="utf-8-sig")
    print(f"动态事件路径结果已导出：{OUTPUT_ROUTES_PATH}")


def export_text_analysis(base_eval, results_df):
    lines = []
    lines.append("问题三高级动态调度结果分析\n")
    lines.append("1. 方法说明\n")
    lines.append(
        "本文采用事件驱动的滚动时域动态调度策略。在动态事件发生时，先冻结事件时刻之前已经完成的服务路径，"
        "再选取受影响车辆及其邻近车辆构造动态子问题，最后采用多随机种子混合 ALNS-VNS 算法进行低扰动重优化。"
    )
    lines.append("\n2. 基准方案\n")
    lines.append(
        f"问题三以问题二最终方案为基准，基准总成本为 {base_eval['总成本']:.2f} 元，"
        f"总距离为 {base_eval['总距离']:.2f} km。"
    )
    lines.append("\n3. 动态事件结果\n")
    for _, row in results_df.iterrows():
        lines.append(
            f"{row['事件编号']}（{row['事件类型']}）：{row['事件描述']}\n"
            f"事件初始方案成本为 {row['事件初始方案总成本']:.2f} 元，重优化后总成本为 {row['总成本']:.2f} 元，"
            f"相对事件初始方案节约 {row['重优化节约成本']:.2f} 元；相对基准变化 {row['总成本变化']:.2f} 元。"
            f"最佳 seed 为 {row['最佳seed']}，子问题目标改善率为 {row['子问题目标改善率/%']:.2f}%。"
            f"调整路径数 {row['调整路径数']}，改派客户数 {row['改派客户数']}，弧段扰动数 {row['弧段扰动数']}，"
            f"鲁棒95分位成本为 {row['鲁棒95分位成本']:.2f} 元。"
        )
    lines.append("\n4. 结论\n")
    lines.append(
        "多随机种子滚动 ALNS-VNS 方法能够在订单取消、新增订单、地址变更和时间窗收紧等事件下，"
        "在不完全推翻原有调度方案的前提下重构受影响路径。通过对比事件初始方案与重优化方案，"
        "可以看出该算法具有二次优化能力，同时兼顾运营成本、路径扰动和随机交通风险。"
    )
    with open(OUTPUT_ANALYSIS_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"动态调度文字分析已导出：{OUTPUT_ANALYSIS_PATH}")


def plot_results(base_eval, results_df):
    """
    问题三最终视觉增强版绘图函数。

    图形组合：
    1. 浮动横向条形图：事件初始方案 vs ALNS-VNS 重优化方案；
    2. 四宫格节约效果卡片：展示节约额、改善率、最佳 seed；
    3. 3D 柱状图：展示路径扰动相对强度；
    4. 鲁棒性指标矩阵：展示均值成本、95分位成本、风险成本与标准差。
    """
    from matplotlib.colors import LinearSegmentedColormap
    from matplotlib.ticker import FuncFormatter
    from matplotlib.patches import FancyBboxPatch, Patch

    os.makedirs(OUTPUT_FIG_DIR, exist_ok=True)

    df = results_df.copy()
    event_order = ["E1", "E2", "E3", "E4"]
    df["事件编号"] = df["事件编号"].astype(str)
    df["_order"] = df["事件编号"].apply(lambda x: event_order.index(x) if x in event_order else 99)
    df = df.sort_values("_order").reset_index(drop=True)

    event_labels = [f"{r['事件编号']}  {r['事件类型']}" for _, r in df.iterrows()]
    events = df["事件编号"].tolist()

    PALETTE = {
        "base": "#355C7D",
        "init": "#A7AFBA",
        "opt": "#E68632",
        "save": "#4F9D69",
        "risk": "#C44E52",
        "purple": "#8E6BBE",
        "teal": "#5DA5A4",
        "card": "#F5F7FA",
        "line": "#CED6E0",
        "grid": "#E7ECF2",
        "text": "#222222",
        "subtext": "#666666",
        "heat_low": "#F7FAFC",
        "heat_mid": "#9BC2DC",
        "heat_high": "#315D92",
        "risk_low": "#FFF7F2",
        "risk_mid": "#F2B6A6",
        "risk_high": "#B94D4D",
    }

    def fmt_money(x, pos=None):
        return f"{x:,.0f}"

    def save_current_fig(fig, filename):
        path = os.path.join(OUTPUT_FIG_DIR, filename)
        fig.savefig(path, dpi=300, bbox_inches="tight", pad_inches=0.18, facecolor="white")
        plt.close(fig)
        print(f"图已生成：{path}")

    def add_header(fig, title, subtitle=None):
        fig.text(0.5, 0.965, title, ha="center", va="top", fontsize=18, fontweight="bold", color=PALETTE["text"])
        if subtitle:
            fig.text(0.5, 0.915, subtitle, ha="center", va="top", fontsize=10.5, color=PALETTE["subtext"])

    def clean_axis(ax, grid_axis="x", money_axis=True):
        ax.set_facecolor("white")
        ax.grid(axis=grid_axis, linestyle="--", linewidth=0.8, alpha=0.45, color=PALETTE["grid"], zorder=0)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_alpha(0.35)
        ax.spines["bottom"].set_alpha(0.35)
        ax.tick_params(labelsize=10.5, colors=PALETTE["text"])
        if money_axis:
            ax.xaxis.set_major_formatter(FuncFormatter(fmt_money))

    def row_normalize(mat):
        mat = np.asarray(mat, dtype=float)
        out = np.zeros_like(mat, dtype=float)
        for i in range(mat.shape[0]):
            row = mat[i]
            if row.max() - row.min() < 1e-9:
                out[i, :] = 0.50
            else:
                out[i, :] = (row - row.min()) / (row.max() - row.min())
        return out

    plt.rcParams["axes.unicode_minus"] = False

    init_cost = df["事件初始方案总成本"].to_numpy(dtype=float)
    opt_cost = df["总成本"].to_numpy(dtype=float)
    saving = df["重优化节约成本"].to_numpy(dtype=float)
    base_cost = float(base_eval["总成本"])

    # =====================================================
    # 图1：浮动横向条形图
    # =====================================================
    y = np.arange(len(df))
    h = 0.32
    x_floor = min(init_cost.min(), opt_cost.min(), base_cost) - 450
    x_ceil = max(init_cost.max(), opt_cost.max(), base_cost) + 650

    fig, ax = plt.subplots(figsize=(11.8, 6.4))
    fig.patch.set_facecolor("white")

    ax.barh(y - h / 2, init_cost - x_floor, left=x_floor, height=h,
            color=PALETTE["init"], edgecolor="white", linewidth=1.0,
            label="事件初始方案", zorder=3)
    ax.barh(y + h / 2, opt_cost - x_floor, left=x_floor, height=h,
            color=PALETTE["opt"], edgecolor="white", linewidth=1.0,
            label="ALNS-VNS 重优化", zorder=3)

    ax.axvline(base_cost, color=PALETTE["base"], linewidth=1.0, linestyle="--", alpha=0.35, zorder=1)
    ax.text(base_cost, -0.62, f"基准 {base_cost:,.0f}", ha="center", va="bottom", fontsize=9.5, color=PALETTE["base"])

    for i in range(len(df)):
        ax.text(init_cost[i] + 35, y[i] - h / 2, f"{init_cost[i]:,.0f}",
                va="center", ha="left", fontsize=9.6, color=PALETTE["text"])
        ax.text(opt_cost[i] + 35, y[i] + h / 2, f"{opt_cost[i]:,.0f}",
                va="center", ha="left", fontsize=9.6, color=PALETTE["text"])
        ax.text(x_floor + (x_ceil - x_floor) * 0.015, y[i] + h / 2,
                f"↓ 节约 {saving[i]:,.0f}", va="center", ha="left",
                fontsize=10.0, color=PALETTE["save"], fontweight="bold")

    ax.set_yticks(y)
    ax.set_yticklabels(event_labels, fontsize=11)
    ax.invert_yaxis()
    ax.set_xlabel("总成本 / 元", fontsize=12)
    ax.set_xlim(x_floor, x_ceil)
    ax.set_ylim(len(df) - 0.55, -0.75)
    ax.legend(frameon=False, loc="lower right", fontsize=10.2)
    clean_axis(ax, grid_axis="x")
    add_header(fig, "动态事件下的成本对比", "浮动条形图展示事件初始方案与滚动重优化方案的成本差异")
    fig.subplots_adjust(top=0.82, bottom=0.14, left=0.15, right=0.97)
    save_current_fig(fig, "p3_advanced_total_cost_compare.png")

    # =====================================================
    # 图2：四宫格节约效果卡片
    # =====================================================
    df_save = df.sort_values("重优化节约成本", ascending=False).reset_index(drop=True)
    max_save = max(df_save["重优化节约成本"].max(), 1.0)

    fig, axes = plt.subplots(2, 2, figsize=(11.4, 6.8))
    fig.patch.set_facecolor("white")
    axes = axes.ravel()

    for ax, (_, row) in zip(axes, df_save.iterrows()):
        val = float(row["重优化节约成本"])
        init_val = float(row["事件初始方案总成本"])
        rate = val / init_val * 100 if init_val > 0 else 0.0
        seed = row["最佳seed"] if "最佳seed" in row.index else "-"
        runtime = row["ALNS运行时间/s"] if "ALNS运行时间/s" in row.index else np.nan

        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)

        card = FancyBboxPatch((0.03, 0.08), 0.94, 0.82,
                              boxstyle="round,pad=0.018,rounding_size=0.04",
                              facecolor=PALETTE["card"], edgecolor="#E0E5EC",
                              linewidth=1.0, transform=ax.transAxes)
        ax.add_patch(card)

        ax.text(0.10, 0.78, f"{row['事件编号']}  {row['事件类型']}",
                fontsize=12.5, fontweight="bold", color=PALETTE["text"], transform=ax.transAxes)
        ax.text(0.10, 0.55, f"{val:,.0f}", fontsize=25,
                fontweight="bold", color=PALETTE["save"], transform=ax.transAxes)
        ax.text(0.10, 0.42, "元节约成本", fontsize=10.5,
                color=PALETTE["subtext"], transform=ax.transAxes)

        bar_x, bar_y, bar_w, bar_h = 0.10, 0.28, 0.78, 0.075
        ax.add_patch(FancyBboxPatch((bar_x, bar_y), bar_w, bar_h,
                                    boxstyle="round,pad=0.004,rounding_size=0.025",
                                    facecolor="#DCE3EA", edgecolor="none", transform=ax.transAxes))
        ax.add_patch(FancyBboxPatch((bar_x, bar_y), bar_w * val / max_save, bar_h,
                                    boxstyle="round,pad=0.004,rounding_size=0.025",
                                    facecolor=PALETTE["save"], edgecolor="none", transform=ax.transAxes))

        rt_text = f"{runtime:.1f}s" if not pd.isna(runtime) else "-"
        ax.text(0.10, 0.16, f"改善率 {rate:.2f}%   最佳 seed {seed}   用时 {rt_text}",
                fontsize=9.8, color=PALETTE["subtext"], transform=ax.transAxes)

    add_header(fig, "重优化节约效果", "四宫格卡片展示不同动态事件下 ALNS-VNS 的直接改进幅度")
    fig.subplots_adjust(top=0.82, bottom=0.08, left=0.05, right=0.98, hspace=0.22, wspace=0.14)
    save_current_fig(fig, "p3_advanced_optimization_saving.png")

    # =====================================================
    # 图3：3D柱状图，展示路径扰动相对强度
    # =====================================================
    metrics = ["调整路径数", "改派客户数", "弧段扰动数"]
    values = df[metrics].to_numpy(dtype=float).T
    n_metrics, n_events = values.shape

    x_grid, y_grid = np.meshgrid(np.arange(n_events), np.arange(n_metrics), indexing="xy")
    xpos = x_grid.ravel().astype(float)
    ypos = y_grid.ravel().astype(float)
    zpos = np.zeros_like(xpos, dtype=float)
    dx = np.full_like(xpos, 0.55, dtype=float)
    dy = np.full_like(ypos, 0.50, dtype=float)
    dz = values.ravel()

    metric_colors = ["#4E79A7", "#F28E2B", "#59A14F"]
    bar_colors = [metric_colors[int(y)] for y in ypos]

    fig = plt.figure(figsize=(12.8, 7.5))
    fig.patch.set_facecolor("white")
    ax = fig.add_subplot(111, projection="3d")

    ax.bar3d(
        xpos, ypos, zpos,
        dx, dy, dz,
        color=bar_colors,
        alpha=0.94,
        shade=True,
        edgecolor="white",
        linewidth=0.65,
        zsort="average",
    )

    for x, y0, z in zip(xpos, ypos, dz):
        ax.text(
            x + 0.275, y0 + 0.25, z + max(dz.max(), 1.0) * 0.025,
            f"{int(round(z))}",
            ha="center", va="bottom",
            fontsize=10.0, fontweight="bold", color=PALETTE["text"],
        )

    ax.set_xticks(np.arange(n_events) + 0.275)
    ax.set_xticklabels(events, fontsize=10.5)
    ax.set_yticks(np.arange(n_metrics) + 0.25)
    ax.set_yticklabels(metrics, fontsize=10.5)
    ax.set_zlabel("相对强度值", fontsize=11.5, labelpad=13)
    ax.set_ylabel("扰动指标", fontsize=11.5, labelpad=25)
    ax.tick_params(axis="x", pad=3)
    ax.tick_params(axis="y", pad=8)
    ax.tick_params(axis="z", pad=4)
    ax.set_zlim(0, max(dz.max(), 1.0) * 1.25)

    ax.view_init(elev=25, azim=-56)
    try:
        ax.set_box_aspect((1.65, 0.85, 0.72))
        ax.xaxis.pane.set_facecolor((0.97, 0.98, 1.00, 0.75))
        ax.yaxis.pane.set_facecolor((0.98, 0.99, 0.97, 0.75))
        ax.zaxis.pane.set_facecolor((1.00, 1.00, 1.00, 0.75))
        ax.xaxis.pane.set_edgecolor((0.86, 0.88, 0.91, 0.45))
        ax.yaxis.pane.set_edgecolor((0.86, 0.88, 0.91, 0.45))
        ax.zaxis.pane.set_edgecolor((0.86, 0.88, 0.91, 0.45))
    except Exception:
        pass

    ax.grid(True)
    handles = [Patch(facecolor=metric_colors[i], label=metrics[i]) for i in range(n_metrics)]
    ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.02, 0.90), frameon=False, fontsize=10.0)

    fig.text(0.5, 0.965, "路径扰动强度对比", ha="center", va="top", fontsize=18, fontweight="bold", color=PALETTE["text"])
    fig.text(0.5, 0.915, "柱高表示各扰动指标在不同事件间的相对强度，柱顶数字为实际统计值", ha="center", va="top", fontsize=10.5, color=PALETTE["subtext"])
    fig.subplots_adjust(left=0.04, right=0.98, bottom=0.08, top=0.84)
    save_current_fig(fig, "p3_advanced_disturbance_compare.png")

    # =====================================================
    # 图4：鲁棒性指标矩阵
    # =====================================================
    robust_metrics = ["鲁棒均值成本", "鲁棒95分位成本", "风险成本", "鲁棒成本标准差"]
    display_names = ["均值成本", "95分位成本", "风险成本", "成本标准差"]
    risk_raw = df[robust_metrics].to_numpy(dtype=float).T
    risk_norm = row_normalize(risk_raw)

    risk_cmap = LinearSegmentedColormap.from_list(
        "paper_risk_heat",
        [PALETTE["risk_low"], PALETTE["risk_mid"], PALETTE["risk_high"]]
    )

    fig, ax = plt.subplots(figsize=(10.2, 6.0))
    fig.patch.set_facecolor("white")
    ax.imshow(risk_norm, cmap=risk_cmap, aspect="auto", vmin=0, vmax=1, zorder=2)

    ax.set_xticks(np.arange(len(events)))
    ax.set_xticklabels(events, fontsize=11)
    ax.set_yticks(np.arange(len(display_names)))
    ax.set_yticklabels(display_names, fontsize=11)

    for i in range(len(display_names)):
        for j in range(len(events)):
            val = risk_raw[i, j]
            norm_val = risk_norm[i, j]
            txt = f"{val:,.0f}" if i in [0, 1] else f"{val:.1f}"
            ax.text(j, i, txt, ha="center", va="center", fontsize=10.8,
                    color="white" if norm_val > 0.62 else PALETTE["text"],
                    fontweight="bold" if i in [2, 3] else "normal")

    ax.set_xticks(np.arange(-0.5, len(events), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(display_names), 1), minor=True)
    ax.grid(which="minor", color="white", linestyle="-", linewidth=2.0)
    ax.tick_params(which="minor", bottom=False, left=False)
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)

    add_header(fig, "动态方案鲁棒性评估", "矩阵展示 Monte Carlo 仿真下的均值、95分位、风险成本和波动程度")
    fig.subplots_adjust(top=0.80, bottom=0.13, left=0.14, right=0.96)
    save_current_fig(fig, "p3_advanced_risk_cost_compare.png")

def main():
    print("========== main_p3.py 问题三高级动态调度已启动 ==========")
    print("方法：事件驱动滚动时域优化 + 冻结机制 + 多随机种子混合 ALNS-VNS + Monte Carlo 鲁棒评价")

    random.seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)
    setup_chinese_font()

    _ = read_summary()  # 保留读取，确保问题二结果文件存在
    raw_routes = read_routes()
    routes_df = normalize_routes_df(raw_routes)

    distance_df = read_distance_matrix()
    time_windows = read_time_windows()
    demand_map = read_customer_demands()

    original_assign = original_assignment_map(routes_df)

    print("问题二基准路径数：", len(routes_df))
    print("动态事件发生时刻：11:00")
    print("多随机种子：", P3_SEEDS)
    print("单个 seed 时间上限：", ALNS_TIME_LIMIT, "秒")

    base_eval = evaluate_full_routes(routes_df, distance_df, time_windows, demand_map)
    base_eval.update(monte_carlo_risk(routes_df, distance_df, time_windows, demand_map))

    print("基准总成本：", round(base_eval["总成本"], 2))
    print("基准总距离：", round(base_eval["总距离"], 2))

    if distance_df is None:
        print("警告：距离矩阵未读取，当前结果仅能用于流程测试，不能作为论文结果。")

    event_results = []
    event_route_map = {}

    for eid in ["E1", "E2", "E3", "E4"]:
        print(f"\n========== 开始处理 {eid} ==========")
        scenario = prepare_event_scenario(eid, routes_df, distance_df, time_windows, demand_map)
        affected_idx = scenario["affected"]
        init_states = scenario["states"]
        event_tw = scenario["time_windows"]

        sub_base_df = routes_df.loc[affected_idx].copy(deep=True)
        evaluator = DynamicEvaluator(
            base_routes_df=sub_base_df,
            distance_df=distance_df,
            time_windows=event_tw,
            demand_map=demand_map,
            original_assign=original_assign,
        )

        init_obj, _ = evaluator.objective(init_states)

        initial_event_routes = merge_states_to_routes(routes_df, init_states)
        initial_event_eval = evaluate_full_routes(initial_event_routes, distance_df, event_tw, demand_map)

        print(
            f"{eid} 事件初始方案：总成本={initial_event_eval['总成本']:.2f}，"
            f"总距离={initial_event_eval['总距离']:.2f}"
        )

        best_states, best_obj, history, runtime, best_seed = run_alns_vns_multiseed(
            init_states,
            evaluator,
            seeds=P3_SEEDS,
        )

        repaired_routes = merge_states_to_routes(routes_df, best_states)
        full_eval = evaluate_full_routes(repaired_routes, distance_df, event_tw, demand_map)
        full_eval.update(monte_carlo_risk(repaired_routes, distance_df, event_tw, demand_map))

        changed_routes, assign_change, arc_change = evaluate_disturbance(routes_df, repaired_routes, original_assign)

        result = {
            "事件编号": scenario["事件编号"],
            "事件类型": scenario["事件类型"],
            "事件描述": scenario["事件描述"],
            "受影响路径数": len(affected_idx),
            "最佳seed": best_seed,
            "ALNS运行时间/s": runtime,
            "初始子问题目标": init_obj,
            "最优子问题目标": best_obj,
            "子问题目标改善率/%": safe_improve_rate(init_obj, best_obj),
            "事件初始方案总成本": initial_event_eval["总成本"],
            "事件初始方案总距离": initial_event_eval["总距离"],
            "重优化节约成本": initial_event_eval["总成本"] - full_eval["总成本"],
            "重优化距离变化": full_eval["总距离"] - initial_event_eval["总距离"],
            "车辆数": full_eval["车辆数"],
            "总距离": full_eval["总距离"],
            "基准总距离": base_eval["总距离"],
            "总距离变化": full_eval["总距离"] - base_eval["总距离"],
            "固定成本": full_eval["固定成本"],
            "能耗成本": full_eval["能耗成本"],
            "碳排成本": full_eval["碳排成本"],
            "等待成本": full_eval["等待成本"],
            "迟到成本": full_eval["迟到成本"],
            "容量惩罚": full_eval["容量惩罚"],
            "总成本": full_eval["总成本"],
            "基准总成本": base_eval["总成本"],
            "总成本变化": full_eval["总成本"] - base_eval["总成本"],
            "调整路径数": changed_routes,
            "改派客户数": assign_change,
            "弧段扰动数": arc_change,
            "鲁棒均值成本": full_eval["鲁棒均值成本"],
            "鲁棒成本标准差": full_eval["鲁棒成本标准差"],
            "鲁棒95分位成本": full_eval["鲁棒95分位成本"],
            "风险成本": full_eval["风险成本"],
        }

        event_results.append(result)
        event_route_map[eid] = repaired_routes

        print(
            f"{eid} 完成：best_seed={best_seed}，总成本={result['总成本']:.2f}，"
            f"相对初始节约={result['重优化节约成本']:.2f}，"
            f"相对基准变化={result['总成本变化']:.2f}，"
            f"调整路径数={changed_routes}，最佳seed运行时间={runtime:.2f}s"
        )

    results_df = pd.DataFrame(event_results)
    results_df.to_csv(OUTPUT_RESULT_PATH, index=False, encoding="utf-8-sig")
    print(f"\n高级动态事件结果已导出：{OUTPUT_RESULT_PATH}")

    export_event_routes(event_route_map)
    export_text_analysis(base_eval, results_df)
    plot_results(base_eval, results_df)

    print("\n========== main_p3.py 运行结束 ==========")
    print("结果文件：", OUTPUT_RESULT_PATH)
    print("路径文件：", OUTPUT_ROUTES_PATH)
    print("分析文件：", OUTPUT_ANALYSIS_PATH)
    print("图像文件夹：", OUTPUT_FIG_DIR)


if __name__ == "__main__":
    main()
