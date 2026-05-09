# === Project path bootstrap ===
from pathlib import Path
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
# ==============================

from data_loader import build_problem_data, build_task_table
from initial_solution import build_initial_solution, evaluate_solution
from route_merge import merge_routes_iteratively


def main():
    problem_data = build_problem_data()

    tasks_df = build_task_table(
        problem_data,
        max_weight=1500.0,
        max_volume=8.5
    )

    routes, task_map = build_initial_solution(
        problem_data=problem_data,
        tasks_df=tasks_df,
        use_policy=False
    )

    init_cost = evaluate_solution(
        routes=routes,
        problem_data=problem_data,
        task_map=task_map,
        use_policy=False
    )

    print("任务数：", len(tasks_df))
    print("合并前车辆数：", len(routes))
    print("合并前总成本：", init_cost)
    print()

    routes = merge_routes_iteratively(
        routes=routes,
        problem_data=problem_data,
        task_map=task_map,
        use_policy=False,
        max_rounds=100
    )

    final_cost = evaluate_solution(
        routes=routes,
        problem_data=problem_data,
        task_map=task_map,
        use_policy=False
    )

    print("合并后车辆数：", len(routes))
    print("合并后总成本：", final_cost)
    print()

    print("前5条路径：")
    for i, route in enumerate(routes[:5], start=1):
        print(f"路径{i}: 车型={route['vehicle_type'].name}, 节点={route['nodes']}")


if __name__ == "__main__":
    main()