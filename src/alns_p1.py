import copy
import inspect
import math
import random
import time
from types import SimpleNamespace
from typing import Dict, List, Any, Tuple

import pandas as pd

from task_eval import evaluate_task_route


# =========================
# 车型参数与数量上限
# =========================
DEFAULT_VEHICLE_SPECS = {
    "fuel_3000": {
        "name": "fuel_3000",
        "energy_type": "fuel",
        "capacity_weight": 3000,
        "capacity_volume": 13.5,
        "count": 60,
        "fixed_cost": 400.0,
    },
    "fuel_1500": {
        "name": "fuel_1500",
        "energy_type": "fuel",
        "capacity_weight": 1500,
        "capacity_volume": 10.8,
        "count": 50,
        "fixed_cost": 400.0,
    },
    "fuel_1250": {
        "name": "fuel_1250",
        "energy_type": "fuel",
        "capacity_weight": 1250,
        "capacity_volume": 6.5,
        "count": 50,
        "fixed_cost": 400.0,
    },
    "ev_3000": {
        "name": "ev_3000",
        "energy_type": "ev",
        "capacity_weight": 3000,
        "capacity_volume": 15.0,
        "count": 10,
        "fixed_cost": 400.0,
    },
    "ev_1250": {
        "name": "ev_1250",
        "energy_type": "ev",
        "capacity_weight": 1250,
        "capacity_volume": 8.5,
        "count": 15,
        "fixed_cost": 400.0,
    },
}

VEHICLE_ORDER = [
    "ev_3000",
    "ev_1250",
    "fuel_3000",
    "fuel_1500",
    "fuel_1250",
]


# =========================
# 结果字段兼容
# =========================
def result_get(result: Dict[str, Any], chinese_key: str, english_key: str, default=None):
    if chinese_key in result:
        return result[chinese_key]
    if english_key in result:
        return result[english_key]
    return default


def is_result_feasible(result: Dict[str, Any]) -> bool:
    return bool(result_get(result, "是否可行", "feasible", False))


def get_result_cost(result: Dict[str, Any]) -> float:
    return float(result_get(result, "总成本", "total_cost", 1e18))


def get_result_fixed_cost(result: Dict[str, Any]) -> float:
    return float(result_get(result, "固定成本", "fixed_cost", 0.0))


def get_result_energy_cost(result: Dict[str, Any]) -> float:
    return float(result_get(result, "能耗成本", "energy_cost", 0.0))


def get_result_carbon_cost(result: Dict[str, Any]) -> float:
    return float(result_get(result, "碳排成本", "carbon_cost", 0.0))


def get_result_wait_cost(result: Dict[str, Any]) -> float:
    return float(result_get(result, "等待成本", "wait_cost", 0.0))


def get_result_late_cost(result: Dict[str, Any]) -> float:
    return float(result_get(result, "迟到成本", "late_cost", 0.0))


def get_result_distance(result: Dict[str, Any]) -> float:
    return float(result_get(result, "总距离", "total_distance", 0.0))


def get_result_arrival_times(result: Dict[str, Any]):
    return result_get(result, "到达时刻", "arrival_times", "")


def get_result_service_start_times(result: Dict[str, Any]):
    return result_get(result, "服务开始时刻", "service_start_times", "")


def get_result_departure_times(result: Dict[str, Any]):
    return result_get(result, "离开时刻", "departure_times", "")


def get_result_violations(result: Dict[str, Any]):
    return result_get(result, "违规信息", "violations", [])


# =========================
# 车型与任务工具
# =========================
def get_vehicle_name(vehicle_type):
    if hasattr(vehicle_type, "name"):
        return vehicle_type.name
    return str(vehicle_type)


def make_vehicle_type(name: str):
    if name not in DEFAULT_VEHICLE_SPECS:
        raise ValueError(f"未知车型：{name}")

    return SimpleNamespace(**DEFAULT_VEHICLE_SPECS[name])


def build_vehicle_pool(initial_routes: List[Any]) -> Dict[str, Any]:
    """
    优先使用初始解中的 VehicleType 对象。
    如果初始解里没有某类车，则用 SimpleNamespace 构造兼容对象。
    """
    vehicle_pool = {}

    for route in initial_routes:
        if not isinstance(route, dict):
            continue

        if "vehicle_type" in route:
            vehicle = route["vehicle_type"]
        elif "车型" in route:
            vehicle = route["车型"]
        else:
            continue

        vehicle_pool[get_vehicle_name(vehicle)] = vehicle

    for name in DEFAULT_VEHICLE_SPECS:
        if name not in vehicle_pool:
            vehicle_pool[name] = make_vehicle_type(name)

    return vehicle_pool


def build_task_map_local(tasks_df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    if "任务编号" not in tasks_df.columns:
        raise KeyError("tasks_df 中缺少列：任务编号")

    task_map = {}
    for _, row in tasks_df.iterrows():
        task_id = str(row["任务编号"])
        task_map[task_id] = row.to_dict()

    return task_map


def get_task_ids(tasks_df: pd.DataFrame) -> List[str]:
    if "任务编号" not in tasks_df.columns:
        raise KeyError("tasks_df 中缺少列：任务编号")
    return [str(x) for x in tasks_df["任务编号"].tolist()]


def normalize_route(route: Any) -> Dict[str, Any]:
    if isinstance(route, dict):
        vehicle_type = None
        nodes = None

        for key in ["vehicle_type", "车型", "type", "vehicle", "车辆类型"]:
            if key in route:
                vehicle_type = route[key]
                break

        for key in ["nodes", "节点", "route", "path", "路径", "node_list"]:
            if key in route:
                nodes = route[key]
                break

        if vehicle_type is None:
            raise KeyError(f"路径缺少车型字段，当前字段为：{list(route.keys())}")

        if nodes is None:
            raise KeyError(f"路径缺少节点字段，当前字段为：{list(route.keys())}")

        return {
            "vehicle_type": vehicle_type,
            "nodes": list(nodes)
        }

    if isinstance(route, tuple) and len(route) == 2:
        vehicle_type, nodes = route
        return {
            "vehicle_type": vehicle_type,
            "nodes": list(nodes)
        }

    raise TypeError(f"无法识别路径格式：{route}")


def normalize_solution(routes: List[Any]) -> List[Dict[str, Any]]:
    return [normalize_route(r) for r in routes]


def route_tasks(route: Dict[str, Any]) -> List[str]:
    return [str(x) for x in route["nodes"] if x != 0 and str(x) != "0"]


def clean_solution(routes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    cleaned = []

    for r in routes:
        vehicle_type = r["vehicle_type"]

        tasks = []
        for x in r["nodes"]:
            if x == 0 or str(x) == "0":
                continue
            tasks.append(str(x))

        if len(tasks) == 0:
            continue

        cleaned.append({
            "vehicle_type": vehicle_type,
            "nodes": [0] + tasks + [0]
        })

    return cleaned


# =========================
# 车型数量约束
# =========================
def get_fleet_usage(routes: List[Dict[str, Any]]) -> Dict[str, int]:
    usage = {name: 0 for name in DEFAULT_VEHICLE_SPECS.keys()}

    for route in routes:
        name = get_vehicle_name(route["vehicle_type"])
        usage[name] = usage.get(name, 0) + 1

    return usage


def fleet_is_feasible(routes: List[Dict[str, Any]]) -> bool:
    usage = get_fleet_usage(routes)

    for name, used in usage.items():
        limit = DEFAULT_VEHICLE_SPECS.get(name, {}).get("count", 0)
        if used > limit:
            return False

    return True


def get_remaining_fleet_count(routes: List[Dict[str, Any]], vehicle_name: str) -> int:
    usage = get_fleet_usage(routes)
    limit = DEFAULT_VEHICLE_SPECS[vehicle_name]["count"]
    used = usage.get(vehicle_name, 0)
    return max(0, limit - used)


# =========================
# evaluate_task_route 兼容调用
# =========================
def call_evaluate_task_route(
    nodes: List[Any],
    vehicle_type: Any,
    problem_data: Dict[str, Any],
    task_map: Dict[str, Dict[str, Any]],
    use_policy: bool = False
) -> Dict[str, Any]:
    sig = inspect.signature(evaluate_task_route)
    params = sig.parameters

    kwargs = {}

    if "route" in params:
        kwargs["route"] = nodes
    elif "nodes" in params:
        kwargs["nodes"] = nodes
    elif "path" in params:
        kwargs["path"] = nodes

    if "vehicle_type" in params:
        kwargs["vehicle_type"] = vehicle_type
    elif "vehicle" in params:
        kwargs["vehicle"] = vehicle_type
    elif "车型" in params:
        kwargs["车型"] = vehicle_type

    if "problem_data" in params:
        kwargs["problem_data"] = problem_data
    elif "data" in params:
        kwargs["data"] = problem_data

    if "task_map" in params:
        kwargs["task_map"] = task_map
    elif "tasks_map" in params:
        kwargs["tasks_map"] = task_map
    elif "task_dict" in params:
        kwargs["task_dict"] = task_map

    if "use_policy" in params:
        kwargs["use_policy"] = use_policy
    elif "policy" in params:
        kwargs["policy"] = use_policy

    try:
        return evaluate_task_route(**kwargs)
    except TypeError:
        pass

    trial_calls = [
        lambda: evaluate_task_route(nodes, vehicle_type, problem_data, task_map, use_policy),
        lambda: evaluate_task_route(nodes, vehicle_type, problem_data, task_map),
        lambda: evaluate_task_route(nodes, vehicle_type, problem_data, use_policy),
        lambda: evaluate_task_route(nodes, vehicle_type, problem_data),
    ]

    last_error = None

    for func in trial_calls:
        try:
            return func()
        except TypeError as e:
            last_error = e
            continue

    raise TypeError(f"无法适配 evaluate_task_route 参数格式。最后错误：{last_error}")


# =========================
# 成本评估
# =========================
def evaluate_route_cost(
    route: Dict[str, Any],
    problem_data: Dict[str, Any],
    task_map: Dict[str, Dict[str, Any]],
    use_policy: bool = False
) -> Tuple[float, Dict[str, Any]]:
    result = call_evaluate_task_route(
        nodes=route["nodes"],
        vehicle_type=route["vehicle_type"],
        problem_data=problem_data,
        task_map=task_map,
        use_policy=use_policy
    )

    feasible = is_result_feasible(result)
    cost = get_result_cost(result)

    if not feasible:
        return 1e18, result

    return cost, result


def evaluate_solution(
    routes: List[Dict[str, Any]],
    problem_data: Dict[str, Any],
    task_map: Dict[str, Dict[str, Any]],
    use_policy: bool = False
) -> Dict[str, Any]:
    routes = clean_solution(routes)

    fleet_ok = fleet_is_feasible(routes)
    usage = get_fleet_usage(routes)

    total_cost = 0.0
    total_fixed = 0.0
    total_energy = 0.0
    total_carbon = 0.0
    total_wait = 0.0
    total_late = 0.0
    total_distance = 0.0

    feasible = True
    route_results = []

    for idx, route in enumerate(routes):
        cost, result = evaluate_route_cost(
            route=route,
            problem_data=problem_data,
            task_map=task_map,
            use_policy=use_policy
        )

        if cost >= 1e17:
            feasible = False

        total_cost += cost
        total_fixed += get_result_fixed_cost(result)
        total_energy += get_result_energy_cost(result)
        total_carbon += get_result_carbon_cost(result)
        total_wait += get_result_wait_cost(result)
        total_late += get_result_late_cost(result)
        total_distance += get_result_distance(result)

        route_results.append({
            "route_index": idx,
            "vehicle_type": route["vehicle_type"],
            "nodes": route["nodes"],
            "result": result
        })

    if not fleet_ok:
        feasible = False
        total_cost = 1e18

    return {
        "是否可行": feasible,
        "车型数量可行": fleet_ok,
        "车型使用": usage,
        "总成本": total_cost,
        "固定成本": total_fixed,
        "能耗成本": total_energy,
        "碳排成本": total_carbon,
        "等待成本": total_wait,
        "迟到成本": total_late,
        "总距离": total_distance,
        "车辆数": len(routes),
        "route_results": route_results
    }


def check_task_coverage(routes: List[Dict[str, Any]], tasks_df: pd.DataFrame) -> Dict[str, Any]:
    all_tasks = set(get_task_ids(tasks_df))

    served = []
    for r in routes:
        served.extend(route_tasks(r))

    served_set = set(served)

    duplicated = sorted([x for x in served_set if served.count(x) > 1])
    missing = sorted(list(all_tasks - served_set))
    extra = sorted(list(served_set - all_tasks))

    return {
        "任务总数": len(all_tasks),
        "服务任务数": len(served),
        "缺失任务": missing,
        "重复任务": duplicated,
        "异常任务": extra,
        "是否覆盖正确": len(missing) == 0 and len(duplicated) == 0 and len(extra) == 0
    }


# =========================
# 破坏算子
# =========================
def random_removal(
    routes: List[Dict[str, Any]],
    remove_count: int
) -> Tuple[List[Dict[str, Any]], List[str]]:
    new_routes = copy.deepcopy(routes)

    all_pairs = []
    for r_idx, r in enumerate(new_routes):
        for task in route_tasks(r):
            all_pairs.append((r_idx, task))

    if len(all_pairs) == 0:
        return new_routes, []

    remove_count = min(remove_count, len(all_pairs))
    selected = random.sample(all_pairs, remove_count)

    removed = [task for _, task in selected]
    removed_set = set(removed)

    for r in new_routes:
        r["nodes"] = [
            x for x in r["nodes"]
            if x == 0 or str(x) not in removed_set
        ]

    return clean_solution(new_routes), removed


def worst_removal(
    routes: List[Dict[str, Any]],
    remove_count: int,
    problem_data: Dict[str, Any],
    task_map: Dict[str, Dict[str, Any]],
    use_policy: bool = False
) -> Tuple[List[Dict[str, Any]], List[str]]:
    candidates = []

    route_indices = list(range(len(routes)))
    if len(route_indices) > 60:
        route_indices = random.sample(route_indices, 60)

    for r_idx in route_indices:
        route = routes[r_idx]
        base_cost, _ = evaluate_route_cost(route, problem_data, task_map, use_policy)

        tasks = route_tasks(route)

        if len(tasks) <= 1:
            continue

        if len(tasks) > 8:
            tasks = random.sample(tasks, 8)

        for task in tasks:
            new_nodes = [
                x for x in route["nodes"]
                if x == 0 or str(x) != str(task)
            ]

            new_route = {
                "vehicle_type": route["vehicle_type"],
                "nodes": new_nodes
            }

            new_cost, _ = evaluate_route_cost(new_route, problem_data, task_map, use_policy)
            saving = base_cost - new_cost
            candidates.append((saving, task))

    if len(candidates) == 0:
        return random_removal(routes, remove_count)

    candidates.sort(reverse=True, key=lambda x: x[0])

    removed = []
    used = set()

    for _, task in candidates:
        if task not in used:
            removed.append(task)
            used.add(task)

        if len(removed) >= remove_count:
            break

    removed_set = set(removed)

    new_routes = copy.deepcopy(routes)
    for r in new_routes:
        r["nodes"] = [
            x for x in r["nodes"]
            if x == 0 or str(x) not in removed_set
        ]

    return clean_solution(new_routes), removed


def route_removal(
    routes: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], List[str]]:
    if len(routes) == 0:
        return routes, []

    new_routes = copy.deepcopy(routes)

    idx = random.randrange(len(new_routes))
    removed_route = new_routes.pop(idx)
    removed = route_tasks(removed_route)

    return clean_solution(new_routes), removed


# =========================
# 修复算子
# =========================
def try_insert_task_into_route(
    task: str,
    route: Dict[str, Any],
    base_cost: float,
    problem_data: Dict[str, Any],
    task_map: Dict[str, Dict[str, Any]],
    use_policy: bool = False
) -> Tuple[float, Dict[str, Any]]:
    best_delta = 1e18
    best_route = None

    nodes = route["nodes"]

    for pos in range(1, len(nodes)):
        candidate_nodes = nodes[:pos] + [task] + nodes[pos:]

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


def try_create_new_route(
    task: str,
    current_routes: List[Dict[str, Any]],
    vehicle_pool: Dict[str, Any],
    problem_data: Dict[str, Any],
    task_map: Dict[str, Dict[str, Any]],
    use_policy: bool = False
) -> Tuple[float, Dict[str, Any]]:
    best_cost = 1e18
    best_route = None

    for vehicle_name in VEHICLE_ORDER:
        remaining = get_remaining_fleet_count(current_routes, vehicle_name)

        if remaining <= 0:
            continue

        vehicle_type = vehicle_pool[vehicle_name]

        candidate_route = {
            "vehicle_type": vehicle_type,
            "nodes": [0, task, 0]
        }

        cost, _ = evaluate_route_cost(
            route=candidate_route,
            problem_data=problem_data,
            task_map=task_map,
            use_policy=use_policy
        )

        if cost < best_cost:
            best_cost = cost
            best_route = candidate_route

    return best_cost, best_route


def greedy_repair(
    routes: List[Dict[str, Any]],
    removed_tasks: List[str],
    vehicle_pool: Dict[str, Any],
    problem_data: Dict[str, Any],
    task_map: Dict[str, Dict[str, Any]],
    use_policy: bool = False,
    max_candidate_routes: int = 35
) -> List[Dict[str, Any]]:
    new_routes = clean_solution(copy.deepcopy(routes))

    removed_tasks = [str(x) for x in removed_tasks]
    random.shuffle(removed_tasks)

    for task in removed_tasks:
        best_delta = 1e18
        best_route_idx = None
        best_new_route = None

        candidate_indices = list(range(len(new_routes)))
        if len(candidate_indices) > max_candidate_routes:
            candidate_indices = random.sample(candidate_indices, max_candidate_routes)

        for r_idx in candidate_indices:
            route = new_routes[r_idx]

            base_cost, _ = evaluate_route_cost(
                route=route,
                problem_data=problem_data,
                task_map=task_map,
                use_policy=use_policy
            )

            if base_cost >= 1e17:
                continue

            delta, candidate_route = try_insert_task_into_route(
                task=task,
                route=route,
                base_cost=base_cost,
                problem_data=problem_data,
                task_map=task_map,
                use_policy=use_policy
            )

            if candidate_route is not None and delta < best_delta:
                best_delta = delta
                best_route_idx = r_idx
                best_new_route = candidate_route

        # 新开车，但必须受车型数量上限限制
        new_route_cost, new_route = try_create_new_route(
            task=task,
            current_routes=new_routes,
            vehicle_pool=vehicle_pool,
            problem_data=problem_data,
            task_map=task_map,
            use_policy=use_policy
        )

        if new_route is not None and new_route_cost < best_delta:
            best_route_idx = None
            best_new_route = new_route

        if best_new_route is None:
            raise ValueError(f"任务 {task} 无法插入，也无法在车型数量约束内新开车辆。")

        if best_route_idx is None:
            new_routes.append(best_new_route)
        else:
            new_routes[best_route_idx] = best_new_route

        if not fleet_is_feasible(new_routes):
            raise ValueError(f"修复后违反车型数量约束：{get_fleet_usage(new_routes)}")

    return clean_solution(new_routes)


# =========================
# 局部搜索
# =========================
def relocate_one_task(
    routes: List[Dict[str, Any]],
    vehicle_pool: Dict[str, Any],
    problem_data: Dict[str, Any],
    task_map: Dict[str, Dict[str, Any]],
    use_policy: bool = False,
    max_trials: int = 50
) -> List[Dict[str, Any]]:
    current_routes = clean_solution(copy.deepcopy(routes))

    current_eval = evaluate_solution(
        routes=current_routes,
        problem_data=problem_data,
        task_map=task_map,
        use_policy=use_policy
    )

    if not current_eval["是否可行"]:
        return routes

    best_routes = current_routes
    best_cost = current_eval["总成本"]

    all_pairs = []
    for r_idx, r in enumerate(current_routes):
        for task in route_tasks(r):
            all_pairs.append((r_idx, task))

    if len(all_pairs) == 0:
        return routes

    random.shuffle(all_pairs)
    all_pairs = all_pairs[:max_trials]

    for r_idx, task in all_pairs:
        trial_routes = copy.deepcopy(current_routes)

        trial_routes[r_idx]["nodes"] = [
            x for x in trial_routes[r_idx]["nodes"]
            if x == 0 or str(x) != str(task)
        ]

        trial_routes = clean_solution(trial_routes)

        try:
            trial_routes = greedy_repair(
                routes=trial_routes,
                removed_tasks=[task],
                vehicle_pool=vehicle_pool,
                problem_data=problem_data,
                task_map=task_map,
                use_policy=use_policy,
                max_candidate_routes=40
            )
        except Exception:
            continue

        trial_eval = evaluate_solution(
            routes=trial_routes,
            problem_data=problem_data,
            task_map=task_map,
            use_policy=use_policy
        )

        if trial_eval["是否可行"] and trial_eval["总成本"] < best_cost:
            best_cost = trial_eval["总成本"]
            best_routes = trial_routes

    return best_routes


# =========================
# ALNS 主循环
# =========================
def run_alns_p1(
    initial_routes: List[Dict[str, Any]],
    problem_data: Dict[str, Any],
    tasks_df: pd.DataFrame,
    use_policy: bool = False,
    max_iter: int = 300,
    time_limit: int = 600,
    remove_ratio_min: float = 0.04,
    remove_ratio_max: float = 0.16,
    start_temperature: float = 2000.0,
    cooling_rate: float = 0.985,
    seed: int = 42,
    verbose: bool = True
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    random.seed(seed)

    start_time = time.time()

    task_map = build_task_map_local(tasks_df)
    vehicle_pool = build_vehicle_pool(initial_routes)

    current_routes = normalize_solution(initial_routes)
    current_routes = clean_solution(current_routes)

    coverage = check_task_coverage(current_routes, tasks_df)

    if not coverage["是否覆盖正确"]:
        print("初始解覆盖检查异常：")
        print(coverage)

    if not fleet_is_feasible(current_routes):
        raise ValueError(f"初始解违反车型数量约束：{get_fleet_usage(current_routes)}")

    current_eval = evaluate_solution(
        routes=current_routes,
        problem_data=problem_data,
        task_map=task_map,
        use_policy=use_policy
    )

    if not current_eval["是否可行"]:
        print("初始解不可行，车型使用：", get_fleet_usage(current_routes))

    current_cost = current_eval["总成本"]

    best_routes = copy.deepcopy(current_routes)
    best_eval = copy.deepcopy(current_eval)
    best_cost = current_cost

    all_task_count = len(get_task_ids(tasks_df))
    temperature = start_temperature

    destroy_methods = ["random", "worst", "route"]

    if verbose:
        print("========== ALNS 开始 ==========")
        print(f"初始车辆数：{len(current_routes)}")
        print(f"初始总成本：{current_cost:.4f}")
        print(f"任务数：{all_task_count}")
        print("车型使用：", get_fleet_usage(current_routes))
        print("车型上限：", {k: v["count"] for k, v in DEFAULT_VEHICLE_SPECS.items()})

    for it in range(1, max_iter + 1):
        if time.time() - start_time > time_limit:
            if verbose:
                print("达到时间限制，提前停止。")
            break

        remove_ratio = random.uniform(remove_ratio_min, remove_ratio_max)
        remove_count = max(1, int(all_task_count * remove_ratio))
        method = random.choice(destroy_methods)

        try:
            if method == "random":
                partial_routes, removed = random_removal(current_routes, remove_count)

            elif method == "worst":
                partial_routes, removed = worst_removal(
                    routes=current_routes,
                    remove_count=remove_count,
                    problem_data=problem_data,
                    task_map=task_map,
                    use_policy=use_policy
                )

            else:
                partial_routes, removed = route_removal(current_routes)

            if len(removed) == 0:
                continue

            candidate_routes = greedy_repair(
                routes=partial_routes,
                removed_tasks=removed,
                vehicle_pool=vehicle_pool,
                problem_data=problem_data,
                task_map=task_map,
                use_policy=use_policy,
                max_candidate_routes=35
            )

            if it % 15 == 0:
                candidate_routes = relocate_one_task(
                    routes=candidate_routes,
                    vehicle_pool=vehicle_pool,
                    problem_data=problem_data,
                    task_map=task_map,
                    use_policy=use_policy,
                    max_trials=50
                )

            if not fleet_is_feasible(candidate_routes):
                continue

            candidate_eval = evaluate_solution(
                routes=candidate_routes,
                problem_data=problem_data,
                task_map=task_map,
                use_policy=use_policy
            )

            if not candidate_eval["是否可行"]:
                continue

            candidate_cost = candidate_eval["总成本"]
            delta = candidate_cost - current_cost

            accept = False

            if delta < 0:
                accept = True
            else:
                prob = math.exp(-delta / max(temperature, 1e-9))
                if random.random() < prob:
                    accept = True

            if accept:
                current_routes = candidate_routes
                current_eval = candidate_eval
                current_cost = candidate_cost

            if candidate_cost < best_cost:
                best_routes = copy.deepcopy(candidate_routes)
                best_eval = copy.deepcopy(candidate_eval)
                best_cost = candidate_cost

                if verbose:
                    print(
                        f"[Iter {it:4d}] 新最优："
                        f"cost={best_cost:.4f}, "
                        f"vehicles={len(best_routes)}, "
                        f"method={method}, "
                        f"removed={len(removed)}, "
                        f"fleet={get_fleet_usage(best_routes)}"
                    )

            temperature *= cooling_rate

        except Exception as e:
            if verbose:
                print(f"[Iter {it}] 跳过异常：{e}")
            continue

        if verbose and it % 50 == 0:
            print(
                f"[Iter {it:4d}] 当前成本={current_cost:.2f}, "
                f"最优成本={best_cost:.2f}, "
                f"温度={temperature:.2f}, "
                f"车辆数={len(best_routes)}, "
                f"车型使用={get_fleet_usage(best_routes)}"
            )

    final_coverage = check_task_coverage(best_routes, tasks_df)

    best_eval = evaluate_solution(
        routes=best_routes,
        problem_data=problem_data,
        task_map=task_map,
        use_policy=use_policy
    )

    best_eval["覆盖检查"] = final_coverage
    best_eval["运行时间"] = time.time() - start_time
    best_eval["车型使用"] = get_fleet_usage(best_routes)
    best_eval["车型数量可行"] = fleet_is_feasible(best_routes)

    if verbose:
        print("========== ALNS 结束 ==========")
        print(f"最优车辆数：{len(best_routes)}")
        print(f"最优总成本：{best_eval['总成本']:.4f}")
        print(f"覆盖正确：{final_coverage['是否覆盖正确']}")
        print(f"车型数量可行：{best_eval['车型数量可行']}")
        print(f"车型使用：{best_eval['车型使用']}")
        print(f"运行时间：{best_eval['运行时间']:.2f} 秒")

    return best_routes, best_eval


# =========================
# 结果导出
# =========================
def export_problem1_results(
    routes: List[Dict[str, Any]],
    solution_eval: Dict[str, Any],
    output_prefix: str = "problem1"
):
    route_rows = []

    for item in solution_eval["route_results"]:
        idx = item["route_index"]
        vehicle_type = item["vehicle_type"]
        nodes = item["nodes"]
        result = item["result"]

        route_rows.append({
            "路径编号": idx + 1,
            "车型": get_vehicle_name(vehicle_type),
            "节点序列": " -> ".join(map(str, nodes)),
            "是否可行": is_result_feasible(result),
            "总成本": get_result_cost(result),
            "固定成本": get_result_fixed_cost(result),
            "能耗成本": get_result_energy_cost(result),
            "碳排成本": get_result_carbon_cost(result),
            "等待成本": get_result_wait_cost(result),
            "迟到成本": get_result_late_cost(result),
            "总距离": get_result_distance(result),
            "违规信息": str(get_result_violations(result)),
            "到达时刻": str(get_result_arrival_times(result)),
            "服务开始时刻": str(get_result_service_start_times(result)),
            "离开时刻": str(get_result_departure_times(result)),
        })

    usage = solution_eval.get("车型使用", {})

    summary_rows = [{
        "是否可行": solution_eval["是否可行"],
        "车型数量可行": solution_eval.get("车型数量可行", None),
        "车辆数": solution_eval["车辆数"],
        "总成本": solution_eval["总成本"],
        "固定成本": solution_eval["固定成本"],
        "能耗成本": solution_eval["能耗成本"],
        "碳排成本": solution_eval["碳排成本"],
        "等待成本": solution_eval["等待成本"],
        "迟到成本": solution_eval["迟到成本"],
        "总距离": solution_eval["总距离"],
        "运行时间": solution_eval.get("运行时间", None),
        "覆盖正确": solution_eval.get("覆盖检查", {}).get("是否覆盖正确", None),
        "ev_3000数量": usage.get("ev_3000", 0),
        "ev_1250数量": usage.get("ev_1250", 0),
        "fuel_3000数量": usage.get("fuel_3000", 0),
        "fuel_1500数量": usage.get("fuel_1500", 0),
        "fuel_1250数量": usage.get("fuel_1250", 0),
    }]

    route_df = pd.DataFrame(route_rows)
    summary_df = pd.DataFrame(summary_rows)

    route_path = f"{output_prefix}_routes.csv"
    summary_path = f"{output_prefix}_summary.csv"

    route_df.to_csv(route_path, index=False, encoding="utf-8-sig")
    summary_df.to_csv(summary_path, index=False, encoding="utf-8-sig")

    print(f"路径结果已导出：{route_path}")
    print(f"汇总结果已导出：{summary_path}")