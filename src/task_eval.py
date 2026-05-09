from config import (
    START_TIME,
    SERVICE_TIME,
    GREEN_BAN_START,
    GREEN_BAN_END,
    WAIT_COST_PER_HOUR,
    LATE_COST_PER_HOUR
)
from cost import get_energy_and_carbon_cost


# =========================================================
# 基础设置
# =========================================================
EPS = 1e-9
BIG_COST = 1e18


# =========================================================
# 速度函数
# =========================================================
def get_expected_speed(current_time):
    """
    根据当前时刻返回期望速度，单位：km/h。

    时间采用真实小时制：
    8.0  表示 8:00
    11.5 表示 11:30

    补充说明速度表：
    9:00-10:00、13:00-15:00      顺畅：55.3 km/h
    10:00-11:30、15:00-17:00     一般：35.4 km/h
    8:00-9:00、11:30-13:00       拥堵：9.8 km/h

    17:00 之后延用一般速度 35.4 km/h。
    """
    if (9.0 <= current_time < 10.0) or (13.0 <= current_time < 15.0):
        return 55.3

    if (10.0 <= current_time < 11.5) or (15.0 <= current_time < 17.0):
        return 35.4

    if (8.0 <= current_time < 9.0) or (11.5 <= current_time < 13.0):
        return 9.8

    return 35.4


def get_next_speed_boundary(current_time):
    """
    返回当前交通时段的下一个边界时刻。
    """
    boundaries = [8.0, 9.0, 10.0, 11.5, 13.0, 15.0, 17.0]

    for b in boundaries:
        if current_time < b - EPS:
            return b

    return float("inf")


def compute_time_dependent_travel(distance_km, departure_time):
    """
    计算时变速度下从 departure_time 出发、行驶 distance_km 所需时间。

    返回：
    travel_time: 行驶时间，单位小时
    effective_speed: 该弧的等效平均速度，单位 km/h
    """
    distance_km = float(distance_km)

    if distance_km <= EPS:
        return 0.0, get_expected_speed(departure_time)

    remaining_distance = distance_km
    current_time = float(departure_time)
    total_travel_time = 0.0

    max_steps = 30
    step = 0

    while remaining_distance > EPS and step < max_steps:
        step += 1

        speed = get_expected_speed(current_time)

        if speed <= EPS:
            raise ValueError(f"速度非正，当前时刻={current_time}, speed={speed}")

        next_boundary = get_next_speed_boundary(current_time)

        if next_boundary == float("inf"):
            dt = remaining_distance / speed
            total_travel_time += dt
            remaining_distance = 0.0
            break

        available_time = max(0.0, next_boundary - current_time)
        available_distance = speed * available_time

        if available_distance + EPS >= remaining_distance:
            dt = remaining_distance / speed
            total_travel_time += dt
            remaining_distance = 0.0
            break

        remaining_distance -= available_distance
        total_travel_time += available_time
        current_time = next_boundary

    if remaining_distance > EPS:
        speed = get_expected_speed(current_time)
        total_travel_time += remaining_distance / speed

    if total_travel_time <= EPS:
        effective_speed = get_expected_speed(departure_time)
    else:
        effective_speed = distance_km / total_travel_time

    return total_travel_time, effective_speed


# =========================================================
# 数据读取工具
# =========================================================
def is_depot_node(node):
    return node == 0 or str(node) == "0"


def normalize_task_id(node):
    return str(node)


def get_distance(dist_matrix, id_to_matrix_idx, i, j):
    """
    从距离矩阵中读取节点 i 到节点 j 的距离。
    """
    i = int(i)
    j = int(j)

    if i not in id_to_matrix_idx:
        raise KeyError(f"距离矩阵中找不到节点 ID：{i}")

    if j not in id_to_matrix_idx:
        raise KeyError(f"距离矩阵中找不到节点 ID：{j}")

    row = id_to_matrix_idx[i]
    col = id_to_matrix_idx[j]

    return float(dist_matrix[row][col])


def build_task_map(tasks_df):
    """
    将任务表转换为字典，key 为任务编号字符串。
    """
    task_map = {}

    for row in tasks_df.to_dict("records"):
        task_id = str(row["任务编号"])
        task_map[task_id] = row

    return task_map


def get_task_row(task_map, task_id):
    task_id = normalize_task_id(task_id)

    if task_id not in task_map:
        raise KeyError(f"task_map 中找不到任务编号：{task_id}")

    return task_map[task_id]


def get_origin_customer_id(task_map, node):
    """
    将虚拟任务编号转换为原始客户编号。
    配送中心返回 0。
    """
    if is_depot_node(node):
        return 0

    task_row = get_task_row(task_map, node)

    return int(task_row["原客户编号"])


# =========================================================
# 绿色配送区政策处理
# =========================================================
def is_green_policy_affected(vehicle_type, task_row, use_policy):
    """
    判断当前车辆访问当前任务是否受绿色限行政策影响。
    """
    if not use_policy:
        return False

    if vehicle_type.energy_type != "fuel":
        return False

    if not bool(task_row["是否绿色区"]):
        return False

    return True


def apply_green_policy_wait(vehicle_type, task_row, physical_arrival_time, use_policy):
    """
    问题二绿色配送区政策处理。

    政策：8:00-16:00 禁止燃油车进入绿色配送区。

    处理方式：
    - 若新能源车访问绿色区：不受限制；
    - 若燃油车访问非绿色区：不受限制；
    - 若燃油车访问绿色区，且物理到达时刻位于 [8:00, 16:00)，
      则认为车辆在绿色区外等待至 16:00 后进入并服务；
    - 该政策等待时间计入等待成本。

    返回：
    adjusted_arrival_time: 可进入客户点的时刻
    policy_wait_time: 因绿色限行产生的等待时间
    """
    physical_arrival_time = float(physical_arrival_time)

    if not is_green_policy_affected(vehicle_type, task_row, use_policy):
        return physical_arrival_time, 0.0

    if GREEN_BAN_START <= physical_arrival_time < GREEN_BAN_END:
        policy_wait_time = GREEN_BAN_END - physical_arrival_time
        adjusted_arrival_time = GREEN_BAN_END
        return adjusted_arrival_time, policy_wait_time

    return physical_arrival_time, 0.0


# =========================================================
# 时间窗成本
# =========================================================
def compute_time_window_cost(arrival_time, tw_early, tw_late):
    """
    软时间窗成本。

    车辆早到：等待至 tw_early 开始服务，产生等待成本；
    车辆晚到：允许服务，但产生迟到惩罚成本。
    """
    service_start_time = max(arrival_time, tw_early)

    wait_time = max(0.0, tw_early - arrival_time)
    late_time = max(0.0, service_start_time - tw_late)

    wait_cost = wait_time * WAIT_COST_PER_HOUR
    late_cost = late_time * LATE_COST_PER_HOUR

    return service_start_time, wait_cost, late_cost


# =========================================================
# 路径评估主函数
# =========================================================
def evaluate_task_route(route, vehicle_type, problem_data, task_map, use_policy=False):
    """
    评估一条车辆路径。

    route 示例：
        [0, '6_1', '7_1', 0]

    返回：
        可行性、总成本、成本构成、总距离、到达/服务/离开时刻、剩余载重轨迹等。
    """
    dist_matrix = problem_data["dist_matrix"]
    id_to_matrix_idx = problem_data["id_to_matrix_idx"]

    route = list(route)

    violations = []
    feasible = True

    if len(route) < 2:
        feasible = False
        violations.append("路径长度不足")

    if not is_depot_node(route[0]):
        feasible = False
        violations.append("路径未从配送中心出发")

    if not is_depot_node(route[-1]):
        feasible = False
        violations.append("路径未返回配送中心")

    # =====================================================
    # 1. 计算路径总需求，并检查容量
    # =====================================================
    total_weight = 0.0
    total_volume = 0.0

    visited_tasks = []

    for node in route:
        if not is_depot_node(node):
            task_id = normalize_task_id(node)
            task_row = get_task_row(task_map, task_id)

            visited_tasks.append(task_id)
            total_weight += float(task_row["任务重量"])
            total_volume += float(task_row["任务体积"])

    if total_weight > vehicle_type.capacity_weight + EPS:
        feasible = False
        violations.append(
            f"超载重: {total_weight:.2f} > {vehicle_type.capacity_weight:.2f}"
        )

    if total_volume > vehicle_type.capacity_volume + EPS:
        feasible = False
        violations.append(
            f"超容积: {total_volume:.2f} > {vehicle_type.capacity_volume:.2f}"
        )

    # =====================================================
    # 2. 初始化状态
    # =====================================================
    current_time = float(START_TIME)
    current_weight = float(total_weight)
    current_volume = float(total_volume)

    total_distance = 0.0
    total_energy_cost = 0.0
    total_carbon_cost = 0.0
    total_wait_cost = 0.0
    total_late_cost = 0.0
    total_policy_wait_cost = 0.0

    arrival_times = [current_time]
    physical_arrival_times = [current_time]
    service_start_times = [current_time]
    departure_times = [current_time]

    remaining_weight_trace = [current_weight]
    remaining_volume_trace = [current_volume]

    speed_trace = []
    distance_trace = []
    travel_time_trace = []
    policy_wait_time_trace = []

    # =====================================================
    # 3. 沿路径逐弧递推
    # =====================================================
    for idx in range(len(route) - 1):
        i = route[idx]
        j = route[idx + 1]

        origin_i = get_origin_customer_id(task_map, i)
        origin_j = get_origin_customer_id(task_map, j)

        distance_ij = get_distance(
            dist_matrix=dist_matrix,
            id_to_matrix_idx=id_to_matrix_idx,
            i=origin_i,
            j=origin_j
        )

        travel_time_ij, effective_speed_ij = compute_time_dependent_travel(
            distance_km=distance_ij,
            departure_time=current_time
        )

        physical_arrival_time_j = current_time + travel_time_ij
        adjusted_arrival_time_j = physical_arrival_time_j
        policy_wait_time = 0.0

        total_distance += distance_ij

        # 计算出发时载荷率。双容量问题取重量和体积占比的较大者。
        load_ratio_weight = (
            current_weight / vehicle_type.capacity_weight
            if vehicle_type.capacity_weight > 0 else 0.0
        )

        load_ratio_volume = (
            current_volume / vehicle_type.capacity_volume
            if vehicle_type.capacity_volume > 0 else 0.0
        )

        load_ratio = max(load_ratio_weight, load_ratio_volume)
        load_ratio = max(0.0, min(1.0, load_ratio))

        energy_cost, carbon_cost = get_energy_and_carbon_cost(
            vehicle_type=vehicle_type,
            distance_km=distance_ij,
            speed=effective_speed_ij,
            load_ratio=load_ratio
        )

        total_energy_cost += energy_cost
        total_carbon_cost += carbon_cost

        speed_trace.append(effective_speed_ij)
        distance_trace.append(distance_ij)
        travel_time_trace.append(travel_time_ij)

        if is_depot_node(j):
            service_start_j = physical_arrival_time_j
            departure_time_j = physical_arrival_time_j

        else:
            task_j = get_task_row(task_map, j)

            adjusted_arrival_time_j, policy_wait_time = apply_green_policy_wait(
                vehicle_type=vehicle_type,
                task_row=task_j,
                physical_arrival_time=physical_arrival_time_j,
                use_policy=use_policy
            )

            # 政策等待：燃油车在绿色区外等待到 16:00 后进入
            policy_wait_cost = policy_wait_time * WAIT_COST_PER_HOUR
            total_policy_wait_cost += policy_wait_cost
            total_wait_cost += policy_wait_cost

            tw_early = float(task_j["开始时间_小时"])
            tw_late = float(task_j["结束时间_小时"])

            service_start_j, wait_cost, late_cost = compute_time_window_cost(
                arrival_time=adjusted_arrival_time_j,
                tw_early=tw_early,
                tw_late=tw_late
            )

            total_wait_cost += wait_cost
            total_late_cost += late_cost

            departure_time_j = service_start_j + SERVICE_TIME

            current_weight -= float(task_j["任务重量"])
            current_volume -= float(task_j["任务体积"])

            if abs(current_weight) < 1e-7:
                current_weight = 0.0
            if abs(current_volume) < 1e-7:
                current_volume = 0.0

        physical_arrival_times.append(physical_arrival_time_j)
        arrival_times.append(adjusted_arrival_time_j)
        service_start_times.append(service_start_j)
        departure_times.append(departure_time_j)
        remaining_weight_trace.append(current_weight)
        remaining_volume_trace.append(current_volume)
        policy_wait_time_trace.append(policy_wait_time)

        current_time = departure_time_j

    # =====================================================
    # 4. 总成本
    # =====================================================
    total_cost = (
        vehicle_type.fixed_cost
        + total_energy_cost
        + total_carbon_cost
        + total_wait_cost
        + total_late_cost
    )

    # =====================================================
    # 5. 输出结果
    # =====================================================
    result = {
        # 英文字段，兼容现有 alns_p1.py
        "feasible": feasible,
        "violations": violations,
        "total_cost": total_cost,
        "fixed_cost": vehicle_type.fixed_cost,
        "energy_cost": total_energy_cost,
        "carbon_cost": total_carbon_cost,
        "wait_cost": total_wait_cost,
        "late_cost": total_late_cost,
        "total_distance": total_distance,
        "arrival_times": arrival_times,
        "physical_arrival_times": physical_arrival_times,
        "service_start_times": service_start_times,
        "departure_times": departure_times,
        "remaining_weight_trace": remaining_weight_trace,
        "remaining_volume_trace": remaining_volume_trace,
        "speed_trace": speed_trace,
        "distance_trace": distance_trace,
        "travel_time_trace": travel_time_trace,
        "policy_wait_time_trace": policy_wait_time_trace,
        "policy_wait_cost": total_policy_wait_cost,

        # 中文字段，便于调试和论文结果输出
        "是否可行": feasible,
        "违规信息": violations,
        "总成本": total_cost,
        "固定成本": vehicle_type.fixed_cost,
        "能耗成本": total_energy_cost,
        "碳排成本": total_carbon_cost,
        "等待成本": total_wait_cost,
        "迟到成本": total_late_cost,
        "总距离": total_distance,
        "到达时刻": arrival_times,
        "物理到达时刻": physical_arrival_times,
        "服务开始时刻": service_start_times,
        "离开时刻": departure_times,
        "剩余载重轨迹": remaining_weight_trace,
        "剩余体积轨迹": remaining_volume_trace,
        "速度轨迹": speed_trace,
        "分段距离": distance_trace,
        "分段行驶时间": travel_time_trace,
        "政策等待时间轨迹": policy_wait_time_trace,
        "政策等待成本": total_policy_wait_cost,
    }

    return result