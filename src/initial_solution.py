import random
from typing import Dict, List, Any, Tuple, Optional

import pandas as pd

from alns_p1 import (
    DEFAULT_VEHICLE_SPECS,
    VEHICLE_ORDER,
    build_task_map_local,
    build_vehicle_pool,
    evaluate_route_cost,
    evaluate_solution,
    get_vehicle_name,
    get_fleet_usage,
    fleet_is_feasible,
)


# =========================================================
# 初始解策略说明
# =========================================================
# 本文件用于构造问题一 / 问题二 ALNS 的初始可行解。
#
# 本版目标：
# 1. 保留困难任务优先分配；
# 2. 保留大车和稀缺新能源车，避免过早耗尽；
# 3. 新开车时用惩罚项选择车型；
# 4. 与插入旧路径比较时使用真实成本，避免惩罚项过度阻止新开车；
# 5. 插入候选路径优先选择空间邻近路径，并保留少量随机候选；
# 6. 严格满足车型数量上限。
# =========================================================


EPS = 1e-9
BIG_COST = 1e18


# 新开车偏好顺序：先小车 / 中车，后大车
# 注意：这里只影响初始解，最终仍由 ALNS 优化。
NEW_ROUTE_VEHICLE_ORDER = [
    "ev_1250",
    "fuel_1250",
    "fuel_1500",
    "ev_3000",
    "fuel_3000",
]


REQUIRED_TASK_COLUMNS = [
    "任务编号",
    "原客户编号",
    "开始时间_小时",
    "结束时间_小时",
    "任务重量",
    "任务体积",
    "是否绿色区",
]


# =========================================================
# 基础工具
# =========================================================
def safe_float(value, default=0.0):
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def check_tasks_df(tasks_df: pd.DataFrame):
    missing = [col for col in REQUIRED_TASK_COLUMNS if col not in tasks_df.columns]

    if missing:
        raise KeyError(
            f"tasks_df 缺少必要列：{missing}，当前列为：{list(tasks_df.columns)}"
        )

    if tasks_df.empty:
        raise ValueError("tasks_df 为空，无法构造初始解。")


def normalize_task_id(task_id) -> str:
    return str(task_id)


def get_task_row(task_id: str, task_map: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    task_id = normalize_task_id(task_id)

    if task_id not in task_map:
        raise KeyError(f"task_map 中找不到任务：{task_id}")

    return task_map[task_id]


def get_task_weight_volume(row_or_dict) -> Tuple[float, float]:
    """
    兼容不同字段名，读取任务重量和体积。
    """
    weight = 0.0
    volume = 0.0

    for key in ["任务重量", "总重量", "重量"]:
        if key in row_or_dict:
            weight = safe_float(row_or_dict[key])
            break

    for key in ["任务体积", "总体积", "体积"]:
        if key in row_or_dict:
            volume = safe_float(row_or_dict[key])
            break

    return weight, volume


def get_task_time_info(task_row: Dict[str, Any]) -> Tuple[float, float]:
    start_time = safe_float(task_row.get("开始时间_小时", 999.0), 999.0)
    end_time = safe_float(task_row.get("结束时间_小时", 999.0), 999.0)
    return start_time, end_time


# =========================================================
# 车型容量相关
# =========================================================
def vehicle_can_cover_task(vehicle_name: str, task_row: Dict[str, Any]) -> bool:
    """
    只从单任务容量角度判断某车型是否能服务该任务。
    路径总容量、时间窗、绿色政策仍由 evaluate_route_cost 判断。
    """
    weight, volume = get_task_weight_volume(task_row)
    spec = DEFAULT_VEHICLE_SPECS[vehicle_name]

    return (
        weight <= spec["capacity_weight"] + EPS
        and volume <= spec["capacity_volume"] + EPS
    )


def get_capacity_feasible_vehicles(task_row: Dict[str, Any]) -> List[str]:
    feasible = []

    for vehicle_name in VEHICLE_ORDER:
        if vehicle_can_cover_task(vehicle_name, task_row):
            feasible.append(vehicle_name)

    return feasible


def count_remaining_fleet(routes: List[Dict[str, Any]], vehicle_name: str) -> int:
    usage = get_fleet_usage(routes)
    used = usage.get(vehicle_name, 0)
    limit = DEFAULT_VEHICLE_SPECS[vehicle_name]["count"]
    return max(0, limit - used)


# =========================================================
# 任务排序
# =========================================================
def get_task_sort_key_from_row(row):
    """
    初始解任务排序。

    排序优先级：
    1. 可服务车型越少，越优先；
    2. 任务越接近最大容量，越优先；
    3. 时间窗结束越早，越优先；
    4. 时间窗开始越早，越优先；
    5. 任务重量和体积越大，越优先。
    """
    row_dict = row.to_dict()

    feasible_vehicles = get_capacity_feasible_vehicles(row_dict)
    feasible_count = len(feasible_vehicles)

    weight, volume = get_task_weight_volume(row_dict)
    start_time, end_time = get_task_time_info(row_dict)

    max_weight_capacity = max(
        spec["capacity_weight"] for spec in DEFAULT_VEHICLE_SPECS.values()
    )

    max_volume_capacity = max(
        spec["capacity_volume"] for spec in DEFAULT_VEHICLE_SPECS.values()
    )

    weight_ratio = weight / max_weight_capacity if max_weight_capacity > 0 else 0.0
    volume_ratio = volume / max_volume_capacity if max_volume_capacity > 0 else 0.0
    difficulty_ratio = max(weight_ratio, volume_ratio)

    task_id = str(row_dict.get("任务编号", ""))

    return (
        feasible_count,
        -difficulty_ratio,
        end_time,
        start_time,
        -weight,
        -volume,
        task_id
    )


def get_task_ids_sorted(tasks_df: pd.DataFrame) -> List[str]:
    check_tasks_df(tasks_df)

    temp = tasks_df.copy()
    temp["_sort_key"] = temp.apply(get_task_sort_key_from_row, axis=1)
    temp = temp.sort_values("_sort_key").reset_index(drop=True)

    return [str(x) for x in temp["任务编号"].tolist()]


# =========================================================
# 新开车辆惩罚
# =========================================================
def vehicle_open_penalty(
    vehicle_name: str,
    task_row: Dict[str, Any],
    routes: List[Dict[str, Any]]
) -> float:
    """
    新开车辆的启发式惩罚项。

    说明：
    该惩罚项只用于“新开车时选择哪种车型”，不进入最终目标函数。
    """
    usage = get_fleet_usage(routes)
    used = usage.get(vehicle_name, 0)
    limit = DEFAULT_VEHICLE_SPECS[vehicle_name]["count"]

    spec = DEFAULT_VEHICLE_SPECS[vehicle_name]
    weight, volume = get_task_weight_volume(task_row)

    weight_slack = max(0.0, spec["capacity_weight"] - weight)
    volume_slack = max(0.0, spec["capacity_volume"] - volume)

    scarcity_ratio = used / max(limit, 1)

    # 车型越接近用满，越不建议继续新开该车型
    scarcity_penalty = 300.0 * scarcity_ratio

    # 容量浪费惩罚，避免小任务占用大车
    slack_penalty = 0.04 * weight_slack + 12.0 * volume_slack

    feasible_vehicles = get_capacity_feasible_vehicles(task_row)

    big_vehicle_penalty = 0.0

    if vehicle_name in ["ev_3000", "fuel_3000"]:
        # 如果小车或中车也能做，就强烈保留大车
        if any(v in feasible_vehicles for v in ["ev_1250", "fuel_1250", "fuel_1500"]):
            big_vehicle_penalty += 1600.0
        else:
            big_vehicle_penalty += 100.0

    # ev_3000 只有 10 辆，额外保留
    if vehicle_name == "ev_3000":
        big_vehicle_penalty += 900.0

    # fuel_3000 是大任务主力，也适当保留
    if vehicle_name == "fuel_3000":
        big_vehicle_penalty += 500.0

    return scarcity_penalty + slack_penalty + big_vehicle_penalty


# =========================================================
# 路径空间相似度
# =========================================================
def get_task_xy(task_row: Dict[str, Any]) -> Tuple[float, float]:
    return safe_float(task_row.get("x", 0.0)), safe_float(task_row.get("y", 0.0))


def route_spatial_score(
    route: Dict[str, Any],
    task_row: Dict[str, Any],
    task_map: Dict[str, Dict[str, Any]]
) -> float:
    """
    计算某任务与一条路径的空间接近程度。
    分数越小，说明越接近，越优先尝试插入。
    """
    tx, ty = get_task_xy(task_row)

    best_dist2 = BIG_COST

    for node in route["nodes"]:
        if node == 0 or str(node) == "0":
            continue

        try:
            row = get_task_row(node, task_map)
        except Exception:
            continue

        x, y = get_task_xy(row)
        dist2 = (tx - x) ** 2 + (ty - y) ** 2

        if dist2 < best_dist2:
            best_dist2 = dist2

    if best_dist2 >= BIG_COST / 10:
        return 0.0

    return best_dist2


# =========================================================
# 插入已有路径
# =========================================================
def try_insert_task_best_position(
    task_id: str,
    route: Dict[str, Any],
    problem_data: Dict[str, Any],
    task_map: Dict[str, Dict[str, Any]],
    use_policy: bool = False
) -> Tuple[float, Optional[Dict[str, Any]]]:
    """
    尝试把任务插入某条路径的所有位置。
    返回：
        best_delta, best_route
    """
    task_id = normalize_task_id(task_id)

    base_cost, _ = evaluate_route_cost(
        route=route,
        problem_data=problem_data,
        task_map=task_map,
        use_policy=use_policy
    )

    if base_cost >= 1e17:
        return BIG_COST, None

    best_delta = BIG_COST
    best_route = None

    nodes = list(route["nodes"])

    for pos in range(1, len(nodes)):
        candidate_nodes = nodes[:pos] + [task_id] + nodes[pos:]

        candidate_route = {
            "vehicle_type": route["vehicle_type"],
            "nodes": candidate_nodes
        }

        candidate_cost, _ = evaluate_route_cost(
            route=candidate_route,
            problem_data=problem_data,
            task_map=task_map,
            use_policy=use_policy
        )

        if candidate_cost >= 1e17:
            continue

        delta = candidate_cost - base_cost

        if delta < best_delta:
            best_delta = delta
            best_route = candidate_route

    return best_delta, best_route


def get_insert_candidate_indices(
    routes: List[Dict[str, Any]],
    task_id: str,
    task_map: Dict[str, Dict[str, Any]],
    max_candidate_routes: int,
    rng: random.Random
) -> List[int]:
    """
    选择候选插入路径。

    优先保留：
    1. 车型容量上能服务该任务的路径；
    2. 空间位置更接近该任务的路径；
    3. 少量随机路径，用于保留多样性。
    """
    task_row = get_task_row(task_id, task_map)
    feasible_vehicle_names = set(get_capacity_feasible_vehicles(task_row))

    candidate_indices = []

    for idx, route in enumerate(routes):
        vehicle_name = get_vehicle_name(route["vehicle_type"])

        if vehicle_name in feasible_vehicle_names:
            candidate_indices.append(idx)

    if len(candidate_indices) <= max_candidate_routes:
        return candidate_indices

    scored = []

    for idx in candidate_indices:
        score = route_spatial_score(
            route=routes[idx],
            task_row=task_row,
            task_map=task_map
        )
        scored.append((score, idx))

    scored.sort(key=lambda x: x[0])

    # 大部分候选取空间最近路径，少部分随机补充，避免过早局部化
    near_count = max(1, int(max_candidate_routes * 0.75))
    random_count = max_candidate_routes - near_count

    selected = [idx for _, idx in scored[:near_count]]

    remaining = [idx for _, idx in scored[near_count:]]

    if random_count > 0 and len(remaining) > 0:
        selected.extend(rng.sample(remaining, min(random_count, len(remaining))))

    return selected


# =========================================================
# 新开车辆
# =========================================================
def create_new_route_for_task(
    task_id: str,
    routes: List[Dict[str, Any]],
    vehicle_pool: Dict[str, Any],
    problem_data: Dict[str, Any],
    task_map: Dict[str, Dict[str, Any]],
    use_policy: bool = False
) -> Tuple[float, float, Optional[Dict[str, Any]]]:
    """
    为任务新开车辆。

    返回：
        best_true_cost: 新路径真实成本
        best_score:     新路径启发式评分，包含车型保留惩罚
        best_route:     最优新路径

    注意：
    best_score 只用于新开车时选择车型；
    与插入已有路径比较时，应使用 best_true_cost。
    """
    task_id = normalize_task_id(task_id)

    task_row = get_task_row(task_id, task_map)
    capacity_feasible_vehicles = get_capacity_feasible_vehicles(task_row)

    best_score = BIG_COST
    best_true_cost = BIG_COST
    best_route = None

    for vehicle_name in NEW_ROUTE_VEHICLE_ORDER:
        if vehicle_name not in capacity_feasible_vehicles:
            continue

        remaining = count_remaining_fleet(routes, vehicle_name)

        if remaining <= 0:
            continue

        vehicle_type = vehicle_pool[vehicle_name]

        candidate_route = {
            "vehicle_type": vehicle_type,
            "nodes": [0, task_id, 0]
        }

        true_cost, _ = evaluate_route_cost(
            route=candidate_route,
            problem_data=problem_data,
            task_map=task_map,
            use_policy=use_policy
        )

        if true_cost >= 1e17:
            continue

        penalty = vehicle_open_penalty(
            vehicle_name=vehicle_name,
            task_row=task_row,
            routes=routes
        )

        score = true_cost + penalty

        if score < best_score:
            best_score = score
            best_true_cost = true_cost
            best_route = candidate_route

    return best_true_cost, best_score, best_route


# =========================================================
# 诊断信息
# =========================================================
def diagnose_unassigned_task(
    task_id: str,
    routes: List[Dict[str, Any]],
    task_map: Dict[str, Dict[str, Any]]
):
    task_row = get_task_row(task_id, task_map)
    weight, volume = get_task_weight_volume(task_row)

    feasible_vehicles = get_capacity_feasible_vehicles(task_row)
    usage = get_fleet_usage(routes)

    print("\n========== 任务分配失败诊断 ==========")
    print("失败任务：", task_id)
    print("任务重量：", weight)
    print("任务体积：", volume)
    print("容量可行车型：", feasible_vehicles)
    print("当前车型使用：", usage)
    print("车型上限：", {k: v["count"] for k, v in DEFAULT_VEHICLE_SPECS.items()})
    print("剩余车辆：", {
        k: DEFAULT_VEHICLE_SPECS[k]["count"] - usage.get(k, 0)
        for k in DEFAULT_VEHICLE_SPECS
    })
    print("任务原始信息：")
    print(task_row)
    print("====================================\n")


# =========================================================
# 初始解主函数
# =========================================================
def build_initial_solution(
    problem_data: Dict[str, Any],
    tasks_df: pd.DataFrame,
    use_policy: bool = False,
    max_candidate_routes: int = 80,
    seed: int = 42
):
    """
    构造满足车型数量约束的初始解。

    返回：
        routes, solution_eval
    """
    check_tasks_df(tasks_df)

    rng = random.Random(seed)

    task_map = build_task_map_local(tasks_df)
    vehicle_pool = build_vehicle_pool([])

    task_ids = get_task_ids_sorted(tasks_df)

    routes: List[Dict[str, Any]] = []

    total_tasks = len(task_ids)

    for idx, task_id in enumerate(task_ids, start=1):
        task_id = normalize_task_id(task_id)

        best_delta = BIG_COST
        best_route_idx = None
        best_route = None

        # 1. 优先尝试插入已有路径
        candidate_indices = get_insert_candidate_indices(
            routes=routes,
            task_id=task_id,
            task_map=task_map,
            max_candidate_routes=max_candidate_routes,
            rng=rng
        )

        for r_idx in candidate_indices:
            route = routes[r_idx]

            delta, candidate_route = try_insert_task_best_position(
                task_id=task_id,
                route=route,
                problem_data=problem_data,
                task_map=task_map,
                use_policy=use_policy
            )

            if candidate_route is not None and delta < best_delta:
                best_delta = delta
                best_route_idx = r_idx
                best_route = candidate_route

        # 2. 再尝试新开车辆
        new_true_cost, new_score, new_route = create_new_route_for_task(
            task_id=task_id,
            routes=routes,
            vehicle_pool=vehicle_pool,
            problem_data=problem_data,
            task_map=task_map,
            use_policy=use_policy
        )

        # 关键点：
        # 新开车辆内部使用 new_score 选择车型；
        # 但和“插入已有路径”比较时，用真实成本 new_true_cost。
        # 这样既能保留大车，又不会过度阻止必要的新开车。
        if new_route is not None and new_true_cost < best_delta:
            best_route_idx = None
            best_route = new_route

        if best_route is None:
            diagnose_unassigned_task(
                task_id=task_id,
                routes=routes,
                task_map=task_map
            )
            raise ValueError(
                f"任务 {task_id} 无法分配。请查看上方诊断信息。"
            )

        if best_route_idx is None:
            routes.append(best_route)
        else:
            routes[best_route_idx] = best_route

        if not fleet_is_feasible(routes):
            diagnose_unassigned_task(
                task_id=task_id,
                routes=routes,
                task_map=task_map
            )
            raise ValueError(
                f"初始解构造过程中违反车型数量约束，当前车型使用：{get_fleet_usage(routes)}"
            )

        if idx % 30 == 0 or idx == total_tasks:
            usage = get_fleet_usage(routes)
            print(
                f"初始解构造进度：{idx}/{total_tasks}，"
                f"当前车辆数={len(routes)}，车型使用={usage}"
            )

    if not fleet_is_feasible(routes):
        usage = get_fleet_usage(routes)
        raise ValueError(f"初始解违反车型数量约束，车型使用情况：{usage}")

    solution_eval = evaluate_solution(
        routes=routes,
        problem_data=problem_data,
        task_map=task_map,
        use_policy=use_policy
    )

    print("========== 初始解车型使用检查 ==========")
    print("车型使用：", get_fleet_usage(routes))
    print("车型上限：", {k: v["count"] for k, v in DEFAULT_VEHICLE_SPECS.items()})
    print("初始解是否可行：", solution_eval["是否可行"])
    print("初始解车型数量可行：", solution_eval.get("车型数量可行", None))
    print("初始解总成本：", solution_eval["总成本"])

    return routes, solution_eval