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

import pandas as pd

from data_loader import build_problem_data, build_task_table
from initial_solution import build_initial_solution
from alns_p1 import run_alns_p1, export_problem1_results


# =========================================================
# 多随机种子参数
# =========================================================
SEEDS = [1, 7, 21, 42, 66, 88, 100]

MAX_ITER = 300
TIME_LIMIT_PER_SEED = 180

REMOVE_RATIO_MIN = 0.04
REMOVE_RATIO_MAX = 0.16
START_TEMPERATURE = 2000.0
COOLING_RATE = 0.985

# False：每个 seed 只输出简要结果，避免控制台刷屏
# True ：输出每次 ALNS 的详细迭代过程
DETAILED_LOG = False

# 是否保存每个 seed 的简要结果表
SAVE_MULTI_SEED_SUMMARY = True
MULTI_SEED_SUMMARY_PATH = "results/problem1/problem1_multiseed_summary.csv"


def extract_initial_routes(initial_output):
    """
    兼容 build_initial_solution 的不同返回格式。

    可能情况：
    1. 直接返回 routes
    2. 返回 (routes, solution_eval)
    3. 返回 {"routes": routes, ...}
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

    row.update({
        "是否有效": is_valid_solution(best_eval),
        "车辆数": best_eval.get("车辆数", None),
        "总成本": best_eval.get("总成本", None),
        "固定成本": best_eval.get("固定成本", None),
        "能耗成本": best_eval.get("能耗成本", None),
        "碳排成本": best_eval.get("碳排成本", None),
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
    print(f"\n========== {title} ==========")
    print("是否可行：", eval_result.get("是否可行", None))
    print("车型数量可行：", eval_result.get("车型数量可行", None))
    print("车辆数：", eval_result.get("车辆数", None))
    print("总成本：", eval_result.get("总成本", None))
    print("固定成本：", eval_result.get("固定成本", None))
    print("能耗成本：", eval_result.get("能耗成本", None))
    print("碳排成本：", eval_result.get("碳排成本", None))
    print("等待成本：", eval_result.get("等待成本", None))
    print("迟到成本：", eval_result.get("迟到成本", None))
    print("总距离：", eval_result.get("总距离", None))
    print("覆盖检查：", eval_result.get("覆盖检查", None))
    print("车型使用：", eval_result.get("车型使用", None))
    print("运行时间：", eval_result.get("运行时间", None))


def run_one_seed(problem_data, tasks_df, seed):
    """
    单个 seed 的完整求解流程。
    """
    initial_routes = None
    best_routes = None
    best_eval = None

    def _run():
        print(f"\n========== Seed {seed} 开始 ==========")

        print("正在构造初始解...")
        initial_output = build_initial_solution(
            problem_data=problem_data,
            tasks_df=tasks_df,
            use_policy=False,
            seed=seed
        )

        local_initial_routes = extract_initial_routes(initial_output)

        print("初始车辆数：", len(local_initial_routes))

        print("正在进行 ALNS 优化...")
        local_best_routes, local_best_eval = run_alns_p1(
            initial_routes=local_initial_routes,
            problem_data=problem_data,
            tasks_df=tasks_df,
            use_policy=False,
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

        row = summarize_eval(
            seed=seed,
            initial_routes=initial_routes,
            best_eval=best_eval,
            status="success",
            error_msg=""
        )

        print(
            f"Seed {seed} 完成："
            f"有效={row['是否有效']}，"
            f"车辆数={row['车辆数']}，"
            f"总成本={row['总成本']}"
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

        print(f"\nSeed {seed} 运行失败：{err}")

        if not DETAILED_LOG:
            print("失败原因追踪：")
            print(tb[-3000:])

        row = summarize_eval(
            seed=seed,
            initial_routes=initial_routes,
            best_eval=None,
            status="failed",
            error_msg=err
        )

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
        raise RuntimeError("所有随机种子均未得到合法可行解，请检查约束或算法参数。")

    valid_results.sort(
        key=lambda item: (
            float(item["best_eval"].get("总成本", 1e18)),
            int(item["best_eval"].get("车辆数", 10**9))
        )
    )

    return valid_results[0]


def main():
    total_start = time.time()

    print("========== main_p1.py 多随机种子版已启动 ==========")

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

    print("========== 问题一数据准备完成 ==========")
    print("任务数：", len(tasks_df))
    print("随机种子列表：", SEEDS)
    print("每个 seed 最大迭代次数：", MAX_ITER)
    print("每个 seed 时间上限：", TIME_LIMIT_PER_SEED, "秒")

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

    print("\n========== 多随机种子运行汇总 ==========")
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
        "等待成本",
        "迟到成本",
        "总距离",
        "覆盖正确",
        "车型数量可行",
    ]

    existing_cols = [col for col in display_cols if col in summary_df.columns]
    print(summary_df[existing_cols])

    if SAVE_MULTI_SEED_SUMMARY:
        summary_df.to_csv(
            MULTI_SEED_SUMMARY_PATH,
            index=False,
            encoding="utf-8-sig"
        )
        print(f"多随机种子汇总已导出：{MULTI_SEED_SUMMARY_PATH}")

    # =========================
    # 4. 选择最优合法解
    # =========================
    best_item = choose_best_result(results)

    best_seed = best_item["seed"]
    best_routes = best_item["best_routes"]
    best_eval = best_item["best_eval"]

    print(f"\n========== 最优 seed = {best_seed} ==========")
    print_solution_summary("问题一最终最优结果", best_eval)

    print("\n前5条最终路径：")
    for i, r in enumerate(best_routes[:5], start=1):
        vehicle_name = get_vehicle_name(r["vehicle_type"])
        print(f"路径{i}: 车型={vehicle_name}, 节点={r['nodes']}")

    # =========================
    # 5. 导出最优结果
    # =========================
    print("\n正在导出问题一最优结果...")

    export_problem1_results(
        routes=best_routes,
        solution_eval=best_eval,
        output_prefix="results/problem1/problem1"
    )

    print("\n========== main_p1.py 多随机种子版运行结束 ==========")
    print("总运行时间：", round(time.time() - total_start, 2), "秒")
    print("最终结果文件：results/problem1/problem1_routes.csv, results/problem1/problem1_summary.csv")
    print("多种子汇总文件：", MULTI_SEED_SUMMARY_PATH)


if __name__ == "__main__":
    main()