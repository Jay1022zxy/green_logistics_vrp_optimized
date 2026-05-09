# === Project path bootstrap ===
from pathlib import Path
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
# ==============================

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import font_manager


# =========================================================
# 文件路径
# =========================================================
P1_SUMMARY_PATH = "results/problem1/problem1_summary.csv"
P2_SUMMARY_PATH = "results/problem2/problem2_summary.csv"

OUTPUT_DIR = "figures/problem2"
CARBON_COST_PER_UNIT = 0.65

DPI = 600


# =========================================================
# 配色
# =========================================================
COLORS = {
    "p1": "#3B6EA8",
    "p2": "#E68632",
    "blue": "#3B6EA8",
    "orange": "#E68632",
    "green": "#4F9D69",
    "red": "#C44E52",
    "purple": "#8E6BBE",
    "teal": "#5DA5A4",
    "gold": "#D9A441",
    "gray": "#8A8A8A",
    "light_gray": "#F2F4F7",
    "grid": "#D9DEE7",
    "text": "#222222",
    "subtext": "#666666",
}


COST_COLOR_MAP = {
    "固定成本": COLORS["blue"],
    "能耗成本": COLORS["orange"],
    "碳排成本": COLORS["green"],
    "等待成本": COLORS["purple"],
    "迟到成本": COLORS["red"],
}


# =========================================================
# 基础工具
# =========================================================
def setup_chinese_font():
    candidates = ["Microsoft YaHei", "SimHei", "SimSun", "Arial Unicode MS"]
    available_fonts = {f.name for f in font_manager.fontManager.ttflist}

    for font in candidates:
        if font in available_fonts:
            plt.rcParams["font.sans-serif"] = [font]
            break

    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.facecolor"] = "white"
    plt.rcParams["axes.facecolor"] = "white"
    plt.rcParams["savefig.facecolor"] = "white"


def ensure_clean_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 删除旧图，避免打开到之前的图
    for name in os.listdir(OUTPUT_DIR):
        if name.lower().endswith((".png", ".jpg", ".jpeg", ".pdf")):
            try:
                os.remove(os.path.join(OUTPUT_DIR, name))
            except Exception:
                pass


def save_fig(fig, filename):
    path = os.path.join(OUTPUT_DIR, filename)
    fig.savefig(
        path,
        dpi=DPI,
        bbox_inches="tight",
        pad_inches=0.22,
        facecolor="white"
    )
    plt.close(fig)
    print(f"图片已生成：{path}")


def read_summary(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"找不到文件：{path}")

    df = pd.read_csv(path, encoding="utf-8-sig")

    if df.empty:
        raise ValueError(f"文件为空：{path}")

    return df.iloc[0].to_dict()


def safe_float(value, default=0.0):
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def get_metric(summary, key):
    return safe_float(summary.get(key, 0.0))


def add_header(fig, title, subtitle=None):
    fig.text(
        0.5, 0.965,
        title,
        ha="center",
        va="top",
        fontsize=18,
        fontweight="bold",
        color=COLORS["text"]
    )

    if subtitle:
        fig.text(
            0.5, 0.915,
            subtitle,
            ha="center",
            va="top",
            fontsize=10.5,
            color=COLORS["subtext"]
        )


def style_axis(ax, grid_axis="y"):
    ax.set_facecolor("white")
    ax.grid(
        axis=grid_axis,
        linestyle="--",
        linewidth=0.8,
        alpha=0.35,
        color=COLORS["grid"]
    )
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_alpha(0.35)
    ax.spines["bottom"].set_alpha(0.35)
    ax.tick_params(labelsize=10.5, colors=COLORS["text"])


def fmt_value(v, unit=""):
    if abs(v) >= 10000:
        return f"{v:,.0f}{unit}"
    if abs(v) >= 1000:
        return f"{v:,.1f}{unit}"
    return f"{v:.2f}{unit}"


def delta_text(diff, ratio):
    direction = "增加" if diff >= 0 else "减少"
    return f"{direction} {abs(diff):.2f}，变化率 {ratio:.2f}%"


# =========================================================
# 图1：总成本变化瀑布图
# =========================================================
def plot_total_cost_waterfall(p1, p2):
    """
    总成本变化分解图。

    说明：
    1. 不使用局部放大窗；
    2. 不使用箭头、指引线、外框；
    3. 所有柱子都按真实数值绘制；
    4. 小变化项文字居中显示在对应柱子上方，字体与其他增量标注一致。
    """
    components = ["固定成本", "能耗成本", "碳排成本", "等待成本", "迟到成本"]

    p1_total = get_metric(p1, "总成本")
    p2_total = get_metric(p2, "总成本")

    deltas = [get_metric(p2, c) - get_metric(p1, c) for c in components]

    labels = ["问题一总成本"] + components + ["问题二总成本"]
    x = np.arange(len(labels))

    fig, ax = plt.subplots(figsize=(12.5, 7.0))
    fig.patch.set_facecolor("white")

    bar_width = 0.58
    max_total = max(p1_total, p2_total)

    SMALL_DELTA_THRESHOLD = 180.0

    ax.bar(
        x[0],
        p1_total,
        width=bar_width,
        color=COLORS["p1"],
        edgecolor="white",
        linewidth=1.2,
        zorder=3
    )

    cumulative = p1_total

    for i, (comp, delta) in enumerate(zip(components, deltas), start=1):
        bottom = cumulative if delta >= 0 else cumulative + delta
        color = COST_COLOR_MAP[comp] if delta >= 0 else COLORS["teal"]
        is_small = 0 < abs(delta) < SMALL_DELTA_THRESHOLD

        ax.bar(
            x[i],
            abs(delta),
            bottom=bottom,
            width=bar_width,
            color=color,
            edgecolor="#666666" if is_small else "white",
            linewidth=0.9 if is_small else 1.2,
            zorder=3
        )

        if is_small:
            y_top = bottom + abs(delta)

            ax.hlines(
                y=y_top,
                xmin=x[i] - bar_width * 0.36,
                xmax=x[i] + bar_width * 0.36,
                colors=color,
                linewidth=2.0,
                zorder=5
            )

            ax.text(
                x[i],
                y_top + max_total * 0.008,
                f"{delta:+.0f}",
                ha="center",
                va="bottom",
                fontsize=10.5,
                color=COLORS["text"]
            )
        else:
            ax.text(
                x[i],
                bottom + abs(delta) + max_total * 0.008,
                f"{delta:+.0f}",
                ha="center",
                va="bottom",
                fontsize=10.5,
                color=COLORS["text"]
            )

        ax.plot(
            [x[i - 1] + bar_width / 2, x[i] - bar_width / 2],
            [cumulative, cumulative],
            color="#BBBBBB",
            linewidth=1.0,
            linestyle="--",
            zorder=2
        )

        cumulative += delta

    ax.bar(
        x[-1],
        p2_total,
        width=bar_width,
        color=COLORS["p2"],
        edgecolor="white",
        linewidth=1.2,
        zorder=3
    )

    ax.plot(
        [x[-2] + bar_width / 2, x[-1] - bar_width / 2],
        [cumulative, cumulative],
        color="#BBBBBB",
        linewidth=1.0,
        linestyle="--",
        zorder=2
    )

    diff = p2_total - p1_total
    ratio = diff / p1_total * 100 if p1_total > 0 else 0.0

    ax.text(
        x[0],
        p1_total + max_total * 0.014,
        f"{p1_total:.0f}",
        ha="center",
        fontsize=10.8,
        color=COLORS["text"]
    )

    ax.text(
        x[-1],
        p2_total + max_total * 0.014,
        f"{p2_total:.0f}",
        ha="center",
        fontsize=10.8,
        color=COLORS["text"]
    )

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10.5, rotation=20, ha="right")
    ax.set_ylabel("成本 / 元", fontsize=12)

    y_min = min(p1_total, p2_total, cumulative) * 0.92
    y_max = max(p1_total, p2_total, cumulative) * 1.08
    ax.set_ylim(y_min, y_max)

    style_axis(ax)

    add_header(
        fig,
        "绿色限行政策下总成本变化分解",
        f"问题二相较问题一总成本增加 {diff:.2f} 元，变化率 {ratio:.2f}%"
    )

    fig.subplots_adjust(top=0.82, bottom=0.22, left=0.08, right=0.97)
    save_fig(fig, "p2_total_cost_compare.png")


# =========================================================
# 图2：成本构成对比
# =========================================================
def plot_cost_structure_stacked(p1, p2):
    components = ["固定成本", "能耗成本", "碳排成本", "等待成本", "迟到成本"]

    p1_values = np.array([get_metric(p1, c) for c in components], dtype=float)
    p2_values = np.array([get_metric(p2, c) for c in components], dtype=float)

    totals = [p1_values.sum(), p2_values.sum()]
    y = np.array([1, 0])

    fig, ax = plt.subplots(figsize=(12, 5.8))
    fig.patch.set_facecolor("white")

    lefts = np.zeros(2)

    for idx, comp in enumerate(components):
        vals = np.array([p1_values[idx], p2_values[idx]])

        ax.barh(
            y,
            vals,
            left=lefts,
            height=0.38,
            color=COST_COLOR_MAP[comp],
            edgecolor="white",
            linewidth=1.0,
            label=comp,
            zorder=3
        )

        for j, val in enumerate(vals):
            pct = val / totals[j] * 100 if totals[j] > 0 else 0
            if pct >= 6:
                ax.text(
                    lefts[j] + val / 2,
                    y[j],
                    f"{pct:.1f}%",
                    ha="center",
                    va="center",
                    fontsize=9.5,
                    color="white",
                    fontweight="bold"
                )

        lefts += vals

    ax.set_yticks(y)
    ax.set_yticklabels(["问题一", "问题二"], fontsize=12)
    ax.set_xlabel("成本 / 元", fontsize=12)

    ax.text(totals[0] * 1.01, y[0], f"{totals[0]:.0f} 元", va="center", fontsize=10.5)
    ax.text(totals[1] * 1.01, y[1], f"{totals[1]:.0f} 元", va="center", fontsize=10.5)

    ax.set_xlim(0, max(totals) * 1.18)
    ax.legend(
        ncol=5,
        frameon=False,
        fontsize=10,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.22)
    )

    style_axis(ax, grid_axis="x")

    add_header(
        fig,
        "问题一与问题二成本构成对比",
        "横向堆叠条形图展示各类成本在总成本中的贡献"
    )

    fig.subplots_adjust(top=0.80, bottom=0.25, left=0.10, right=0.95)
    save_fig(fig, "p2_cost_structure_compare.png")


# =========================================================
# 图3：车型使用对比
# =========================================================
def plot_vehicle_type_compare(p1, p2):
    vehicle_cols = [
        ("fuel_3000数量", "燃油车 3000kg"),
        ("fuel_1500数量", "燃油车 1500kg"),
        ("fuel_1250数量", "燃油车 1250kg"),
        ("ev_3000数量", "新能源车 3000kg"),
        ("ev_1250数量", "新能源车 1250kg"),
    ]

    labels = [x[1] for x in vehicle_cols]
    p1_values = [get_metric(p1, x[0]) for x in vehicle_cols]
    p2_values = [get_metric(p2, x[0]) for x in vehicle_cols]

    y = np.arange(len(labels))
    h = 0.32

    fig, ax = plt.subplots(figsize=(11.5, 6.2))
    fig.patch.set_facecolor("white")

    bars1 = ax.barh(
        y - h / 2,
        p1_values,
        height=h,
        color=COLORS["p1"],
        edgecolor="white",
        linewidth=1.0,
        label="问题一",
        zorder=3
    )

    bars2 = ax.barh(
        y + h / 2,
        p2_values,
        height=h,
        color=COLORS["p2"],
        edgecolor="white",
        linewidth=1.0,
        label="问题二",
        zorder=3
    )

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=11)
    ax.set_xlabel("车辆数 / 辆", fontsize=12)

    max_v = max(max(p1_values), max(p2_values))
    ax.set_xlim(0, max_v * 1.22)

    for bars in [bars1, bars2]:
        for bar in bars:
            w = bar.get_width()
            ax.text(
                w + max_v * 0.015,
                bar.get_y() + bar.get_height() / 2,
                f"{w:.0f}",
                ha="left",
                va="center",
                fontsize=10
            )

    ax.legend(frameon=False, fontsize=11, loc="lower right")

    style_axis(ax, grid_axis="x")

    add_header(
        fig,
        "问题一与问题二车型使用数量对比",
        "绿色限行政策主要引起小型燃油车使用数量变化"
    )

    fig.subplots_adjust(top=0.82, bottom=0.12, left=0.17, right=0.95)
    save_fig(fig, "p2_vehicle_type_compare.png")


# =========================================================
# 图4：碳排放量对比
# =========================================================
def plot_carbon_emission_compare(p1, p2):
    p1_emission = get_metric(p1, "碳排成本") / CARBON_COST_PER_UNIT
    p2_emission = get_metric(p2, "碳排成本") / CARBON_COST_PER_UNIT

    values = [p1_emission, p2_emission]
    labels = ["问题一", "问题二"]
    colors = [COLORS["p1"], COLORS["p2"]]

    diff = p2_emission - p1_emission
    ratio = diff / p1_emission * 100 if p1_emission > 0 else 0.0

    fig, ax = plt.subplots(figsize=(9.2, 5.0))
    fig.patch.set_facecolor("white")

    y = np.arange(len(labels))
    bars = ax.barh(
        y,
        values,
        height=0.42,
        color=colors,
        edgecolor="white",
        linewidth=1.0,
        zorder=3
    )

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=12)
    ax.invert_yaxis()
    ax.set_xlabel("碳排放量 / kg", fontsize=12)

    x_min = min(values) * 0.965
    x_max = max(values) * 1.045
    ax.set_xlim(x_min, x_max)

    for bar, value in zip(bars, values):
        ax.text(
            value + (x_max - x_min) * 0.008,
            bar.get_y() + bar.get_height() / 2,
            f"{value:,.0f} kg",
            ha="left",
            va="center",
            fontsize=11,
            color=COLORS["text"]
        )

    ax.text(
        0.98,
        0.10,
        f"较问题一增加 {diff:,.2f} kg，变化率 {ratio:.2f}%",
        transform=ax.transAxes,
        ha="right",
        va="center",
        fontsize=11,
        color=COLORS["text"],
        bbox=dict(
            boxstyle="round,pad=0.38",
            facecolor="#F7F8FA",
            edgecolor="#D3D8E0"
        )
    )

    style_axis(ax, grid_axis="x")

    add_header(
        fig,
        "问题一与问题二碳排放量对比",
        "采用碳排成本除以单位碳成本得到估算碳排放量"
    )

    fig.subplots_adjust(top=0.78, bottom=0.16, left=0.13, right=0.95)
    save_fig(fig, "p2_carbon_emission_compare.png")


# =========================================================
# 图5：时间窗成本对比
# =========================================================
def plot_time_penalty_compare(p1, p2):
    categories = ["等待成本", "迟到成本"]
    p1_values = np.array([
        get_metric(p1, "等待成本"),
        get_metric(p1, "迟到成本")
    ], dtype=float)
    p2_values = np.array([
        get_metric(p2, "等待成本"),
        get_metric(p2, "迟到成本")
    ], dtype=float)

    y = np.arange(len(categories))
    h = 0.32

    fig, ax = plt.subplots(figsize=(10.2, 5.4))
    fig.patch.set_facecolor("white")

    bars1 = ax.barh(
        y - h / 2,
        p1_values,
        height=h,
        color=COLORS["p1"],
        edgecolor="white",
        linewidth=1.0,
        label="问题一",
        zorder=3
    )

    bars2 = ax.barh(
        y + h / 2,
        p2_values,
        height=h,
        color=COLORS["p2"],
        edgecolor="white",
        linewidth=1.0,
        label="问题二",
        zorder=3
    )

    ax.set_yticks(y)
    ax.set_yticklabels(categories, fontsize=12)
    ax.invert_yaxis()
    ax.set_xlabel("成本 / 元", fontsize=12)

    x_max = max(p1_values.max(), p2_values.max()) * 1.25
    ax.set_xlim(0, x_max)

    for bars in [bars1, bars2]:
        for bar in bars:
            w = bar.get_width()
            ax.text(
                w + x_max * 0.012,
                bar.get_y() + bar.get_height() / 2,
                f"{w:,.0f}",
                ha="left",
                va="center",
                fontsize=10.5,
                color=COLORS["text"]
            )

    for i, name in enumerate(categories):
        diff = p2_values[i] - p1_values[i]
        ratio = diff / p1_values[i] * 100 if p1_values[i] > 0 else 0.0

        ax.text(
            x_max * 0.70,
            i,
            f"变化：{diff:+,.2f} 元（{ratio:+.1f}%）",
            ha="left",
            va="center",
            fontsize=10.3,
            color=COLORS["subtext"],
            bbox=dict(
                boxstyle="round,pad=0.26",
                facecolor="white",
                edgecolor="#E0E3E8",
                alpha=0.95
            )
        )

    ax.legend(frameon=False, fontsize=11, loc="lower right")

    style_axis(ax, grid_axis="x")

    add_header(
        fig,
        "绿色限行政策对时间窗成本的影响",
        "比较等待成本和迟到成本在政策前后的变化"
    )

    fig.subplots_adjust(top=0.80, bottom=0.16, left=0.13, right=0.95)
    save_fig(fig, "p2_time_penalty_compare.png")


# =========================================================
# 图6：总配送距离对比
# =========================================================
def plot_distance_compare(p1, p2):
    p1_distance = get_metric(p1, "总距离")
    p2_distance = get_metric(p2, "总距离")

    values = [p1_distance, p2_distance]
    labels = ["问题一", "问题二"]
    colors = [COLORS["p1"], COLORS["p2"]]

    diff = p2_distance - p1_distance
    ratio = diff / p1_distance * 100 if p1_distance > 0 else 0.0

    fig, ax = plt.subplots(figsize=(9.2, 5.0))
    fig.patch.set_facecolor("white")

    y = np.arange(len(labels))
    bars = ax.barh(
        y,
        values,
        height=0.42,
        color=colors,
        edgecolor="white",
        linewidth=1.0,
        zorder=3
    )

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=12)
    ax.invert_yaxis()
    ax.set_xlabel("总配送距离 / km", fontsize=12)

    x_min = min(values) * 0.965
    x_max = max(values) * 1.045
    ax.set_xlim(x_min, x_max)

    for bar, value in zip(bars, values):
        ax.text(
            value + (x_max - x_min) * 0.008,
            bar.get_y() + bar.get_height() / 2,
            f"{value:,.0f} km",
            ha="left",
            va="center",
            fontsize=11,
            color=COLORS["text"]
        )

    ax.text(
        0.98,
        0.10,
        f"较问题一增加 {diff:,.2f} km，变化率 {ratio:.2f}%",
        transform=ax.transAxes,
        ha="right",
        va="center",
        fontsize=11,
        color=COLORS["text"],
        bbox=dict(
            boxstyle="round,pad=0.38",
            facecolor="#F7F8FA",
            edgecolor="#D3D8E0"
        )
    )

    style_axis(ax, grid_axis="x")

    add_header(
        fig,
        "问题一与问题二总配送距离对比",
        "绿色限行政策导致路径重排，总配送距离出现小幅变化"
    )

    fig.subplots_adjust(top=0.78, bottom=0.16, left=0.13, right=0.95)
    save_fig(fig, "p2_distance_compare.png")


# =========================================================
# 图7：政策影响综合指标卡
# =========================================================
def plot_policy_kpi_cards(p1, p2):
    cards = [
        ("总成本", get_metric(p1, "总成本"), get_metric(p2, "总成本"), "元"),
        ("车辆数", get_metric(p1, "车辆数"), get_metric(p2, "车辆数"), "辆"),
        ("总配送距离", get_metric(p1, "总距离"), get_metric(p2, "总距离"), "km"),
        (
            "碳排放量",
            get_metric(p1, "碳排成本") / CARBON_COST_PER_UNIT,
            get_metric(p2, "碳排成本") / CARBON_COST_PER_UNIT,
            "kg"
        ),
    ]

    fig, axes = plt.subplots(1, 4, figsize=(14, 4.8))
    fig.patch.set_facecolor("white")

    for ax, (name, p1v, p2v, unit) in zip(axes, cards):
        diff = p2v - p1v
        ratio = diff / p1v * 100 if p1v > 0 else 0.0

        ax.set_facecolor(COLORS["light_gray"])
        ax.set_xticks([])
        ax.set_yticks([])

        for spine in ax.spines.values():
            spine.set_visible(False)

        ax.text(
            0.5, 0.78,
            name,
            ha="center",
            va="center",
            fontsize=13,
            fontweight="bold",
            color=COLORS["text"],
            transform=ax.transAxes
        )

        ax.text(
            0.5, 0.56,
            f"{p2v:,.1f}",
            ha="center",
            va="center",
            fontsize=19,
            fontweight="bold",
            color=COLORS["p2"],
            transform=ax.transAxes
        )

        ax.text(
            0.5, 0.43,
            unit,
            ha="center",
            va="center",
            fontsize=10.5,
            color=COLORS["subtext"],
            transform=ax.transAxes
        )

        direction = "↑" if diff >= 0 else "↓"

        ax.text(
            0.5, 0.23,
            f"{direction} {abs(diff):,.1f} ({ratio:+.2f}%)",
            ha="center",
            va="center",
            fontsize=10.5,
            color=COLORS["red"] if diff >= 0 else COLORS["green"],
            transform=ax.transAxes
        )

    add_header(
        fig,
        "绿色限行政策影响综合指标",
        "以问题二结果为主值，括号内为相较问题一的变化"
    )

    fig.subplots_adjust(top=0.78, bottom=0.10, left=0.04, right=0.98, wspace=0.16)
    save_fig(fig, "p2_policy_kpi_cards.png")


# =========================================================
# 文字分析
# =========================================================
def generate_text_analysis(p1, p2):
    p1_total = get_metric(p1, "总成本")
    p2_total = get_metric(p2, "总成本")
    total_diff = p2_total - p1_total
    total_ratio = total_diff / p1_total * 100 if p1_total > 0 else 0.0

    p1_vehicle = get_metric(p1, "车辆数")
    p2_vehicle = get_metric(p2, "车辆数")

    p1_distance = get_metric(p1, "总距离")
    p2_distance = get_metric(p2, "总距离")
    distance_diff = p2_distance - p1_distance
    distance_ratio = distance_diff / p1_distance * 100 if p1_distance > 0 else 0.0

    p1_carbon = get_metric(p1, "碳排成本") / CARBON_COST_PER_UNIT
    p2_carbon = get_metric(p2, "碳排成本") / CARBON_COST_PER_UNIT
    carbon_diff = p2_carbon - p1_carbon
    carbon_ratio = carbon_diff / p1_carbon * 100 if p1_carbon > 0 else 0.0

    p1_wait = get_metric(p1, "等待成本")
    p2_wait = get_metric(p2, "等待成本")
    p1_late = get_metric(p1, "迟到成本")
    p2_late = get_metric(p2, "迟到成本")

    text = f"""问题二结果分析

1. 总体结果
在引入绿色配送区限行政策后，问题二最终方案共启用车辆 {p2_vehicle:.0f} 辆，相比问题一的 {p1_vehicle:.0f} 辆增加 {p2_vehicle - p1_vehicle:.0f} 辆。
问题二总成本为 {p2_total:.2f} 元，相比问题一的 {p1_total:.2f} 元增加 {total_diff:.2f} 元，增幅为 {total_ratio:.2f}%。

2. 成本变化
政策实施后，固定成本由 {get_metric(p1, "固定成本"):.2f} 元增加至 {get_metric(p2, "固定成本"):.2f} 元；
能耗成本由 {get_metric(p1, "能耗成本"):.2f} 元增加至 {get_metric(p2, "能耗成本"):.2f} 元；
碳排成本由 {get_metric(p1, "碳排成本"):.2f} 元增加至 {get_metric(p2, "碳排成本"):.2f} 元；
等待成本由 {p1_wait:.2f} 元增加至 {p2_wait:.2f} 元；
迟到成本由 {p1_late:.2f} 元增加至 {p2_late:.2f} 元。

3. 距离与碳排变化
问题二总配送距离为 {p2_distance:.2f} km，相比问题一增加 {distance_diff:.2f} km，增幅为 {distance_ratio:.2f}%。
估算碳排放量由 {p1_carbon:.2f} kg 变化为 {p2_carbon:.2f} kg，变化量为 {carbon_diff:.2f} kg，变化率为 {carbon_ratio:.2f}%。

4. 结论说明
绿色限行政策实施后，配送方案需要对绿色区任务进行额外约束处理，导致车辆路径、服务时刻与车型使用配置发生调整。
在新能源车辆数量受限的情况下，政策会使总成本、等待成本和迟到成本上升，同时总距离与碳排放量也会出现小幅增长。
"""

    path = os.path.join(OUTPUT_DIR, "p2_result_analysis.txt")

    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"文字分析已生成：{path}")


# =========================================================
# 主函数
# =========================================================
def main():
    print("========== 问题二结果分析图生成开始 ==========")

    setup_chinese_font()
    ensure_clean_output_dir()

    p1 = read_summary(P1_SUMMARY_PATH)
    p2 = read_summary(P2_SUMMARY_PATH)

    print("问题一汇总：")
    print(p1)

    print("\n问题二汇总：")
    print(p2)

    plot_policy_kpi_cards(p1, p2)
    plot_total_cost_waterfall(p1, p2)
    plot_cost_structure_stacked(p1, p2)
    plot_vehicle_type_compare(p1, p2)
    plot_carbon_emission_compare(p1, p2)
    plot_time_penalty_compare(p1, p2)
    plot_distance_compare(p1, p2)

    generate_text_analysis(p1, p2)

    print("========== 问题二结果分析图生成结束 ==========")


if __name__ == "__main__":
    main()