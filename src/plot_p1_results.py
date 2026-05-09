# === Project path bootstrap ===
from pathlib import Path
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
# ==============================

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator, FuncFormatter
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401


# =========================
# 全局参数
# =========================
FIG_SIZE = (10.5, 6.8)
FIG_SIZE_PIE = (10.8, 7.2)
FIG_SIZE_3D = (14.0, 8.8)
DPI = 600
OUTPUT_DIR = "figures/problem1"

# 你之前已经调到满意的位置，这里直接保留
Z_LABEL_X = 0.60

plt.rcParams["font.sans-serif"] = [
    "Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Arial Unicode MS", "DejaVu Sans"
]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.facecolor"] = "white"
plt.rcParams["axes.facecolor"] = "white"
plt.rcParams["savefig.facecolor"] = "white"

COLORS = {
    "blue": "#2E6FBB",
    "orange": "#F28E2B",
    "green": "#2B9348",
    "red": "#D1495B",
    "purple": "#7B6FD0",
    "cyan": "#2AA7A1",
    "gray": "#6B7280",
    "dark": "#1F2D3D",
    "light_gray": "#E9EDF3",
}

VEHICLE_ORDER = [
    "ev_3000",
    "ev_1250",
    "fuel_3000",
    "fuel_1500",
    "fuel_1250",
]


# =========================
# 基础工具
# =========================
def ensure_output_dir():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)


def save_fig_2d(fig, filename):
    ensure_output_dir()
    path = os.path.join(OUTPUT_DIR, filename)
    fig.tight_layout(rect=[0.02, 0.04, 0.98, 0.90])
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"图片已生成：{path}")


def save_fig_3d(fig, filename):
    ensure_output_dir()
    path = os.path.join(OUTPUT_DIR, filename)

    fig.subplots_adjust(
        left=0.03,
        right=0.97,
        bottom=0.08,
        top=0.87
    )

    fig.savefig(
        path,
        dpi=DPI,
        bbox_inches=None,
        pad_inches=0.30,
        facecolor="white"
    )
    plt.close(fig)
    print(f"图片已生成：{path}")


def add_figure_titles(fig, title, subtitle=None):
    fig.suptitle(
        title,
        fontsize=18,
        fontweight="bold",
        color=COLORS["dark"],
        y=0.975
    )
    if subtitle:
        fig.text(
            0.5,
            0.925,
            subtitle,
            ha="center",
            va="center",
            fontsize=10.5,
            color=COLORS["gray"]
        )


def beautify_2d_axes(ax):
    ax.grid(True, which="major", linestyle="--", linewidth=0.8, alpha=0.6, zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#333333")
    ax.spines["bottom"].set_color("#333333")
    ax.tick_params(axis="both", labelsize=11)


def beautify_3d_axes(ax, zmax):
    try:
        ax.set_proj_type("ortho")
    except Exception:
        pass

    try:
        ax.xaxis.pane.set_facecolor((0.96, 0.97, 0.99, 1.0))
        ax.yaxis.pane.set_facecolor((0.98, 0.98, 0.98, 1.0))
        ax.zaxis.pane.set_facecolor((1.00, 1.00, 1.00, 1.0))

        ax.xaxis.pane.set_edgecolor("#D0D7DE")
        ax.yaxis.pane.set_edgecolor("#D0D7DE")
        ax.zaxis.pane.set_edgecolor("#D0D7DE")
    except Exception:
        pass

    for axis in [ax.xaxis, ax.yaxis, ax.zaxis]:
        try:
            axis._axinfo["grid"]["color"] = (0.82, 0.86, 0.91, 1.0)
            axis._axinfo["grid"]["linestyle"] = "--"
            axis._axinfo["grid"]["linewidth"] = 0.7
        except Exception:
            pass

    ax.tick_params(axis="x", labelsize=12, pad=4)
    ax.tick_params(axis="z", labelsize=12, pad=6)

    if zmax >= 10000:
        ax.zaxis.set_major_locator(MaxNLocator(nbins=6))
        ax.zaxis.set_major_formatter(
            FuncFormatter(lambda x, pos: "0" if abs(x) < 1e-9 else f"{x / 10000:.1f}万")
        )
    elif zmax <= 150:
        ax.zaxis.set_major_locator(MaxNLocator(nbins=6, integer=True))
    else:
        ax.zaxis.set_major_locator(MaxNLocator(nbins=6))


def safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def parse_node_count(node_sequence):
    try:
        parts = [x.strip() for x in str(node_sequence).split("->")]
        tasks = [x for x in parts if x != "0"]
        return len(tasks)
    except Exception:
        return 0


def load_results(route_path="results/problem1/problem1_routes.csv", summary_path="results/problem1/problem1_summary.csv"):
    if not os.path.exists(route_path):
        raise FileNotFoundError(f"找不到文件：{route_path}")
    if not os.path.exists(summary_path):
        raise FileNotFoundError(f"找不到文件：{summary_path}")

    routes_df = pd.read_csv(route_path, encoding="utf-8-sig")
    summary_df = pd.read_csv(summary_path, encoding="utf-8-sig")
    return routes_df, summary_df


def get_adaptive_bar_width(n):
    if n <= 1:
        return 0.35
    if n <= 3:
        return 0.42
    if n <= 6:
        return 0.50
    return 0.60


def get_adaptive_bins(data):
    data = np.asarray(data, dtype=float)
    unique_count = len(np.unique(np.round(data, 6)))

    if unique_count <= 1:
        return 1
    if unique_count <= 6:
        return unique_count
    return min(16, max(8, int(np.sqrt(len(data))) + 2))


def normalize_color_list(color_list, n):
    base_colors = [
        COLORS["blue"],
        COLORS["orange"],
        COLORS["green"],
        COLORS["purple"],
        COLORS["red"],
        COLORS["cyan"],
    ]

    if color_list is None:
        color_list = base_colors

    color_list = list(color_list)

    if len(color_list) == n:
        return color_list

    if len(color_list) > n:
        return color_list[:n]

    while len(color_list) < n:
        color_list.append(base_colors[len(color_list) % len(base_colors)])

    return color_list


# =========================
# 3D 柱状图通用函数
# =========================
def plot_3d_bar_chart(
    labels,
    values,
    title,
    subtitle,
    xlabel,
    zlabel,
    filename,
    color_list=None,
    show_percent=False
):
    labels = list(labels)
    values = np.array(values, dtype=float)

    n = len(labels)
    color_list = normalize_color_list(color_list, n)

    fig = plt.figure(figsize=FIG_SIZE_3D)

    # 车辆数量图专门放大主绘图区
    ax = fig.add_axes([0.05, 0.14, 0.82, 0.70], projection="3d")

    add_figure_titles(fig, title, subtitle)

    x = np.arange(n, dtype=float)
    y = np.zeros(n, dtype=float)
    z = np.zeros(n, dtype=float)

    # 柱子加粗一点，更显眼
    if n <= 1:
        dx_val = 0.42
        dy_val = 0.46
    elif n <= 3:
        dx_val = 0.50
        dy_val = 0.50
    else:
        dx_val = 0.56
        dy_val = 0.54

    dx = np.full(n, dx_val)
    dy = np.full(n, dy_val)
    dz = values.copy()

    tiny_height = max(np.max(dz) * 0.012, 0.08) if np.max(dz) > 0 else 0.08
    display_dz = dz.copy()
    display_dz[display_dz == 0] = tiny_height

    ax.bar3d(
        x - dx / 2,
        y - dy / 2,
        z,
        dx,
        dy,
        display_dz,
        color=color_list,
        edgecolor="white",
        linewidth=0.9,
        shade=True,
        alpha=0.97
    )

    zmax = max(np.max(values), 1.0)

    if n == 1:
        ax.set_xlim(-1.2, 1.2)
    else:
        ax.set_xlim(-0.8, n - 0.2)

    ax.set_ylim(-0.9, 0.9)
    ax.set_zlim(0, zmax * 1.32)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=12)

    ax.set_yticks([])
    ax.set_xlabel(xlabel, labelpad=16, fontsize=14)
    ax.set_zlabel("")

    fig.text(
        Z_LABEL_X,
        0.50,
        zlabel,
        ha="center",
        va="center",
        rotation=90,
        fontsize=14,
        color=COLORS["dark"]
    )

    ax.view_init(elev=18, azim=-50)

    try:
        ax.set_box_aspect((max(4.8, n * 1.15), 1.4, 3.0))
    except Exception:
        pass

    beautify_3d_axes(ax, zmax)

    total = float(np.sum(values)) if np.sum(values) > 0 else 1.0

    for i, val in enumerate(values):
        if show_percent:
            txt = f"{val:.1f}\n({val / total * 100:.1f}%)"
        else:
            txt = f"{int(val)}" if abs(val - int(val)) < 1e-8 else f"{val:.1f}"

        label_z = max(val, tiny_height) + zmax * 0.035

        ax.text(
            x[i],
            0,
            label_z,
            txt,
            ha="center",
            va="bottom",
            fontsize=11.5,
            color=COLORS["dark"]
        )

    save_fig_3d(fig, filename)


# =========================
# 图1：成本构成图（饼图）
# =========================
def plot_cost_structure(summary_df):
    row = summary_df.iloc[0]

    cost_items = {
        "固定成本": safe_float(row.get("固定成本", 0.0)),
        "能耗成本": safe_float(row.get("能耗成本", 0.0)),
        "碳排成本": safe_float(row.get("碳排成本", 0.0)),
        "等待成本": safe_float(row.get("等待成本", 0.0)),
        "迟到成本": safe_float(row.get("迟到成本", 0.0)),
    }

    labels = list(cost_items.keys())
    values = np.array(list(cost_items.values()), dtype=float)
    total_cost = safe_float(row.get("总成本", np.sum(values)))

    fig, ax = plt.subplots(figsize=FIG_SIZE_PIE)

    add_figure_titles(
        fig,
        "问题一成本构成图",
        f"总成本 = {total_cost:.2f}，展示各类成本在目标函数中的占比"
    )

    pie_colors = [
        COLORS["blue"],
        COLORS["orange"],
        COLORS["green"],
        COLORS["purple"],
        COLORS["red"],
    ]

    def autopct_fmt(pct):
        if pct < 0.5:
            return ""
        return f"{pct:.1f}%"

    wedges, texts, autotexts = ax.pie(
        values,
        labels=labels,
        colors=pie_colors,
        startangle=90,
        counterclock=False,
        autopct=autopct_fmt,
        pctdistance=0.72,
        labeldistance=1.04,
        wedgeprops=dict(edgecolor="white", linewidth=1.2),
        textprops=dict(fontsize=11, color=COLORS["dark"])
    )

    for t in autotexts:
        t.set_fontsize(11)
        t.set_color("white")
        t.set_weight("bold")

    # 中心补充总成本信息
    ax.text(
        0, 0,
        f"总成本\n{total_cost:.2f}",
        ha="center",
        va="center",
        fontsize=13,
        fontweight="bold",
        color=COLORS["dark"],
        bbox=dict(
            boxstyle="round,pad=0.35",
            facecolor="white",
            edgecolor="#D9DEE7",
            alpha=0.95
        )
    )

    # 右侧图例
    legend_labels = [
        f"{name}: {value:.2f} ({value / total_cost * 100:.2f}%)" if total_cost > 0 else f"{name}: {value:.2f}"
        for name, value in zip(labels, values)
    ]

    ax.legend(
        wedges,
        legend_labels,
        title="成本明细",
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
        fontsize=10.5,
        title_fontsize=11.5,
        frameon=True
    )

    ax.set_aspect("equal")
    save_fig_2d(fig, "p1_cost_structure_pie.png")


# =========================
# 图2：车型使用数量图（放大版 3D）
# =========================
def plot_vehicle_type_count(routes_df):
    raw_counts = routes_df["车型"].value_counts()

    vehicle_counts = pd.Series(
        {vehicle: int(raw_counts.get(vehicle, 0)) for vehicle in VEHICLE_ORDER}
    )

    labels = vehicle_counts.index.tolist()
    values = vehicle_counts.values.tolist()

    subtitle = "统计优化后方案中不同车型的使用数量；图像已放大以增强展示效果"

    plot_3d_bar_chart(
        labels=labels,
        values=values,
        title="问题一车型使用数量图",
        subtitle=subtitle,
        xlabel="车型",
        zlabel="车辆数",
        filename="p1_vehicle_type_count_3d.png",
        color_list=[
            COLORS["blue"],
            COLORS["cyan"],
            COLORS["orange"],
            COLORS["green"],
            COLORS["purple"],
        ],
        show_percent=False
    )


# =========================
# 图3：路径成本分布图（2D）
# =========================
def plot_route_cost_hist(routes_df):
    costs = routes_df["总成本"].astype(float).values

    fig, ax = plt.subplots(figsize=FIG_SIZE)

    add_figure_titles(
        fig,
        "单车路径成本分布图",
        "反映不同车辆路径之间的成本差异"
    )

    unique_count = len(np.unique(np.round(costs, 6)))

    if unique_count <= 1:
        ax.bar(
            [0],
            [len(costs)],
            width=0.35,
            color=COLORS["orange"],
            edgecolor="white",
            zorder=3
        )
        ax.set_xticks([0])
        ax.set_xticklabels([f"{costs[0]:.2f}"])
        ax.set_xlabel("单车路径成本")
        ax.set_ylabel("频数")
        ax.text(
            0,
            len(costs) + 0.2,
            str(len(costs)),
            ha="center",
            va="bottom",
            fontsize=11
        )
    else:
        bins = get_adaptive_bins(costs)

        ax.hist(
            costs,
            bins=bins,
            color=COLORS["orange"],
            edgecolor="white",
            linewidth=1.0,
            alpha=0.90,
            zorder=3
        )

        mean_val = np.mean(costs)
        median_val = np.median(costs)

        ax.axvline(
            mean_val,
            color=COLORS["red"],
            linestyle="--",
            linewidth=2.0,
            label=f"均值 = {mean_val:.2f}",
            zorder=4
        )

        ax.axvline(
            median_val,
            color=COLORS["green"],
            linestyle="-.",
            linewidth=2.0,
            label=f"中位数 = {median_val:.2f}",
            zorder=4
        )

        legend = ax.legend(frameon=True)
        legend.get_frame().set_facecolor("white")
        legend.get_frame().set_edgecolor("#D0D7DE")

        ax.set_xlabel("单车路径成本")
        ax.set_ylabel("频数")

    text_str = (
        f"路径数：{len(costs)}\n"
        f"最大成本：{np.max(costs):.2f}\n"
        f"最小成本：{np.min(costs):.2f}\n"
        f"标准差：{np.std(costs):.2f}"
    )

    ax.text(
        0.97,
        0.93,
        text_str,
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=10.5,
        bbox=dict(
            boxstyle="round,pad=0.35",
            facecolor="white",
            edgecolor="#D9DEE7",
            alpha=0.96
        )
    )

    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    beautify_2d_axes(ax)
    save_fig_2d(fig, "p1_route_cost_hist.png")


# =========================
# 图4：路径距离分布图（2D）
# =========================
def plot_route_distance_hist(routes_df):
    distances = routes_df["总距离"].astype(float).values

    fig, ax = plt.subplots(figsize=FIG_SIZE)

    add_figure_titles(
        fig,
        "单车路径距离分布图",
        "反映优化方案中各车辆配送路径长度的离散程度"
    )

    unique_count = len(np.unique(np.round(distances, 6)))

    if unique_count <= 1:
        ax.bar(
            [0],
            [len(distances)],
            width=0.35,
            color=COLORS["green"],
            edgecolor="white",
            zorder=3
        )
        ax.set_xticks([0])
        ax.set_xticklabels([f"{distances[0]:.2f}"])
        ax.set_xlabel("单车路径距离 / km")
        ax.set_ylabel("频数")
        ax.text(
            0,
            len(distances) + 0.2,
            str(len(distances)),
            ha="center",
            va="bottom",
            fontsize=11
        )
    else:
        bins = get_adaptive_bins(distances)

        ax.hist(
            distances,
            bins=bins,
            color=COLORS["green"],
            edgecolor="white",
            linewidth=1.0,
            alpha=0.90,
            zorder=3
        )

        mean_val = np.mean(distances)
        median_val = np.median(distances)

        ax.axvline(
            mean_val,
            color=COLORS["red"],
            linestyle="--",
            linewidth=2.0,
            label=f"均值 = {mean_val:.2f}",
            zorder=4
        )

        ax.axvline(
            median_val,
            color=COLORS["blue"],
            linestyle="-.",
            linewidth=2.0,
            label=f"中位数 = {median_val:.2f}",
            zorder=4
        )

        legend = ax.legend(frameon=True)
        legend.get_frame().set_facecolor("white")
        legend.get_frame().set_edgecolor("#D0D7DE")

        ax.set_xlabel("单车路径距离 / km")
        ax.set_ylabel("频数")

    text_str = (
        f"路径数：{len(distances)}\n"
        f"最大距离：{np.max(distances):.2f}\n"
        f"最小距离：{np.min(distances):.2f}\n"
        f"标准差：{np.std(distances):.2f}"
    )

    ax.text(
        0.97,
        0.93,
        text_str,
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=10.5,
        bbox=dict(
            boxstyle="round,pad=0.35",
            facecolor="white",
            edgecolor="#D9DEE7",
            alpha=0.96
        )
    )

    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    beautify_2d_axes(ax)
    save_fig_2d(fig, "p1_route_distance_hist.png")


# =========================
# 图5：单车任务数分布图（2D）
# =========================
def plot_route_task_count_hist(routes_df):
    task_counts = routes_df["节点序列"].apply(parse_node_count)
    count_series = task_counts.value_counts().sort_index()

    x = count_series.index.tolist()
    y = count_series.values.tolist()

    fig, ax = plt.subplots(figsize=FIG_SIZE)

    add_figure_titles(
        fig,
        "单车服务任务数分布图",
        "统计每辆车承担的任务数量"
    )

    bar_width = get_adaptive_bar_width(len(x))

    bars = ax.bar(
        x,
        y,
        width=bar_width,
        color=COLORS["purple"],
        edgecolor="white",
        linewidth=1.0,
        zorder=3
    )

    for bar, val in zip(bars, y):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(y) * 0.015,
            str(val),
            ha="center",
            va="bottom",
            fontsize=10.5
        )

    mean_val = task_counts.mean()

    ax.axvline(
        mean_val,
        color=COLORS["red"],
        linestyle="--",
        linewidth=2.0,
        label=f"平均任务数 = {mean_val:.2f}",
        zorder=4
    )

    legend = ax.legend(frameon=True)
    legend.get_frame().set_facecolor("white")
    legend.get_frame().set_edgecolor("#D0D7DE")

    text_str = (
        f"车辆数：{len(task_counts)}\n"
        f"最大任务数：{task_counts.max()}\n"
        f"最小任务数：{task_counts.min()}\n"
        f"平均任务数：{task_counts.mean():.2f}"
    )

    ax.text(
        0.97,
        0.93,
        text_str,
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=10.5,
        bbox=dict(
            boxstyle="round,pad=0.35",
            facecolor="white",
            edgecolor="#D9DEE7",
            alpha=0.96
        )
    )

    ax.set_xlabel("单车服务任务数")
    ax.set_ylabel("频数")
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    beautify_2d_axes(ax)
    save_fig_2d(fig, "p1_route_task_count_hist.png")


# =========================
# 文字总结
# =========================
def generate_analysis_text(routes_df, summary_df):
    row = summary_df.iloc[0]

    vehicle_num = int(row.get("车辆数", len(routes_df)))
    total_cost = safe_float(row.get("总成本", 0.0))
    fixed_cost = safe_float(row.get("固定成本", 0.0))
    energy_cost = safe_float(row.get("能耗成本", 0.0))
    carbon_cost = safe_float(row.get("碳排成本", 0.0))
    wait_cost = safe_float(row.get("等待成本", 0.0))
    late_cost = safe_float(row.get("迟到成本", 0.0))
    total_distance = safe_float(row.get("总距离", 0.0))
    feasible = row.get("是否可行", "")
    coverage_ok = row.get("覆盖正确", "")

    route_costs = routes_df["总成本"].astype(float)
    route_distances = routes_df["总距离"].astype(float)
    task_counts = routes_df["节点序列"].apply(parse_node_count)

    raw_vehicle_counts = routes_df["车型"].value_counts()
    vehicle_counts = pd.Series(
        {vehicle: int(raw_vehicle_counts.get(vehicle, 0)) for vehicle in VEHICLE_ORDER}
    )

    fixed_ratio = fixed_cost / total_cost * 100 if total_cost > 0 else 0
    energy_ratio = energy_cost / total_cost * 100 if total_cost > 0 else 0
    carbon_ratio = carbon_cost / total_cost * 100 if total_cost > 0 else 0
    wait_ratio = wait_cost / total_cost * 100 if total_cost > 0 else 0
    late_ratio = late_cost / total_cost * 100 if total_cost > 0 else 0

    lines = []
    lines.append("问题一结果分析文字草稿")
    lines.append("=" * 40)
    lines.append("")
    lines.append(
        f"在无绿色配送区限行政策约束的情形下，本文采用初始解生成算法与 ALNS 优化算法对车辆调度方案进行求解。"
        f"最终得到可行解状态为 {feasible}，任务覆盖检查结果为 {coverage_ok}，"
        f"说明所有配送任务均被完整服务且不存在重复服务。"
    )
    lines.append("")
    lines.append(
        f"优化后的调度方案共使用车辆 {vehicle_num} 辆，总配送距离为 {total_distance:.2f} km，总成本为 {total_cost:.2f}。"
        f"其中，固定成本为 {fixed_cost:.2f}，占总成本的 {fixed_ratio:.2f}%；"
        f"能耗成本为 {energy_cost:.2f}，占 {energy_ratio:.2f}%；"
        f"碳排放成本为 {carbon_cost:.2f}，占 {carbon_ratio:.2f}%；"
        f"等待成本为 {wait_cost:.2f}，占 {wait_ratio:.2f}%；"
        f"迟到成本为 {late_cost:.2f}，占 {late_ratio:.2f}%。"
    )
    lines.append("")
    lines.append(
        f"从单车路径表现来看，单车路径成本均值为 {route_costs.mean():.2f}，中位数为 {route_costs.median():.2f}，"
        f"最大值为 {route_costs.max():.2f}，最小值为 {route_costs.min():.2f}。"
        f"单车路径距离均值为 {route_distances.mean():.2f} km，中位数为 {route_distances.median():.2f} km。"
    )
    lines.append("")
    lines.append(
        f"从任务分配情况看，单车平均服务任务数为 {task_counts.mean():.2f}，"
        f"最大服务任务数为 {task_counts.max()}，最小服务任务数为 {task_counts.min()}。"
    )
    lines.append("")
    lines.append("车型使用数量统计如下：")
    for vehicle_type, count in vehicle_counts.items():
        lines.append(f"  - {vehicle_type}: {count} 辆")

    lines.append("")
    lines.append(
        "上述结果表明，所建立的车辆路径优化模型能够在满足容量约束、时间窗约束和任务唯一服务约束的基础上，"
        "有效降低总配送成本，并形成可用于后续绿色配送政策分析和动态扰动响应的基础调度方案。"
    )

    ensure_output_dir()
    path = os.path.join(OUTPUT_DIR, "p1_result_analysis.txt")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"文字分析已生成：{path}")


# =========================
# 主函数
# =========================
def main():
    print("========== 问题一结果分析图生成开始 ==========")

    routes_df, summary_df = load_results(
        route_path="results/problem1/problem1_routes.csv",
        summary_path="results/problem1/problem1_summary.csv"
    )

    print("路径结果行数：", len(routes_df))
    print("汇总结果：")
    print(summary_df)

    # 成本构成图：改为饼图
    plot_cost_structure(summary_df)

    # 车辆使用数量图：放大版 3D
    plot_vehicle_type_count(routes_df)

    # 其余统计图保持
    plot_route_cost_hist(routes_df)
    plot_route_distance_hist(routes_df)
    plot_route_task_count_hist(routes_df)

    generate_analysis_text(routes_df, summary_df)

    print("========== 问题一结果分析图生成结束 ==========")


if __name__ == "__main__":
    main()