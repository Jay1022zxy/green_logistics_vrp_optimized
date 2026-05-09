import os
import math
from pathlib import Path

import pandas as pd

try:
    from config import GREEN_RADIUS
except Exception:
    GREEN_RADIUS = 10.0


# =========================================================
# 数据文件配置
# =========================================================
DATA_DIR = "data/raw"

ORDERS_FILE = "订单信息.xlsx"
DIST_FILE = "距离矩阵.xlsx"
COORDS_FILE = "客户坐标信息.xlsx"
TIME_WINDOW_FILE = "时间窗.xlsx"


# =========================================================
# 基础工具函数
# =========================================================
def time_to_float(t):
    """
    将时间转换为小时制浮点数。
    例如：
    '11:30' -> 11.5
    '8:00'  -> 8.0
    11.5    -> 11.5
    """
    if pd.isna(t):
        return None

    # 处理 pandas / datetime 的 time 对象
    if hasattr(t, "hour") and hasattr(t, "minute"):
        return float(t.hour) + float(t.minute) / 60.0

    s = str(t).strip()

    if ":" in s:
        parts = s.split(":")
        hh = int(parts[0])
        mm = int(parts[1])
        return hh + mm / 60.0

    return float(s)


def check_required_columns(df, required_cols, df_name):
    """
    检查 DataFrame 是否包含必要列。
    """
    missing = [col for col in required_cols if col not in df.columns]

    if missing:
        raise KeyError(
            f"{df_name} 缺少必要列：{missing}；当前列为：{list(df.columns)}"
        )


def ensure_file_exists(path):
    """
    检查文件是否存在。
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"找不到数据文件：{path}")


def safe_float(value, default=0.0):
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def safe_int(value):
    return int(float(value))


# =========================================================
# 读取原始数据
# =========================================================
def load_all_data(base_path=DATA_DIR):
    """
    读取四个原始数据文件：
    1. 订单信息.xlsx
    2. 距离矩阵.xlsx
    3. 客户坐标信息.xlsx
    4. 时间窗.xlsx
    """
    base_path = Path(base_path)

    orders_path = base_path / ORDERS_FILE
    dist_path = base_path / DIST_FILE
    coords_path = base_path / COORDS_FILE
    tw_path = base_path / TIME_WINDOW_FILE

    for path in [orders_path, dist_path, coords_path, tw_path]:
        ensure_file_exists(path)

    orders_df = pd.read_excel(orders_path, engine="openpyxl")
    dist_df = pd.read_excel(dist_path, engine="openpyxl")
    coords_df = pd.read_excel(coords_path, engine="openpyxl")
    tw_df = pd.read_excel(tw_path, engine="openpyxl")

    check_required_columns(
        orders_df,
        ["订单编号", "重量", "体积", "目标客户编号"],
        "订单信息.xlsx"
    )

    check_required_columns(
        coords_df,
        ["类型", "ID", "X (km)", "Y (km)"],
        "客户坐标信息.xlsx"
    )

    check_required_columns(
        tw_df,
        ["客户编号", "开始时间", "结束时间"],
        "时间窗.xlsx"
    )

    if "客户" not in dist_df.columns:
        raise KeyError(
            f"距离矩阵.xlsx 缺少必要列：客户；当前列为：{list(dist_df.columns)}"
        )

    return orders_df, dist_df, coords_df, tw_df


# =========================================================
# 需求汇总
# =========================================================
def build_demand_table(orders_df):
    """
    将订单信息按客户编号汇总为客户需求。
    """
    demand_df = (
        orders_df
        .groupby("目标客户编号", as_index=False)[["重量", "体积"]]
        .sum()
        .rename(columns={
            "目标客户编号": "客户编号",
            "重量": "总重量",
            "体积": "总体积"
        })
    )

    demand_df["客户编号"] = demand_df["客户编号"].astype(int)
    demand_df["总重量"] = demand_df["总重量"].astype(float)
    demand_df["总体积"] = demand_df["总体积"].astype(float)

    return demand_df


# =========================================================
# 客户坐标表
# =========================================================
def build_customer_base_table(coords_df):
    """
    提取客户坐标，不包含配送中心。
    """
    customer_base_df = (
        coords_df[coords_df["类型"] == "客户"][["ID", "X (km)", "Y (km)"]]
        .rename(columns={
            "ID": "客户编号",
            "X (km)": "x",
            "Y (km)": "y"
        })
        .copy()
    )

    customer_base_df["客户编号"] = customer_base_df["客户编号"].astype(int)
    customer_base_df["x"] = customer_base_df["x"].astype(float)
    customer_base_df["y"] = customer_base_df["y"].astype(float)

    return customer_base_df


def build_depot_info(coords_df):
    """
    提取配送中心信息。
    """
    depot_df = coords_df[coords_df["ID"] == 0]

    if depot_df.empty:
        raise ValueError("客户坐标信息.xlsx 中找不到配送中心 ID=0。")

    depot_row = depot_df.iloc[0]

    depot_info = {
        "depot_id": 0,
        "x": float(depot_row["X (km)"]),
        "y": float(depot_row["Y (km)"])
    }

    return depot_info


# =========================================================
# 时间窗表
# =========================================================
def build_time_window_table(tw_df):
    """
    清洗时间窗表，并转为小时制。
    """
    tw_clean_df = tw_df.copy()

    tw_clean_df["客户编号"] = tw_clean_df["客户编号"].astype(int)
    tw_clean_df["开始时间_小时"] = tw_clean_df["开始时间"].apply(time_to_float)
    tw_clean_df["结束时间_小时"] = tw_clean_df["结束时间"].apply(time_to_float)

    tw_clean_df = tw_clean_df[
        ["客户编号", "开始时间_小时", "结束时间_小时"]
    ].copy()

    if tw_clean_df["开始时间_小时"].isna().any():
        bad_ids = tw_clean_df[tw_clean_df["开始时间_小时"].isna()]["客户编号"].tolist()
        raise ValueError(f"以下客户开始时间为空或无法解析：{bad_ids}")

    if tw_clean_df["结束时间_小时"].isna().any():
        bad_ids = tw_clean_df[tw_clean_df["结束时间_小时"].isna()]["客户编号"].tolist()
        raise ValueError(f"以下客户结束时间为空或无法解析：{bad_ids}")

    invalid_df = tw_clean_df[
        tw_clean_df["结束时间_小时"] < tw_clean_df["开始时间_小时"]
    ]

    if not invalid_df.empty:
        raise ValueError(
            f"存在结束时间早于开始时间的客户：{invalid_df['客户编号'].tolist()}"
        )

    return tw_clean_df


# =========================================================
# 距离矩阵
# =========================================================
def build_distance_matrix(dist_df):
    """
    构造距离矩阵和 ID 到矩阵下标的映射。
    """
    matrix_cols = [col for col in dist_df.columns if col != "客户"]

    if len(matrix_cols) == 0:
        raise ValueError("距离矩阵中没有客户距离列。")

    # 统一矩阵列 ID 为 int
    matrix_ids = [safe_int(col) for col in matrix_cols]

    dist_matrix = dist_df[matrix_cols].to_numpy(dtype=float)

    if dist_matrix.shape[0] != dist_matrix.shape[1]:
        raise ValueError(
            f"距离矩阵不是方阵，当前形状为：{dist_matrix.shape}"
        )

    if dist_matrix.shape[0] != len(matrix_ids):
        raise ValueError(
            "距离矩阵行数与列 ID 数不一致，请检查距离矩阵文件。"
        )

    id_to_matrix_idx = {
        int(cid): idx for idx, cid in enumerate(matrix_ids)
    }

    return dist_matrix, id_to_matrix_idx, matrix_ids


def check_distance_id_coverage(id_to_matrix_idx, all_node_ids):
    """
    检查所有节点 ID 是否都能在距离矩阵中找到。
    """
    missing = [int(cid) for cid in all_node_ids if int(cid) not in id_to_matrix_idx]

    if missing:
        raise ValueError(
            f"以下节点 ID 在距离矩阵中找不到：{missing}"
        )


# =========================================================
# 构建问题数据
# =========================================================
def build_problem_data(base_path=DATA_DIR):
    """
    构建统一问题数据 problem_data。
    """
    orders_df, dist_df, coords_df, tw_df = load_all_data(base_path)

    demand_df = build_demand_table(orders_df)
    customer_base_df = build_customer_base_table(coords_df)
    tw_clean_df = build_time_window_table(tw_df)
    depot_info = build_depot_info(coords_df)

    all_customers_df = customer_base_df.merge(
        tw_clean_df,
        on="客户编号",
        how="left"
    )

    all_customers_df = all_customers_df.merge(
        demand_df,
        on="客户编号",
        how="left"
    )

    all_customers_df["总重量"] = all_customers_df["总重量"].fillna(0.0).astype(float)
    all_customers_df["总体积"] = all_customers_df["总体积"].fillna(0.0).astype(float)

    # 时间窗缺失检查
    missing_tw_df = all_customers_df[
        all_customers_df["开始时间_小时"].isna()
        | all_customers_df["结束时间_小时"].isna()
    ]

    if not missing_tw_df.empty:
        raise ValueError(
            f"以下客户缺少时间窗：{missing_tw_df['客户编号'].tolist()}"
        )

    # 绿色区：以市中心 (0,0) 为圆心，半径 GREEN_RADIUS km
    all_customers_df["距市中心距离"] = (
        all_customers_df["x"] ** 2 + all_customers_df["y"] ** 2
    ) ** 0.5

    all_customers_df["是否绿色区"] = (
        all_customers_df["距市中心距离"] <= GREEN_RADIUS + 1e-9
    )

    all_customers_df = (
        all_customers_df
        .sort_values("客户编号")
        .reset_index(drop=True)
    )

    active_customers_df = all_customers_df[
        (all_customers_df["总重量"] > 0)
        | (all_customers_df["总体积"] > 0)
    ].copy().reset_index(drop=True)

    green_customers_df = all_customers_df[
        all_customers_df["是否绿色区"]
    ].copy().reset_index(drop=True)

    active_green_customers_df = active_customers_df[
        active_customers_df["是否绿色区"]
    ].copy().reset_index(drop=True)

    dist_matrix, id_to_matrix_idx, matrix_id_list = build_distance_matrix(dist_df)

    all_node_ids = [0] + all_customers_df["客户编号"].astype(int).tolist()
    check_distance_id_coverage(id_to_matrix_idx, all_node_ids)

    customer_id_list = all_customers_df["客户编号"].astype(int).tolist()
    active_customer_id_list = active_customers_df["客户编号"].astype(int).tolist()
    green_customer_id_list = green_customers_df["客户编号"].astype(int).tolist()
    active_green_customer_id_list = active_green_customers_df["客户编号"].astype(int).tolist()

    problem_data = {
        "orders_df": orders_df,
        "dist_df": dist_df,
        "coords_df": coords_df,
        "tw_df": tw_df,

        "demand_df": demand_df,
        "all_customers_df": all_customers_df,
        "active_customers_df": active_customers_df,
        "green_customers_df": green_customers_df,
        "active_green_customers_df": active_green_customers_df,

        "dist_matrix": dist_matrix,
        "depot_info": depot_info,

        "customer_id_list": customer_id_list,
        "active_customer_id_list": active_customer_id_list,
        "green_customer_id_list": green_customer_id_list,
        "active_green_customer_id_list": active_green_customer_id_list,

        "id_to_matrix_idx": id_to_matrix_idx,
        "matrix_id_list": matrix_id_list,

        "green_radius": GREEN_RADIUS
    }

    return problem_data


# =========================================================
# 任务拆分
# =========================================================
def build_task_table(problem_data, max_weight=1500.0, max_volume=8.5):
    """
    将有效客户拆分为可由单车承载的虚拟任务。

    默认使用 1500kg / 8.5m³ 作为拆分上限：
    这样任务粒度较细，更容易被不同车型插入路径。
    如果后续想减少任务数，可以在 main_p1.py 中显式传入：
        build_task_table(problem_data, max_weight=3000.0, max_volume=13.5)
    """
    if max_weight <= 0 or max_volume <= 0:
        raise ValueError("max_weight 和 max_volume 必须为正数。")

    active_customers_df = problem_data["active_customers_df"]

    task_rows = []

    for _, row in active_customers_df.iterrows():
        customer_id = int(row["客户编号"])
        total_weight = float(row["总重量"])
        total_volume = float(row["总体积"])

        split_by_weight = math.ceil(total_weight / max_weight) if total_weight > 0 else 1
        split_by_volume = math.ceil(total_volume / max_volume) if total_volume > 0 else 1

        split_count = max(split_by_weight, split_by_volume, 1)

        base_weight = total_weight / split_count
        base_volume = total_volume / split_count

        allocated_weight = 0.0
        allocated_volume = 0.0

        for k in range(split_count):
            if k < split_count - 1:
                task_weight = base_weight
                task_volume = base_volume
            else:
                # 最后一个任务吸收浮点误差，保证拆分总和严格等于客户总需求
                task_weight = total_weight - allocated_weight
                task_volume = total_volume - allocated_volume

            allocated_weight += task_weight
            allocated_volume += task_volume

            # 防止 -0.0000000001 这类浮点误差
            task_weight = max(0.0, float(task_weight))
            task_volume = max(0.0, float(task_volume))

            task_rows.append({
                "任务编号": f"{customer_id}_{k + 1}",
                "原客户编号": customer_id,
                "x": float(row["x"]),
                "y": float(row["y"]),
                "距市中心距离": float(row["距市中心距离"]),
                "开始时间_小时": float(row["开始时间_小时"]),
                "结束时间_小时": float(row["结束时间_小时"]),
                "任务重量": task_weight,
                "任务体积": task_volume,
                "是否绿色区": bool(row["是否绿色区"]),
                "拆分数": int(split_count)
            })

    tasks_df = pd.DataFrame(task_rows)

    if tasks_df.empty:
        raise ValueError("任务表为空，请检查订单需求数据。")

    if (tasks_df["任务重量"] > max_weight + 1e-6).any():
        bad = tasks_df[tasks_df["任务重量"] > max_weight + 1e-6]
        raise ValueError(f"存在超过拆分重量上限的任务：\n{bad}")

    if (tasks_df["任务体积"] > max_volume + 1e-6).any():
        bad = tasks_df[tasks_df["任务体积"] > max_volume + 1e-6]
        raise ValueError(f"存在超过拆分体积上限的任务：\n{bad}")

    return tasks_df


# =========================================================
# 数据摘要输出
# =========================================================
def print_data_summary(problem_data, tasks_df=None):
    """
    输出数据处理摘要，便于检查和写论文。
    """
    all_customers_df = problem_data["all_customers_df"]
    active_customers_df = problem_data["active_customers_df"]
    green_customers_df = problem_data["green_customers_df"]
    active_green_customers_df = problem_data["active_green_customers_df"]

    print("========== 数据处理摘要 ==========")
    print("全部客户数：", len(all_customers_df))
    print("有效客户数：", len(active_customers_df))
    print("绿色区客户数：", len(green_customers_df))
    print("有效绿色区客户数：", len(active_green_customers_df))
    print("绿色区半径：", problem_data["green_radius"], "km")
    print("配送中心信息：", problem_data["depot_info"])
    print("距离矩阵形状：", problem_data["dist_matrix"].shape)

    if tasks_df is not None:
        print("任务数：", len(tasks_df))
        print("最大任务重量：", tasks_df["任务重量"].max())
        print("最大任务体积：", tasks_df["任务体积"].max())
        print("绿色区任务数：", int(tasks_df["是否绿色区"].sum()))
        print("被拆分客户数：", int((tasks_df.groupby("原客户编号").size() > 1).sum()))

    print("==================================")


# =========================================================
# 单独运行测试
# =========================================================
if __name__ == "__main__":
    problem_data = build_problem_data()
    tasks_df = build_task_table(problem_data)

    print_data_summary(problem_data, tasks_df)

    print("\n全部客户前5行：")
    print(problem_data["all_customers_df"].head())

    print("\n有效客户前5行：")
    print(problem_data["active_customers_df"].head())

    print("\n任务表前5行：")
    print(tasks_df.head())