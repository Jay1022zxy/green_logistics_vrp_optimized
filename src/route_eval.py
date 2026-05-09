from config import START_TIME, SERVICE_TIME, GREEN_BAN_START, GREEN_BAN_END
from cost import get_energy_and_carbon_cost, get_time_window_penalty


def get_expected_speed(current_time):
    """
    先用题目给出的各时段期望速度
    拥堵：8:00-9:00, 11:30-13:00 -> 9.8
    一般：10:00-11:30, 15:00-17:00 -> 35.4
    顺畅：9:00-10:00, 13:00-15:00 -> 55.3
    其他时段这里先按一般速度处理
    """
    if (9.0 <= current_time < 10.0) or (13.0 <= current_time < 15.0):
        return 55.3
    if (10.0 <= current_time < 11.5) or (15.0 <= current_time < 17.0):
        return 35.4
    if (8.0 <= current_time < 9.0) or (11.5 <= current_time < 13.0):
        return 9.8
    return 35.4


def get_distance(dist_matrix, id_to_matrix_idx, i, j):
    row = id_to_matrix_idx[i]
    col = id_to_matrix_idx[j]
    return float(dist_matrix[row][col])


def check_green_policy(vehicle_type, customer_row, arrival_time, use_policy):
    """
    问题2时启用：
    8:00–16:00 禁止燃油车进入绿色配送区
    """
    if not use_policy:
        return True

    if vehicle_type.energy_type != "fuel":
        return True

    if not bool(customer_row["是否绿色区"]):
        return True

    if GREEN_BAN_START <= arrival_time < GREEN_BAN_END:
        return False

    return True


def evaluate_route(route, vehicle_type, problem_data, use_policy=False):
    """
    route: [0, 3, 5, 8, 0]
    vehicle_type: config.VehicleType
    problem_data: build_problem_data() 返回的字典

    返回：
    {
        "feasible": bool,
        "violations": [],
        "total_cost": float,
        "fixed_cost": float,
        "energy_cost": float,
        "carbon_cost": float,
        "wait_cost": float,
        "late_cost": float,
        "total_distance": float,
        "arrival_times": [...],
        "service_start_times": [...],
        "departure_times": [...],
        "remaining_weight_trace": [...],
        "remaining_volume_trace": [...]
    }
    """
    all_customers_df = problem_data["all_customers_df"]
    dist_matrix = problem_data["dist_matrix"]
    id_to_matrix_idx = problem_data["id_to_matrix_idx"]

    customer_map = {
        int(row["客户编号"]): row
        for _, row in all_customers_df.iterrows()
    }

    violations = []
    feasible = True

    # 初始总载货量：按路径中所有客户需求累加
    total_weight = 0.0
    total_volume = 0.0
    for node in route:
        if node != 0:
            row = customer_map[node]
            total_weight += float(row["总重量"])
            total_volume += float(row["总体积"])

    if total_weight > vehicle_type.capacity_weight:
        feasible = False
        violations.append(f"超载重: {total_weight:.2f} > {vehicle_type.capacity_weight:.2f}")

    if total_volume > vehicle_type.capacity_volume:
        feasible = False
        violations.append(f"超容积: {total_volume:.2f} > {vehicle_type.capacity_volume:.2f}")

    current_time = START_TIME
    current_weight = total_weight
    current_volume = total_volume

    total_distance = 0.0
    total_energy_cost = 0.0
    total_carbon_cost = 0.0
    total_wait_cost = 0.0
    total_late_cost = 0.0

    arrival_times = [START_TIME]
    service_start_times = [START_TIME]
    departure_times = [START_TIME]
    remaining_weight_trace = [current_weight]
    remaining_volume_trace = [current_volume]

    for idx in range(len(route) - 1):
        i = route[idx]
        j = route[idx + 1]

        distance_ij = get_distance(dist_matrix, id_to_matrix_idx, i, j)
        speed_ij = get_expected_speed(current_time)
        travel_time_ij = distance_ij / speed_ij

        arrival_time_j = current_time + travel_time_ij
        total_distance += distance_ij

        # 当前载重率：重量和体积取更紧的那个
        load_ratio_weight = current_weight / vehicle_type.capacity_weight if vehicle_type.capacity_weight > 0 else 0
        load_ratio_volume = current_volume / vehicle_type.capacity_volume if vehicle_type.capacity_volume > 0 else 0
        load_ratio = max(load_ratio_weight, load_ratio_volume)

        energy_cost, carbon_cost = get_energy_and_carbon_cost(
            vehicle_type=vehicle_type,
            distance_km=distance_ij,
            speed=speed_ij,
            load_ratio=load_ratio
        )
        total_energy_cost += energy_cost
        total_carbon_cost += carbon_cost

        if j == 0:
            service_start_j = arrival_time_j
            departure_time_j = arrival_time_j
        else:
            customer_j = customer_map[j]

            # 绿色限行检查（问题2）
            if not check_green_policy(vehicle_type, customer_j, arrival_time_j, use_policy):
                feasible = False
                violations.append(f"绿色限行违规：客户 {j} 到达时刻 {arrival_time_j:.2f}")

            tw_early = float(customer_j["开始时间_小时"])
            tw_late = float(customer_j["结束时间_小时"])

            wait_cost, late_cost = get_time_window_penalty(arrival_time_j, tw_early, tw_late)
            total_wait_cost += wait_cost
            total_late_cost += late_cost

            service_start_j = max(arrival_time_j, tw_early)
            departure_time_j = service_start_j + SERVICE_TIME

            # 卸货后剩余载重减少
            current_weight -= float(customer_j["总重量"])
            current_volume -= float(customer_j["总体积"])

        arrival_times.append(arrival_time_j)
        service_start_times.append(service_start_j)
        departure_times.append(departure_time_j)
        remaining_weight_trace.append(current_weight)
        remaining_volume_trace.append(current_volume)

        current_time = departure_time_j

    total_cost = (
        vehicle_type.fixed_cost
        + total_energy_cost
        + total_carbon_cost
        + total_wait_cost
        + total_late_cost
    )

    return {
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
        "service_start_times": service_start_times,
        "departure_times": departure_times,
        "remaining_weight_trace": remaining_weight_trace,
        "remaining_volume_trace": remaining_volume_trace
    }