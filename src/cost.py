from config import (
    FUEL_PRICE, ELECTRICITY_PRICE, CARBON_COST_PER_UNIT,
    FUEL_CARBON_FACTOR, EV_CARBON_FACTOR,
    WAIT_COST_PER_HOUR, LATE_COST_PER_HOUR
)


def fuel_consumption_per_100km(v):
    """
    燃油车百公里油耗函数 FPK(v)
    题目给定：
    FPK(v) = 0.0025v^2 - 0.2554v + 31.75
    """
    return 0.0025 * v * v - 0.2554 * v + 31.75


def ev_consumption_per_100km(v):
    """
    新能源车百公里电耗函数 EPK(v)
    题目给定：
    EPK(v) = 0.001v^2 - 0.1v + 36.194
    """
    return 0.001 * v * v - 0.1 * v + 36.194


def load_factor_multiplier(energy_type, load_ratio):
    """
    载荷修正因子。
    燃油车满载能耗比空载高 40%，新能源车满载能耗比空载高 35%。
    """
    load_ratio = max(0.0, min(1.0, load_ratio))

    if energy_type == "fuel":
        return 1.0 + 0.4 * load_ratio

    return 1.0 + 0.35 * load_ratio


def get_energy_and_carbon_cost(vehicle_type, distance_km, speed, load_ratio):
    """
    根据车型、距离、速度和载荷率计算能源成本与碳排放成本。
    """
    multiplier = load_factor_multiplier(vehicle_type.energy_type, load_ratio)

    if vehicle_type.energy_type == "fuel":
        liters = fuel_consumption_per_100km(speed) * distance_km / 100.0 * multiplier
        energy_cost = liters * FUEL_PRICE
        carbon_emission = liters * FUEL_CARBON_FACTOR

    else:
        kwh = ev_consumption_per_100km(speed) * distance_km / 100.0 * multiplier
        energy_cost = kwh * ELECTRICITY_PRICE
        carbon_emission = kwh * EV_CARBON_FACTOR

    carbon_cost = carbon_emission * CARBON_COST_PER_UNIT

    return energy_cost, carbon_cost


def get_time_window_penalty(arrival_time, tw_early, tw_late):
    """
    软时间窗成本。
    早到产生等待成本，晚到产生迟到惩罚成本。
    """
    wait_cost = 0.0
    late_cost = 0.0

    if arrival_time < tw_early:
        wait_cost = (tw_early - arrival_time) * WAIT_COST_PER_HOUR

    elif arrival_time > tw_late:
        late_cost = (arrival_time - tw_late) * LATE_COST_PER_HOUR

    return wait_cost, late_cost