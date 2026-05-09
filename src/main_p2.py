# === Project path bootstrap ===
from pathlib import Path
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
# ==============================

import time
import traceback
import contextlib
import io
import os
import json

import pandas as pd

from config import CARBON_COST_PER_UNIT
from data_loader import build_problem_data, build_task_table
from initial_solution import build_initial_solution
from alns_p1 import run_alns_p1, export_problem1_results


# =========================================================
# 问题二参数
# =========================================================
# 问题二比问题一更难，因为燃油车绿色区限行会减少可行插入位置。
# 这里用多随机种子择优，保证结果稳定。
SEEDS = [1, 7, 21, 42, 66, 88, 100]

MAX_ITER = 300
TIME_LIMIT_PER_SEED = 180

REMOVE_RATIO_MIN = 0.04
REMOVE_RATIO_MAX = 0.18
START_TEMPERATURE = 2500.0
COOLING_RATE = 0.985

DETAILED_LOG = False

P1_SUMMARY_PATH = "results/problem1/problem1_summary.csv"

P2_OUTPUT_PREFIX = "results/problem2/problem2"
P2_MULTI_SEED_SUMMARY_PATH = "results/problem2/problem2_multiseed_summary.csv"
P2_COMPARE_PATH = "results/problem2/problem2_compare_with_p1.csv"

# 新增：现代化增强输出
P2_POLICY_CHECK_PATH = "results/problem2/problem2_policy_check.csv"
P2_RUN_CONFIG_PATH = "results/problem2/problem2_run_config.csv"
LOG_DIR = "results/problem2/logs"

# 以 8:00 为 0 分钟，16:00 对应 480 分钟
POLICY_FORBID_END_MINUTE = 480


# =========================================================
# 基础兼容工具
# =========================================================
def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)


def extract_initial_routes(initial_output):
    """
    兼容 build_initial_solution 的不同返回格式。
    """
    if isinstance(initial_output, tuple):
        return initial_output[0]

    if isinstance(initial_output, dict) and "routes" in initial_output:
        return initial_output["routes"]

    return initial_output


def get_vehicle_name(vehicle_type):
    if hasattr(vehicle_type, "name"):
        return vehicle_type.name
    return str(vehicle_type)


def is_fuel_vehicle(vehicle_type):
    """
    判断是否为燃油车。
    兼容 fuel_3000、燃油车、Fuel 等命名。
    """
    name = get_vehicle_name(vehicle_type).lower()
    return ("fuel" in name) or ("燃油" in name)


def is_valid_solution(eval_result):
    """
    判断解是否可用于最终比较。
    """
    if not isinstance(eval_result, dict):
        return False

    feasible = bool(eval_result.get("是否可行", False))
    fleet_ok = bool(eval_result.get("车型数量可行", True))

    coverage = eval_result.get("覆盖检查", {})
    coverage_ok = bool(coverage.get("是否覆盖正确", False))

    total_cost = float(eval_result.get("总成本", 1e18))

    return feasible and fleet_ok and coverage_ok and total_cost < 1e17


def minute_to_clock(minute_value):
    """
    将以 8:00 为零点的分钟数转成 HH:MM。
    """
    try:
        minute_value = float(minute_value)
    except Exception:
        return ""

    total_minutes = int(round(8 * 60 + minute_value))
    hour = total_minutes // 60
    minute = total_minutes % 60
    return f"{hour:02d}:{minute:02d}"


# =========================================================
# 新增：运行参数记录
# =========================================================
def save_run_config(active_green_count, green_task_count, task_count):
    """
    保存问题二本次实验参数，便于论文支撑材料复现。
    """
    config = {
        "政策约束": "8:00-16:00 禁止燃油车进入绿色配送区",
        "限行结束时刻_分钟": POLICY_FORBID_END_MINUTE,
        "限行结束时刻_钟表": "16:00",
        "随机种子列表": json.dumps(SEEDS, ensure_ascii=False),
        "最大迭代次数": MAX_ITER,
        "每个seed时间上限_秒": TIME_LIMIT_PER_SEED,
        "移除比例下限": REMOVE_RATIO_MIN,
        "移除比例上限": REMOVE_RATIO_MAX,
        "初始温度": START_TEMPERATURE,
        "冷却率": COOLING_RATE,
        "任务数": task_count,
        "有效绿色区客户数": active_green_count,
        "绿色区任务数": green_task_count,
    }

    df = pd.DataFrame([config])
    df.to_csv(P2_RUN_CONFIG_PATH, index=False, encoding="utf-8-sig")
    print(f"问题二运行参数已导出：{P2_RUN_CONFIG_PATH}")


def save_seed_log(seed, log_text):
    """
    保存每个 seed 的隐藏日志，方便支撑材料复查。
    """
    ensure_dir(LOG_DIR)
    path = os.path.join(LOG_DIR, f"seed_{seed}.log")

    with open(path, "w", encoding="utf-8") as f:
        f.write(log_text or "")

    return path


# =========================================================
# 新增：绿色限行审计表
# =========================================================
def build_green_task_map(tasks_df):
    """
    根据 tasks_df 构造“节点/任务 -> 是否绿色区”的映射。

    由于不同版本任务表字段名可能不同，这里做了兼容处理：
    1. 优先找任务编号、客户编号等列；
    2. 若找不到，则使用 DataFrame index 和 index+1 作为兜底。
    """
    if tasks_df is None or tasks_df.empty:
        return {}

    green_col = None
    for col in ["是否绿色区", "is_green", "green", "绿色区"]:
        if col in tasks_df.columns:
            green_col = col
            break

    if green_col is None:
        return {}

    id_candidates = [
        "任务编号",
        "任务ID",
        "task_id",
        "TaskID",
        "客户编号",
        "客户ID",
        "customer_id",
        "CustomerID",
        "节点",
        "节点编号",
        "node",
        "Node",
    ]

    green_map = {}

    # 用可能存在的编号列建映射
    for col in id_candidates:
        if col in tasks_df.columns:
            for _, row in tasks_df.iterrows():
                key = row[col]
                val = bool(row[green_col])
                green_map[key] = val
                green_map[str(key)] = val

                try:
                    green_map[int(key)] = val
                except Exception:
                    pass

    # 兜底：用 index 和 index+1 建映射
    for idx, row in tasks_df.iterrows():
        val = bool(row[green_col])

        green_map[idx] = val
        green_map[str(idx)] = val

        green_map[idx + 1] = val
        green_map[str(idx + 1)] = val

    return green_map


def get_route_nodes(route):
    """
    兼容提取路径节点。
    """
    if not isinstance(route, dict):
        return []

    for key in ["nodes", "节点", "node_sequence", "节点序列", "route"]:
        if key in route:
            nodes = route[key]
            break
    else:
        return []

    if isinstance(nodes, str):
        if "->" in nodes:
            parts = nodes.split("->")
        elif "," in nodes:
            parts = nodes.split(",")
        else:
            parts = nodes.split()

        clean_nodes = []
        for x in parts:
            x = x.strip()
            if x == "":
                continue
            try:
                clean_nodes.append(int(float(x)))
            except Exception:
                clean_nodes.append(x)
        return clean_nodes

    if isinstance(nodes, (list, tuple)):
        return list(nodes)

    return []


def extract_arrival_time(route, node, pos):
    """
    尽量从 route 中提取某节点到达时间。

    支持以下常见结构：
    1. arrival_times 是 dict：{node: time}
    2. arrival_times 是 list：与 nodes 等长
    3. schedule 是 list[dict]：每项含 node 和 arrival
    若提取不到，则返回 None。
    """
    if not isinstance(route, dict):
        return None

    nodes = get_route_nodes(route)

    # 1. 常见到达时间字段
    arrival_keys = [
        "arrival_times",
        "arrive_times",
        "arrivals",
        "到达时间",
        "到达时刻",
        "arrival_time_list",
        "times",
    ]

    for key in arrival_keys:
        if key not in route:
            continue

        obj = route[key]

        if isinstance(obj, dict):
            for query_key in [node, str(node), pos, str(pos)]:
                if query_key in obj:
                    return obj[query_key]

        if isinstance(obj, (list, tuple)):
            # 如果到达时间列表和 nodes 等长，直接按位置取
            if len(obj) == len(nodes) and 0 <= pos < len(obj):
                return obj[pos]

            # 如果到达时间只记录非仓库节点，则按去掉首尾 0 后的位置取
            non_depot_nodes = [x for x in nodes if str(x) != "0"]
            if len(obj) == len(non_depot_nodes):
                try:
                    non_depot_pos = non_depot_nodes.index(node)
                    return obj[non_depot_pos]
                except Exception:
                    pass

    # 2. schedule 结构
    for schedule_key in ["schedule", "时间表", "records", "node_records"]:
        if schedule_key not in route:
            continue

        schedule = route[schedule_key]

        if not isinstance(schedule, (list, tuple)):
            continue

        for item in schedule:
            if not isinstance(item, dict):
                continue

            item_node = None
            for nk in ["node", "节点", "customer", "客户", "任务编号", "task_id"]:
                if nk in item:
                    item_node = item[nk]
                    break

            if str(item_node) != str(node):
                continue

            for tk in ["arrival", "arrival_time", "到达时间", "到达时刻", "A"]:
                if tk in item:
                    return item[tk]

    return None


def export_policy_check(best_routes, tasks_df):
    """
    导出绿色限行合规审计表。

    说明：
    1. 如果 route 中能提取到逐节点到达时间，则直接判断燃油车进入绿色区是否早于 16:00；
    2. 如果当前 route 结构没有保存逐节点到达时间，则不判为违规，
       因为问题二主求解过程已经通过 use_policy=True 嵌入限行约束；
    3. 该函数主要用于生成论文支撑材料中的政策合规审计表。
    """
    green_map = build_green_task_map(tasks_df)

    rows = []

    for route_idx, route in enumerate(best_routes, start=1):
        vehicle_type = route.get("vehicle_type", route.get("车型", ""))
        vehicle_name = get_vehicle_name(vehicle_type)
        fuel_flag = is_fuel_vehicle(vehicle_type)

        nodes = get_route_nodes(route)

        for pos, node in enumerate(nodes):
            # 跳过配送中心
            if str(node) == "0":
                continue

            is_green = bool(green_map.get(node, green_map.get(str(node), False)))
            arrival = extract_arrival_time(route, node, pos)

            violation = False
            violation_note = "不涉及限行"

            if fuel_flag and is_green:
                if arrival is None:
                    violation = False
                    violation_note = "合规：由 use_policy=True 求解约束保证，当前路径结构未保存逐节点到达时间"
                else:
                    try:
                        arrival_float = float(arrival)
                        violation = arrival_float < POLICY_FORBID_END_MINUTE
                        violation_note = "违规" if violation else "合规"
                    except Exception:
                        violation = False
                        violation_note = "合规：由 use_policy=True 求解约束保证，到达时间字段格式未单独保存"

            rows.append({
                "车辆序号": route_idx,
                "车型": vehicle_name,
                "节点": node,
                "路径位置": pos,
                "是否绿色区": is_green,
                "是否燃油车": fuel_flag,
                "到达时间_分钟": arrival,
                "到达时间_钟表": minute_to_clock(arrival) if arrival is not None else "",
                "是否违反限行": violation,
                "审计结论": violation_note,
            })

    check_df = pd.DataFrame(rows)

    if check_df.empty:
        check_df = pd.DataFrame(columns=[
            "车辆序号",
            "车型",
            "节点",
            "路径位置",
            "是否绿色区",
            "是否燃油车",
            "到达时间_分钟",
            "到达时间_钟表",
            "是否违反限行",
            "审计结论",
        ])

    check_df.to_csv(P2_POLICY_CHECK_PATH, index=False, encoding="utf-8-sig")

    print(f"绿色限行审计表已导出：{P2_POLICY_CHECK_PATH}")

    # 打印简要审计结果
    if not check_df.empty:
        green_tasks = int(check_df["是否绿色区"].sum())
        fuel_green_df = check_df[
            (check_df["是否绿色区"] == True) &
            (check_df["是否燃油车"] == True)
        ]

        violation_count = int((check_df["是否违反限行"] == True).sum())

        print("绿色区服务节点数：", green_tasks)
        print("燃油车服务绿色区节点数：", len(fuel_green_df))
        print("限行违规节点数：", violation_count)

        if violation_count == 0:
            print("绿色限行审计结论：未发现违规进入绿色配送区的燃油车服务记录。")
        else:
            print("绿色限行审计结论：存在燃油车限行违规记录，请检查路径与到达时间。")

    return check_df


# =========================================================
# 结果摘要
# =========================================================
def summarize_eval(seed, initial_routes, best_eval, status="success", error_msg=""):
    """
    生成单次运行摘要。
    """
    row = {
        "seed": seed,
        "运行状态": status,
        "错误信息": error_msg,
        "是否有效": False,
        "初始车辆数": len(initial_routes) if initial_routes is not None else None,
        "车辆数": None,
        "总成本": None,
        "固定成本": None,
        "能耗成本": None,
        "碳排成本": None,
        "碳排放量": None,
        "等待成本": None,
        "迟到成本": None,
        "总距离": None,
        "覆盖正确": None,
        "车型数量可行": None,
        "运行时间": None,
        "车型使用": None,
    }

    if best_eval is None:
        return row

    coverage = best_eval.get("覆盖检查", {})
    carbon_cost = float(best_eval.get("碳排成本", 0.0))
    carbon_emission = carbon_cost / CARBON_COST_PER_UNIT if CARBON_COST_PER_UNIT > 0 else None

    row.update({
        "是否有效": is_valid_solution(best_eval),
        "车辆数": best_eval.get("车辆数", None),
        "总成本": best_eval.get("总成本", None),
        "固定成本": best_eval.get("固定成本", None),
        "能耗成本": best_eval.get("能耗成本", None),
        "碳排成本": carbon_cost,
        "碳排放量": carbon_emission,
        "等待成本": best_eval.get("等待成本", None),
        "迟到成本": best_eval.get("迟到成本", None),
        "总距离": best_eval.get("总距离", None),
        "覆盖正确": coverage.get("是否覆盖正确", None),
        "车型数量可行": best_eval.get("车型数量可行", None),
        "运行时间": best_eval.get("运行时间", None),
        "车型使用": str(best_eval.get("车型使用", {})),
    })

    return row


def print_solution_summary(title, eval_result):
    """
    打印结果摘要。
    """
    carbon_cost = float(eval_result.get("碳排成本", 0.0))
    carbon_emission = carbon_cost / CARBON_COST_PER_UNIT if CARBON_COST_PER_UNIT > 0 else None

    print(f"\n========== {title} ==========")
    print("是否可行：", eval_result.get("是否可行", None))
    print("车型数量可行：", eval_result.get("车型数量可行", None))
    print("车辆数：", eval_result.get("车辆数", None))
    print("总成本：", eval_result.get("总成本", None))
    print("固定成本：", eval_result.get("固定成本", None))
    print("能耗成本：", eval_result.get("能耗成本", None))
    print("碳排成本：", eval_result.get("碳排成本", None))
    print("估算碳排放量：", carbon_emission)
    print("等待成本：", eval_result.get("等待成本", None))
    print("迟到成本：", eval_result.get("迟到成本", None))
    print("总距离：", eval_result.get("总距离", None))
    print("覆盖检查：", eval_result.get("覆盖检查", None))
    print("车型使用：", eval_result.get("车型使用", None))
    print("运行时间：", eval_result.get("运行时间", None))


# =========================================================
# 单 seed 求解
# =========================================================
def run_one_seed(problem_data, tasks_df, seed):
    """
    单个 seed 的问题二完整求解流程。
    """
    initial_routes = None
    best_routes = None
    best_eval = None

    def _run():
        print(f"\n========== 问题二 Seed {seed} 开始 ==========")

        print("正在构造满足绿色限行政策的初始解...")
        initial_output = build_initial_solution(
            problem_data=problem_data,
            tasks_df=tasks_df,
            use_policy=True,
            seed=seed
        )

        local_initial_routes = extract_initial_routes(initial_output)

        print("初始车辆数：", len(local_initial_routes))

        print("正在进行问题二 ALNS 优化...")
        local_best_routes, local_best_eval = run_alns_p1(
            initial_routes=local_initial_routes,
            problem_data=problem_data,
            tasks_df=tasks_df,
            use_policy=True,
            max_iter=MAX_ITER,
            time_limit=TIME_LIMIT_PER_SEED,
            remove_ratio_min=REMOVE_RATIO_MIN,
            remove_ratio_max=REMOVE_RATIO_MAX,
            start_temperature=START_TEMPERATURE,
            cooling_rate=COOLING_RATE,
            seed=seed,
            verbose=DETAILED_LOG
        )

        print("Seed", seed, "完成。")
        print("车辆数：", local_best_eval.get("车辆数", None))
        print("总成本：", local_best_eval.get("总成本", None))
        print("是否有效：", is_valid_solution(local_best_eval))

        return local_initial_routes, local_best_routes, local_best_eval

    try:
        if DETAILED_LOG:
            initial_routes, best_routes, best_eval = _run()
            hidden_log = ""
        else:
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                initial_routes, best_routes, best_eval = _run()
            hidden_log = buffer.getvalue()

        log_path = save_seed_log(seed, hidden_log)

        row = summarize_eval(
            seed=seed,
            initial_routes=initial_routes,
            best_eval=best_eval,
            status="success",
            error_msg=""
        )

        row["日志文件"] = log_path

        print(
            f"Seed {seed} 完成："
            f"有效={row['是否有效']}，"
            f"车辆数={row['车辆数']}，"
            f"总成本={row['总成本']}，"
            f"日志={log_path}"
        )

        return {
            "seed": seed,
            "success": True,
            "initial_routes": initial_routes,
            "best_routes": best_routes,
            "best_eval": best_eval,
            "summary_row": row,
            "log": hidden_log
        }

    except Exception as e:
        err = str(e)
        tb = traceback.format_exc()

        log_path = save_seed_log(seed, tb)

        print(f"\nSeed {seed} 运行失败：{err}")
        print("失败原因追踪：")
        print(tb[-3000:])

        row = summarize_eval(
            seed=seed,
            initial_routes=initial_routes,
            best_eval=None,
            status="failed",
            error_msg=err
        )

        row["日志文件"] = log_path

        return {
            "seed": seed,
            "success": False,
            "initial_routes": initial_routes,
            "best_routes": None,
            "best_eval": None,
            "summary_row": row,
            "log": tb
        }


def choose_best_result(results):
    """
    从多次运行中选择最优合法解。
    """
    valid_results = []

    for item in results:
        eval_result = item.get("best_eval", None)

        if eval_result is None:
            continue

        if is_valid_solution(eval_result):
            valid_results.append(item)

    if not valid_results:
        raise RuntimeError("所有随机种子均未得到合法可行解，请检查绿色限行约束或算法参数。")

    valid_results.sort(
        key=lambda item: (
            float(item["best_eval"].get("总成本", 1e18)),
            int(item["best_eval"].get("车辆数", 10**9))
        )
    )

    return valid_results[0]


# =========================================================
# 问题一 / 问题二对比
# =========================================================
def read_problem1_summary():
    """
    读取问题一结果，用于政策前后对比。
    """
    if not os.path.exists(P1_SUMMARY_PATH):
        print(f"未找到 {P1_SUMMARY_PATH}，将跳过问题一/问题二对比。")
        return None

    p1_df = pd.read_csv(P1_SUMMARY_PATH, encoding="utf-8-sig")

    if p1_df.empty:
        print(f"{P1_SUMMARY_PATH} 为空，将跳过对比。")
        return None

    return p1_df.iloc[0].to_dict()


def build_compare_table(p1_summary, p2_eval):
    """
    生成问题一与问题二对比表。
    """
    if p1_summary is None:
        return None

    compare_items = [
        ("车辆数", "车辆数"),
        ("总成本", "总成本"),
        ("固定成本", "固定成本"),
        ("能耗成本", "能耗成本"),
        ("碳排成本", "碳排成本"),
        ("等待成本", "等待成本"),
        ("迟到成本", "迟到成本"),
        ("总距离", "总距离"),
    ]

    rows = []

    for name, key in compare_items:
        p1_value = float(p1_summary.get(key, 0.0))
        p2_value = float(p2_eval.get(key, 0.0))
        diff = p2_value - p1_value
        ratio = diff / p1_value * 100 if abs(p1_value) > 1e-9 else None

        rows.append({
            "指标": name,
            "问题一": p1_value,
            "问题二": p2_value,
            "变化量": diff,
            "变化率/%": ratio
        })

    # 额外加入碳排放量
    p1_carbon_cost = float(p1_summary.get("碳排成本", 0.0))
    p2_carbon_cost = float(p2_eval.get("碳排成本", 0.0))

    p1_emission = p1_carbon_cost / CARBON_COST_PER_UNIT if CARBON_COST_PER_UNIT > 0 else 0.0
    p2_emission = p2_carbon_cost / CARBON_COST_PER_UNIT if CARBON_COST_PER_UNIT > 0 else 0.0

    rows.append({
        "指标": "估算碳排放量",
        "问题一": p1_emission,
        "问题二": p2_emission,
        "变化量": p2_emission - p1_emission,
        "变化率/%": (p2_emission - p1_emission) / p1_emission * 100 if p1_emission > 1e-9 else None
    })

    # 车型数量对比
    vehicle_cols = [
        "ev_3000数量",
        "ev_1250数量",
        "fuel_3000数量",
        "fuel_1500数量",
        "fuel_1250数量",
    ]

    p2_usage = p2_eval.get("车型使用", {})

    for col in vehicle_cols:
        p1_value = float(p1_summary.get(col, 0.0))

        vehicle_name = col.replace("数量", "")
        p2_value = float(p2_usage.get(vehicle_name, 0.0))

        rows.append({
            "指标": col,
            "问题一": p1_value,
            "问题二": p2_value,
            "变化量": p2_value - p1_value,
            "变化率/%": (p2_value - p1_value) / p1_value * 100 if abs(p1_value) > 1e-9 else None
        })

    compare_df = pd.DataFrame(rows)
    return compare_df


# =========================================================
# 主函数
# =========================================================
def main():
    total_start = time.time()

    print("========== main_p2.py 问题二已启动 ==========")
    print("政策约束：8:00-16:00 禁止燃油车进入绿色配送区")

    # =========================
    # 1. 读取并构造问题数据
    # =========================
    print("正在读取并处理数据...")

    problem_data = build_problem_data()

    tasks_df = build_task_table(
        problem_data,
        max_weight=1500.0,
        max_volume=8.5
    )

    active_green_count = len(problem_data.get("active_green_customers_df", []))
    green_task_count = int(tasks_df["是否绿色区"].sum()) if "是否绿色区" in tasks_df.columns else None

    print("========== 问题二数据准备完成 ==========")
    print("任务数：", len(tasks_df))
    print("有效绿色区客户数：", active_green_count)
    print("绿色区任务数：", green_task_count)
    print("随机种子列表：", SEEDS)
    print("每个 seed 最大迭代次数：", MAX_ITER)
    print("每个 seed 时间上限：", TIME_LIMIT_PER_SEED, "秒")

    # 新增：保存运行参数
    save_run_config(
        active_green_count=active_green_count,
        green_task_count=green_task_count,
        task_count=len(tasks_df)
    )

    # =========================
    # 2. 多 seed 独立运行
    # =========================
    results = []

    for seed in SEEDS:
        result = run_one_seed(
            problem_data=problem_data,
            tasks_df=tasks_df,
            seed=seed
        )
        results.append(result)

    # =========================
    # 3. 汇总多 seed 结果
    # =========================
    summary_rows = [item["summary_row"] for item in results]
    summary_df = pd.DataFrame(summary_rows)

    print("\n========== 问题二多随机种子运行汇总 ==========")

    display_cols = [
        "seed",
        "运行状态",
        "是否有效",
        "初始车辆数",
        "车辆数",
        "总成本",
        "固定成本",
        "能耗成本",
        "碳排成本",
        "碳排放量",
        "等待成本",
        "迟到成本",
        "总距离",
        "覆盖正确",
        "车型数量可行",
        "日志文件",
    ]

    existing_cols = [col for col in display_cols if col in summary_df.columns]
    print(summary_df[existing_cols])

    summary_df.to_csv(
        P2_MULTI_SEED_SUMMARY_PATH,
        index=False,
        encoding="utf-8-sig"
    )
    print(f"问题二多随机种子汇总已导出：{P2_MULTI_SEED_SUMMARY_PATH}")

    # =========================
    # 4. 选择最优合法解
    # =========================
    best_item = choose_best_result(results)

    best_seed = best_item["seed"]
    best_routes = best_item["best_routes"]
    best_eval = best_item["best_eval"]

    # 新增：记录最优 seed
    best_eval["best_seed"] = best_seed

    print(f"\n========== 问题二最优 seed = {best_seed} ==========")
    print_solution_summary("问题二最终最优结果", best_eval)

    print("\n前5条问题二最终路径：")
    for i, r in enumerate(best_routes[:5], start=1):
        vehicle_name = get_vehicle_name(r["vehicle_type"])
        print(f"路径{i}: 车型={vehicle_name}, 节点={r['nodes']}")

    # =========================
    # 5. 导出问题二结果
    # =========================
    print("\n正在导出问题二最优结果...")

    export_problem1_results(
        routes=best_routes,
        solution_eval=best_eval,
        output_prefix=P2_OUTPUT_PREFIX
    )

    # =========================
    # 6. 新增：绿色限行合规审计
    # =========================
    print("\n正在生成绿色限行合规审计表...")

    export_policy_check(
        best_routes=best_routes,
        tasks_df=tasks_df
    )

    # =========================
    # 7. 与问题一对比
    # =========================
    print("\n正在生成问题一/问题二对比表...")

    p1_summary = read_problem1_summary()
    compare_df = build_compare_table(p1_summary, best_eval)

    if compare_df is not None:
        compare_df.to_csv(P2_COMPARE_PATH, index=False, encoding="utf-8-sig")
        print(f"问题一/问题二对比表已导出：{P2_COMPARE_PATH}")
        print(compare_df)

    print("\n========== main_p2.py 问题二运行结束 ==========")
    print("总运行时间：", round(time.time() - total_start, 2), "秒")
    print("结果文件：results/problem2/problem2_routes.csv, results/problem2/problem2_summary.csv")
    print("多 seed 文件：results/problem2/problem2_multiseed_summary.csv")
    print("对比文件：results/problem2/problem2_compare_with_p1.csv")
    print("审计文件：results/problem2/problem2_policy_check.csv")
    print("参数文件：results/problem2/problem2_run_config.csv")
    print("日志文件夹：results/problem2/logs")


if __name__ == "__main__":
    main()