from dataclasses import dataclass


@dataclass
class VehicleType:
    name: str
    energy_type: str   # "fuel" or "ev"
    capacity_weight: float
    capacity_volume: float
    count: int
    fixed_cost: float = 400.0


VEHICLE_TYPES = [
    VehicleType("fuel_3000", "fuel", 3000, 13.5, 60),
    VehicleType("fuel_1500", "fuel", 1500, 10.8, 50),
    VehicleType("fuel_1250", "fuel", 1250, 6.5, 50),
    VehicleType("ev_3000", "ev", 3000, 15.0, 10),
    VehicleType("ev_1250", "ev", 1250, 8.5, 15),
]

WAIT_COST_PER_HOUR = 20.0
LATE_COST_PER_HOUR = 50.0

FUEL_PRICE = 7.61
ELECTRICITY_PRICE = 1.64
CARBON_COST_PER_UNIT = 0.65

FUEL_CARBON_FACTOR = 2.547
EV_CARBON_FACTOR = 0.501

GREEN_RADIUS = 10.0
GREEN_BAN_START = 8.0
GREEN_BAN_END = 16.0

SERVICE_TIME = 20 / 60   # 20分钟 = 1/3小时
START_TIME = 8.0