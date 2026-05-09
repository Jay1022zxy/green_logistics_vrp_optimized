import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Patch, Rectangle, Polygon
from matplotlib.ticker import MaxNLocator, MultipleLocator
from matplotlib.lines import Line2D
import matplotlib.colors as mcolors


# =========================
# 全局参数：统一尺寸
# =========================
FIG_W = 10
FIG_H = 6.5
FIG_SIZE = (FIG_W, FIG_H)
DPI = 600


# =========================
# 全局绘图风格
# =========================
plt.rcParams["font.sans-serif"] = [
    "Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Arial Unicode MS", "DejaVu Sans"
]
plt.rcParams["axes.unicode_minus"] = False

plt.rcParams["figure.facecolor"] = "white"
plt.rcParams["axes.facecolor"] = "#FBFCFE"
plt.rcParams["savefig.facecolor"] = "white"

plt.rcParams["axes.edgecolor"] = "#2B2B2B"
plt.rcParams["axes.linewidth"] = 1.1

plt.rcParams["grid.color"] = "#D7DCE5"
plt.rcParams["grid.linestyle"] = "--"
plt.rcParams["grid.linewidth"] = 0.8
plt.rcParams["grid.alpha"] = 0.9

plt.rcParams["axes.titlesize"] = 18
plt.rcParams["axes.titleweight"] = "bold"
plt.rcParams["axes.labelsize"] = 14
plt.rcParams["xtick.labelsize"] = 11
plt.rcParams["ytick.labelsize"] = 11
plt.rcParams["legend.fontsize"] = 11


# =========================
# 统一配色
# =========================
COLORS = {
    "blue": "#2E6FBB",
    "orange": "#F28E2B",
    "green": "#2B9348",
    "red": "#D1495B",
    "purple": "#7B6FD0",
    "cyan": "#2AA7A1",
    "gray": "#7A7A7A",
    "light_green_fill": "#B7E4C7",
    "dark": "#1F2D3D",
    "light_bar_blue": "#4F86C6",
    "light_bar_cyan": "#4FB3B3",
    "avg_line": "#D1495B",
    "med_line": "#2B9348"
}


# =========================
# 通用辅助函数
# =========================
def _beautify_axes(ax):
    ax.grid(True, which="major", zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#3A3A3A")
    ax.spines["bottom"].set_color("#3A3A3A")
    ax.spines["left"].set_linewidth(1.0)
    ax.spines["bottom"].set_linewidth(1.0)
    ax.tick_params(axis="both", which="major", length=5, width=0.9, color="#3A3A3A")


def _save_fig_2d(fig, save_path):
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(save_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def _save_fig_3d(fig, save_path):
    """
    伪 3D 图使用 2D 保存方式，避免真 3D 坐标轴裁剪和遮挡。
    """
    fig.savefig(save_path, dpi=DPI, bbox_inches="tight", pad_inches=0.18)
    plt.close(fig)


def _add_title(ax, title, subtitle=None):
    ax.set_title(
        title,
        pad=24,
        color=COLORS["dark"],
        fontsize=18,
        fontweight="bold"
    )

    if subtitle:
        ax.text(
            0.5, 1.005,
            subtitle,
            transform=ax.transAxes,
            ha="center",
            va="bottom",
            fontsize=10,
            color="#6B7280"
        )


def _adjust_color(color, factor):
    """
    调整颜色明暗。
    factor < 1 变暗，factor > 1 变亮。
    """
    rgb = np.array(mcolors.to_rgb(color))

    if factor < 1:
        rgb = rgb * factor
    else:
        rgb = 1 - (1 - rgb) / factor

    return tuple(np.clip(rgb, 0, 1))


def _add_title_25d(fig, title, subtitle=None):
    """
    伪 3D 图标题：使用 figure 级标题，避免被图层遮挡。
    """
    fig.suptitle(
        title,
        y=0.975,
        fontsize=18,
        fontweight="bold",
        color=COLORS["dark"]
    )

    if subtitle:
        fig.text(
            0.5, 0.925,
            subtitle,
            ha="center",
            va="center",
            fontsize=10,
            color="#6B7280"
        )


def _draw_bar_25d(ax, x_center, height, width, depth_x, depth_y, color, zorder=3):
    """
    绘制伪 3D 柱子：
    front：正面
    right：右侧面
    top：顶面
    """
    if height <= 0:
        return

    left = x_center - width / 2
    right = x_center + width / 2

    front_color = color
    right_color = _adjust_color(color, 0.62)
    top_color = _adjust_color(color, 1.35)

    # 右侧面
    right_face = Polygon(
        [
            (right, 0),
            (right + depth_x, depth_y),
            (right + depth_x, height + depth_y),
            (right, height),
        ],
        closed=True,
        facecolor=right_color,
        edgecolor="white",
        linewidth=0.45,
        alpha=0.96,
        zorder=zorder
    )
    ax.add_patch(right_face)

    # 顶面
    top_face = Polygon(
        [
            (left, height),
            (right, height),
            (right + depth_x, height + depth_y),
            (left + depth_x, height + depth_y),
        ],
        closed=True,
        facecolor=top_color,
        edgecolor="white",
        linewidth=0.45,
        alpha=0.96,
        zorder=zorder + 0.1
    )
    ax.add_patch(top_face)

    # 正面
    front_face = Rectangle(
        (left, 0),
        width,
        height,
        facecolor=front_color,
        edgecolor="white",
        linewidth=0.65,
        alpha=0.96,
        zorder=zorder + 0.2
    )
    ax.add_patch(front_face)


def _style_25d_axes(ax):
    """
    伪 3D 柱状图坐标轴美化。
    """
    ax.grid(True, which="major", zorder=0)
    ax.set_axisbelow(True)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#3A3A3A")
    ax.spines["bottom"].set_color("#3A3A3A")
    ax.spines["left"].set_linewidth(1.0)
    ax.spines["bottom"].set_linewidth(1.0)

    ax.tick_params(axis="both", which="major", length=5, width=0.9, color="#3A3A3A")
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))


# =========================
# 1. 客户空间分布图（2D）
# =========================
def plot_customer_map(problem_data, save_path="customer_map.png"):
    all_customers_df = problem_data["all_customers_df"]
    depot_info = problem_data["depot_info"]

    green_df = all_customers_df[all_customers_df["是否绿色区"] == True]
    non_green_df = all_customers_df[all_customers_df["是否绿色区"] == False]

    fig, ax = plt.subplots(figsize=FIG_SIZE)

    green_fill = Circle(
        (0, 0), 10,
        facecolor=COLORS["light_green_fill"],
        edgecolor=COLORS["green"],
        linestyle=(0, (5, 3)),
        linewidth=1.8,
        alpha=0.22,
        zorder=1
    )
    ax.add_patch(green_fill)

    ax.scatter(
        non_green_df["x"], non_green_df["y"],
        s=46,
        c=COLORS["blue"],
        edgecolors="white",
        linewidths=0.7,
        alpha=0.95,
        label="非绿色区客户",
        zorder=3
    )

    ax.scatter(
        green_df["x"], green_df["y"],
        s=70,
        c=COLORS["orange"],
        edgecolors="white",
        linewidths=1.0,
        alpha=0.98,
        label="绿色区客户",
        zorder=4
    )

    ax.scatter(
        depot_info["x"], depot_info["y"],
        s=300,
        marker="*",
        c=COLORS["green"],
        edgecolors="white",
        linewidths=1.2,
        label="配送中心",
        zorder=6
    )

    ax.annotate(
        "配送中心",
        xy=(depot_info["x"], depot_info["y"]),
        xytext=(depot_info["x"] + 2.0, depot_info["y"] + 2.0),
        fontsize=10.5,
        color=COLORS["dark"],
        bbox=dict(boxstyle="round,pad=0.18", facecolor="white", edgecolor="none", alpha=0.9),
        arrowprops=dict(arrowstyle="->", color="#6B7280", lw=1.0),
        zorder=7
    )

    ax.scatter(
        0, 0,
        s=220,
        marker="X",
        c=COLORS["purple"],
        edgecolors="white",
        linewidths=1.8,
        label="市中心",
        zorder=10
    )

    ax.annotate(
        "市中心 (0,0)",
        xy=(0, 0),
        xytext=(2.2, -2.8),
        fontsize=10.5,
        color=COLORS["dark"],
        bbox=dict(boxstyle="round,pad=0.20", facecolor="white", edgecolor="none", alpha=0.92),
        arrowprops=dict(arrowstyle="->", color="#6B7280", lw=1.0),
        zorder=11
    )

    _add_title(ax, "客户空间分布图", "绿色配送区以市中心为圆心，半径为 10 km")

    ax.set_xlabel("X 坐标 / km")
    ax.set_ylabel("Y 坐标 / km")

    ax.set_aspect("equal", adjustable="box")
    ax.xaxis.set_major_locator(MultipleLocator(10))
    ax.yaxis.set_major_locator(MultipleLocator(10))

    _beautify_axes(ax)

    legend = ax.legend(
        loc="upper right",
        frameon=True,
        fancybox=True,
        framealpha=0.96,
        borderpad=0.8
    )
    legend.get_frame().set_edgecolor("#D0D7DE")
    legend.get_frame().set_facecolor("white")

    text_str = (
        f"客户总数：{len(all_customers_df)}\n"
        f"绿色区客户数：{int(green_df.shape[0])}\n"
        f"绿区圆心：市中心 (0,0)\n"
        f"绿区半径：10 km"
    )

    ax.text(
        0.03, 0.97,
        text_str,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=10.5,
        bbox=dict(boxstyle="round,pad=0.35", facecolor="white", edgecolor="#D9DEE7", alpha=0.95)
    )

    _save_fig_2d(fig, save_path)


# =========================
# 2. 时间窗分布图（2D）
# =========================
def plot_time_windows(problem_data, save_path="time_windows.png"):
    active_customers_df = problem_data["active_customers_df"].copy()
    active_customers_df = active_customers_df.sort_values("开始时间_小时").reset_index(drop=True)

    fig, ax = plt.subplots(figsize=FIG_SIZE)

    widths = (
        active_customers_df["结束时间_小时"] - active_customers_df["开始时间_小时"]
    ).values

    colors = []
    for w in widths:
        if w <= 0.8:
            colors.append(COLORS["red"])
        elif w <= 1.0:
            colors.append(COLORS["orange"])
        else:
            colors.append(COLORS["blue"])

    for i, row in active_customers_df.iterrows():
        start_t = row["开始时间_小时"]
        end_t = row["结束时间_小时"]

        ax.hlines(
            y=i,
            xmin=start_t,
            xmax=end_t,
            color=colors[i],
            linewidth=2.2,
            alpha=0.95,
            zorder=3
        )
        ax.plot(start_t, i, "o", ms=3.2, color=colors[i], zorder=4)
        ax.plot(end_t, i, "o", ms=3.2, color=colors[i], zorder=4)

    mean_start = active_customers_df["开始时间_小时"].mean()
    mean_end = active_customers_df["结束时间_小时"].mean()

    ax.axvline(mean_start, color=COLORS["green"], linestyle="--", linewidth=1.5, alpha=0.9)
    ax.axvline(mean_end, color=COLORS["purple"], linestyle="--", linewidth=1.5, alpha=0.9)

    _add_title(ax, "客户时间窗分布图", "按最早服务时刻排序；颜色表示时间窗宽度")

    ax.set_xlabel("时间 / 小时")
    ax.set_ylabel("客户排序编号")

    ax.set_xlim(
        active_customers_df["开始时间_小时"].min() - 0.5,
        active_customers_df["结束时间_小时"].max() + 0.5
    )

    _beautify_axes(ax)

    text_str = (
        f"客户数：{len(active_customers_df)}\n"
        f"平均最早时刻：{mean_start:.2f}\n"
        f"平均最晚时刻：{mean_end:.2f}"
    )

    ax.text(
        0.98, 0.03,
        text_str,
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=10.5,
        bbox=dict(boxstyle="round,pad=0.35", facecolor="white", edgecolor="#D9DEE7", alpha=0.96)
    )

    _save_fig_2d(fig, save_path)


# =========================
# 3. 重量分布图：2D
# =========================
def _plot_weight_hist_2d(problem_data, save_path):
    active_customers_df = problem_data["active_customers_df"]
    weight = active_customers_df["总重量"].values

    fig, ax = plt.subplots(figsize=FIG_SIZE)

    _, _, patches = ax.hist(
        weight,
        bins=20,
        color=COLORS["light_bar_blue"],
        edgecolor="white",
        linewidth=1.3,
        alpha=0.88,
        zorder=3
    )

    for i, patch in enumerate(patches):
        alpha = 0.70 + 0.25 * (i / max(len(patches) - 1, 1))
        patch.set_alpha(alpha)

    mean_val = np.mean(weight)
    median_val = np.median(weight)

    ax.axvline(mean_val, color=COLORS["avg_line"], linestyle="--", linewidth=2.6, label=f"均值 = {mean_val:.1f}")
    ax.axvline(median_val, color=COLORS["med_line"], linestyle="-.", linewidth=2.6, label=f"中位数 = {median_val:.1f}")

    _add_title(ax, "客户需求重量分布图", "用于观察需求规模分布及重尾特征")

    ax.set_xlabel("客户总需求重量 / kg")
    ax.set_ylabel("频数")

    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    _beautify_axes(ax)

    legend = ax.legend(frameon=True, fancybox=True, framealpha=0.96, loc="center right")
    legend.get_frame().set_edgecolor("#D0D7DE")
    legend.get_frame().set_facecolor("white")

    text_str = (
        f"样本数：{len(weight)}\n"
        f"最大值：{np.max(weight):.1f}\n"
        f"均值：{mean_val:.1f}\n"
        f"中位数：{median_val:.1f}"
    )

    ax.text(
        0.97, 0.94,
        text_str,
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=10.5,
        bbox=dict(boxstyle="round,pad=0.35", facecolor="white", edgecolor="#D9DEE7", alpha=0.96)
    )

    _save_fig_2d(fig, save_path)


# =========================
# 4. 体积分布图：2D
# =========================
def _plot_volume_hist_2d(problem_data, save_path):
    active_customers_df = problem_data["active_customers_df"]
    volume = active_customers_df["总体积"].values

    fig, ax = plt.subplots(figsize=FIG_SIZE)

    _, _, patches = ax.hist(
        volume,
        bins=20,
        color=COLORS["light_bar_cyan"],
        edgecolor="white",
        linewidth=1.3,
        alpha=0.88,
        zorder=3
    )

    for i, patch in enumerate(patches):
        alpha = 0.70 + 0.25 * (i / max(len(patches) - 1, 1))
        patch.set_alpha(alpha)

    mean_val = np.mean(volume)
    median_val = np.median(volume)

    ax.axvline(mean_val, color=COLORS["avg_line"], linestyle="--", linewidth=2.6, label=f"均值 = {mean_val:.2f}")
    ax.axvline(median_val, color=COLORS["med_line"], linestyle="-.", linewidth=2.6, label=f"中位数 = {median_val:.2f}")

    _add_title(ax, "客户需求体积分布图", "用于分析容积约束对派车与拆分的影响")

    ax.set_xlabel(r"客户总体积 / $m^3$")
    ax.set_ylabel("频数")

    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    _beautify_axes(ax)

    legend = ax.legend(frameon=True, fancybox=True, framealpha=0.96, loc="center right")
    legend.get_frame().set_edgecolor("#D0D7DE")
    legend.get_frame().set_facecolor("white")

    text_str = (
        f"样本数：{len(volume)}\n"
        f"最大值：{np.max(volume):.2f}\n"
        f"均值：{mean_val:.2f}\n"
        f"中位数：{median_val:.2f}"
    )

    ax.text(
        0.97, 0.94,
        text_str,
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=10.5,
        bbox=dict(boxstyle="round,pad=0.35", facecolor="white", edgecolor="#D9DEE7", alpha=0.96)
    )

    _save_fig_2d(fig, save_path)


# =========================
# 5. 拆分次数图：2D
# =========================
def _plot_split_counts_2d(tasks_df, save_path):
    split_df = tasks_df.groupby("原客户编号")["拆分数"].max().reset_index()

    x = split_df["原客户编号"].values
    y = split_df["拆分数"].values

    fig, ax = plt.subplots(figsize=FIG_SIZE)

    bar_colors = [COLORS["blue"] if v == 1 else COLORS["orange"] for v in y]

    bars = ax.bar(
        x, y,
        color=bar_colors,
        width=0.72,
        edgecolor="white",
        linewidth=0.8,
        alpha=0.92,
        zorder=3
    )

    for bar, v in zip(bars, y):
        bar.set_alpha(0.82 if v == 1 else 0.95)

    avg_split = np.mean(y)
    max_split = np.max(y)

    ax.axhline(avg_split, color=COLORS["red"], linestyle="--", linewidth=2.3, label=f"平均拆分次数 = {avg_split:.2f}")

    _add_title(ax, "客户任务拆分次数图", "橙色表示发生拆分的客户；蓝色表示无需拆分")

    ax.set_xlabel("原客户编号")
    ax.set_ylabel("拆分次数")

    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    _beautify_axes(ax)

    legend = ax.legend(frameon=True, fancybox=True, framealpha=0.96, loc="upper left")
    legend.get_frame().set_edgecolor("#D0D7DE")
    legend.get_frame().set_facecolor("white")

    text_str = (
        f"客户数：{len(split_df)}\n"
        f"平均拆分次数：{avg_split:.2f}\n"
        f"最大拆分次数：{int(max_split)}"
    )

    ax.text(
        0.98, 0.94,
        text_str,
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=10.5,
        bbox=dict(boxstyle="round,pad=0.35", facecolor="white", edgecolor="#D9DEE7", alpha=0.96)
    )

    _save_fig_2d(fig, save_path)


# =========================
# 6. 重量分布图：伪 3D
# =========================
def _plot_weight_hist_3d(problem_data, save_path):
    active_customers_df = problem_data["active_customers_df"]
    weight = active_customers_df["总重量"].values

    fig, ax = plt.subplots(figsize=FIG_SIZE)
    fig.subplots_adjust(left=0.09, right=0.97, bottom=0.14, top=0.78)

    counts, bins = np.histogram(weight, bins=20)

    bin_widths = np.diff(bins)
    centers = bins[:-1] + bin_widths / 2

    zmax = max(counts) if len(counts) > 0 else 1
    depth_y = zmax * 0.035

    for i, (x, h, bw) in enumerate(zip(centers, counts, bin_widths)):
        _draw_bar_25d(
            ax=ax,
            x_center=x,
            height=h,
            width=bw * 0.78,
            depth_x=bw * 0.10,
            depth_y=depth_y,
            color=COLORS["blue"],
            zorder=3 + i * 0.01
        )

    mean_val = np.mean(weight)
    median_val = np.median(weight)

    ax.axvline(
        mean_val,
        color=COLORS["red"],
        linestyle="--",
        linewidth=2.4,
        label=f"均值 = {mean_val:.1f}",
        zorder=20
    )

    ax.axvline(
        median_val,
        color=COLORS["green"],
        linestyle="-.",
        linewidth=2.4,
        label=f"中位数 = {median_val:.1f}",
        zorder=20
    )

    _add_title_25d(fig, "客户需求重量分布图", "立体柱状图用于观察需求规模分布及重尾特征")

    ax.set_xlabel("客户总需求重量 / kg")
    ax.set_ylabel("频数")

    ax.set_xlim(bins[0] - bin_widths[0] * 0.3, bins[-1] + bin_widths[-1] * 0.5)
    ax.set_ylim(0, zmax * 1.20)

    _style_25d_axes(ax)

    legend = ax.legend(frameon=True, fancybox=True, framealpha=0.96, loc="upper right")
    legend.get_frame().set_edgecolor("#D0D7DE")
    legend.get_frame().set_facecolor("white")

    text_str = (
        f"样本数：{len(weight)}\n"
        f"最大值：{np.max(weight):.1f}\n"
        f"均值：{mean_val:.1f}\n"
        f"中位数：{median_val:.1f}"
    )

    ax.text(
        0.97, 0.70,
        text_str,
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=10.5,
        bbox=dict(boxstyle="round,pad=0.35", facecolor="white", edgecolor="#D9DEE7", alpha=0.96),
        zorder=30
    )

    _save_fig_3d(fig, save_path)


# =========================
# 7. 体积分布图：伪 3D
# =========================
def _plot_volume_hist_3d(problem_data, save_path):
    active_customers_df = problem_data["active_customers_df"]
    volume = active_customers_df["总体积"].values

    fig, ax = plt.subplots(figsize=FIG_SIZE)
    fig.subplots_adjust(left=0.09, right=0.97, bottom=0.14, top=0.78)

    counts, bins = np.histogram(volume, bins=20)

    bin_widths = np.diff(bins)
    centers = bins[:-1] + bin_widths / 2

    zmax = max(counts) if len(counts) > 0 else 1
    depth_y = zmax * 0.035

    for i, (x, h, bw) in enumerate(zip(centers, counts, bin_widths)):
        _draw_bar_25d(
            ax=ax,
            x_center=x,
            height=h,
            width=bw * 0.78,
            depth_x=bw * 0.10,
            depth_y=depth_y,
            color=COLORS["cyan"],
            zorder=3 + i * 0.01
        )

    mean_val = np.mean(volume)
    median_val = np.median(volume)

    ax.axvline(
        mean_val,
        color=COLORS["red"],
        linestyle="--",
        linewidth=2.4,
        label=f"均值 = {mean_val:.2f}",
        zorder=20
    )

    ax.axvline(
        median_val,
        color=COLORS["green"],
        linestyle="-.",
        linewidth=2.4,
        label=f"中位数 = {median_val:.2f}",
        zorder=20
    )

    _add_title_25d(fig, "客户需求体积分布图", "立体柱状图用于分析容积约束对派车与拆分的影响")

    ax.set_xlabel(r"客户总体积 / $m^3$")
    ax.set_ylabel("频数")

    ax.set_xlim(bins[0] - bin_widths[0] * 0.3, bins[-1] + bin_widths[-1] * 0.5)
    ax.set_ylim(0, zmax * 1.20)

    _style_25d_axes(ax)

    legend = ax.legend(frameon=True, fancybox=True, framealpha=0.96, loc="upper right")
    legend.get_frame().set_edgecolor("#D0D7DE")
    legend.get_frame().set_facecolor("white")

    text_str = (
        f"样本数：{len(volume)}\n"
        f"最大值：{np.max(volume):.2f}\n"
        f"均值：{mean_val:.2f}\n"
        f"中位数：{median_val:.2f}"
    )

    ax.text(
        0.97, 0.70,
        text_str,
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=10.5,
        bbox=dict(boxstyle="round,pad=0.35", facecolor="white", edgecolor="#D9DEE7", alpha=0.96),
        zorder=30
    )

    _save_fig_3d(fig, save_path)


# =========================
# 8. 拆分次数图：伪 3D
# =========================
def _plot_split_counts_3d(tasks_df, save_path):
    split_df = tasks_df.groupby("原客户编号")["拆分数"].max().reset_index()

    x = split_df["原客户编号"].values.astype(float)
    y = split_df["拆分数"].values.astype(float)

    fig, ax = plt.subplots(figsize=FIG_SIZE)
    fig.subplots_adjust(left=0.09, right=0.97, bottom=0.14, top=0.78)

    max_y = np.max(y)
    depth_y = max_y * 0.040

    bar_width = 0.55
    depth_x = 0.11

    for i, (cid, value) in enumerate(zip(x, y)):
        color = COLORS["blue"] if value == 1 else COLORS["orange"]

        _draw_bar_25d(
            ax=ax,
            x_center=cid,
            height=value,
            width=bar_width,
            depth_x=depth_x,
            depth_y=depth_y,
            color=color,
            zorder=3 + i * 0.01
        )

    avg_split = np.mean(y)

    ax.axhline(
        avg_split,
        color=COLORS["red"],
        linestyle="--",
        linewidth=2.4,
        label=f"平均拆分次数 = {avg_split:.2f}",
        zorder=25
    )

    _add_title_25d(fig, "客户任务拆分次数图", "立体柱状图展示拆分任务在客户之间的分布差异")

    ax.set_xlabel("原客户编号")
    ax.set_ylabel("拆分次数")

    ax.set_xlim(x.min() - 3, x.max() + 4)
    ax.set_ylim(0, max_y * 1.18)

    _style_25d_axes(ax)

    handles = [
        Patch(facecolor=COLORS["orange"], edgecolor="white", label="发生拆分"),
        Patch(facecolor=COLORS["blue"], edgecolor="white", label="无需拆分"),
        Line2D([0], [0], color=COLORS["red"], lw=2.4, linestyle="--", label=f"平均拆分次数 = {avg_split:.2f}")
    ]

    legend = ax.legend(
        handles=handles,
        loc="upper left",
        frameon=True,
        fancybox=True,
        framealpha=0.96
    )
    legend.get_frame().set_edgecolor("#D0D7DE")
    legend.get_frame().set_facecolor("white")

    text_str = (
        f"客户数：{len(split_df)}\n"
        f"平均拆分次数：{avg_split:.2f}\n"
        f"最大拆分次数：{int(max_y)}"
    )

    ax.text(
        0.97, 0.72,
        text_str,
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=10.5,
        bbox=dict(boxstyle="round,pad=0.35", facecolor="white", edgecolor="#D9DEE7", alpha=0.96),
        zorder=30
    )

    _save_fig_3d(fig, save_path)


# =========================
# 9. 外部统一接口
# =========================
def plot_weight_hist(problem_data, save_path="weight_hist.png", mode="2d"):
    mode = mode.lower()

    if mode == "2d":
        _plot_weight_hist_2d(problem_data, save_path)
    elif mode == "3d":
        _plot_weight_hist_3d(problem_data, save_path)
    else:
        raise ValueError("mode 只能是 '2d' 或 '3d'")


def plot_volume_hist(problem_data, save_path="volume_hist.png", mode="2d"):
    mode = mode.lower()

    if mode == "2d":
        _plot_volume_hist_2d(problem_data, save_path)
    elif mode == "3d":
        _plot_volume_hist_3d(problem_data, save_path)
    else:
        raise ValueError("mode 只能是 '2d' 或 '3d'")


def plot_split_counts(tasks_df, save_path="split_counts.png", mode="2d"):
    mode = mode.lower()

    if mode == "2d":
        _plot_split_counts_2d(tasks_df, save_path)
    elif mode == "3d":
        _plot_split_counts_3d(tasks_df, save_path)
    else:
        raise ValueError("mode 只能是 '2d' 或 '3d'")

    import os
    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Polygon, Patch
    from matplotlib.lines import Line2D

    # =========================
    # 全局中文与风格设置
    # =========================
    plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False

    def ensure_dir(path):
        folder = os.path.dirname(path)
        if folder and not os.path.exists(folder):
            os.makedirs(folder)

    def get_split_series(tasks_df):
        """
        从 tasks_df 生成“原客户编号 -> 拆分次数”的序列
        兼容两种情况：
        1) tasks_df 每行就是一个任务：按原客户编号 groupby size
        2) tasks_df 已经有 '拆分数' 列，且每个客户只保留一行
        """
        if '原客户编号' not in tasks_df.columns:
            raise ValueError("tasks_df 中缺少列：'原客户编号'")

        # 如果已经是客户级汇总表
        if '拆分数' in tasks_df.columns and tasks_df['原客户编号'].nunique() == len(tasks_df):
            split_series = tasks_df.set_index('原客户编号')['拆分数'].sort_index()
        else:
            # 默认按任务表统计
            if '任务编号' in tasks_df.columns:
                split_series = tasks_df.groupby('原客户编号')['任务编号'].count().sort_index()
            else:
                split_series = tasks_df.groupby('原客户编号').size().sort_index()

        return split_series

    def draw_bar_25d(ax, x, h,
                     width=0.52,
                     depth_x=0.24,
                     depth_y=0.35,
                     face_color='#F28E2B',
                     side_color='#C86A14',
                     top_color='#F7B267',
                     shadow_color='#D9DDE3',
                     edge_color='white',
                     shadow=True,
                     zorder=3):
        """
        绘制单个 2.5D 柱子：
        - 正面：Rectangle
        - 右侧面：Polygon
        - 顶面：Polygon
        - 阴影：Rectangle（偏移）
        """
        left = x - width / 2

        # 阴影（让 2.5D 更明显）
        if shadow:
            shadow_rect = Rectangle(
                (left + depth_x * 0.18, depth_y * 0.10),
                width,
                h,
                facecolor=shadow_color,
                edgecolor='none',
                alpha=0.35,
                zorder=zorder - 2
            )
            ax.add_patch(shadow_rect)

        # 正面
        front = Rectangle(
            (left, 0), width, h,
            facecolor=face_color,
            edgecolor=edge_color,
            linewidth=1.0,
            zorder=zorder
        )
        ax.add_patch(front)

        # 侧面
        side = Polygon(
            [
                (left + width, 0),
                (left + width + depth_x, depth_y),
                (left + width + depth_x, h + depth_y),
                (left + width, h)
            ],
            closed=True,
            facecolor=side_color,
            edgecolor=edge_color,
            linewidth=0.8,
            zorder=zorder - 0.1
        )
        ax.add_patch(side)

        # 顶面
        top = Polygon(
            [
                (left, h),
                (left + width, h),
                (left + width + depth_x, h + depth_y),
                (left + depth_x, h + depth_y)
            ],
            closed=True,
            facecolor=top_color,
            edgecolor=edge_color,
            linewidth=0.8,
            zorder=zorder + 0.1
        )
        ax.add_patch(top)

    def plot_split_counts_25d(tasks_df, save_path='split_counts_25d.png'):
        """
        客户任务拆分次数图（2.5D增强版）
        """
        split_series = get_split_series(tasks_df)

        customer_ids = split_series.index.to_list()
        counts = split_series.values.astype(float)

        customer_num = len(split_series)
        avg_split = split_series.mean()
        max_split = split_series.max()

        # ========== 颜色设置 ==========
        orange_front = '#F28E2B'
        orange_side = '#C86A14'
        orange_top = '#F7B267'

        blue_front = '#3A78C2'
        blue_side = '#24518C'
        blue_top = '#72A7E6'

        bg_color = '#F7F9FC'
        grid_color = '#D7DEE8'
        title_color = '#23364D'
        subtitle_color = '#6B778C'

        # ========== 画布 ==========
        fig, ax = plt.subplots(figsize=(16, 9), dpi=220)
        fig.patch.set_facecolor('white')
        ax.set_facecolor(bg_color)

        # 给标题和副标题预留空间
        fig.subplots_adjust(left=0.08, right=0.94, bottom=0.12, top=0.78)

        # ========== 标题 ==========
        fig.suptitle(
            '客户任务拆分次数图',
            fontsize=26,
            fontweight='bold',
            color=title_color,
            y=0.965
        )

        fig.text(
            0.5, 0.915,
            '2.5D柱状图展示拆分任务在客户之间的分布差异',
            ha='center',
            va='center',
            fontsize=14,
            color=subtitle_color
        )

        # ========== 网格 ==========
        ax.grid(axis='y', linestyle='--', linewidth=1.0, color=grid_color, alpha=0.9)
        ax.grid(axis='x', linestyle='--', linewidth=0.8, color=grid_color, alpha=0.45)
        ax.set_axisbelow(True)

        # ========== 绘制 2.5D 柱子 ==========
        # 为了让 2.5D 更明显，这里把深度设得更大一些
        width = 0.52
        depth_x = 0.24
        depth_y = 0.35

        for x, h in zip(customer_ids, counts):
            # h > 1 认为发生拆分
            if h > 1:
                draw_bar_25d(
                    ax, x, h,
                    width=width,
                    depth_x=depth_x,
                    depth_y=depth_y,
                    face_color=orange_front,
                    side_color=orange_side,
                    top_color=orange_top,
                    shadow=True,
                    zorder=4
                )
            else:
                draw_bar_25d(
                    ax, x, h,
                    width=width,
                    depth_x=depth_x,
                    depth_y=depth_y,
                    face_color=blue_front,
                    side_color=blue_side,
                    top_color=blue_top,
                    shadow=True,
                    zorder=3
                )

        # ========== 均值线 ==========
        ax.axhline(
            avg_split,
            color='#D1495B',
            linestyle='--',
            linewidth=2.6,
            alpha=0.95,
            zorder=2
        )

        # ========== 坐标轴设置 ==========
        ax.set_xlabel('原客户编号', fontsize=20, labelpad=12)
        ax.set_ylabel('拆分次数', fontsize=20, labelpad=12)

        ax.tick_params(axis='x', labelsize=13)
        ax.tick_params(axis='y', labelsize=13)

        xmin = min(customer_ids) - 3
        xmax = max(customer_ids) + 3 + depth_x
        ymax = max_split + depth_y + 1.0

        ax.set_xlim(xmin, xmax)
        ax.set_ylim(0, ymax)

        # x轴刻度每10个一组
        xticks = np.arange(0, max(customer_ids) + 1, 10)
        ax.set_xticks(xticks)

        yticks = np.arange(0, int(np.ceil(max_split)) + 2, 1)
        ax.set_yticks(yticks)

        # 去除上右边框，保留左下
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        for side in ['left', 'bottom']:
            ax.spines[side].set_linewidth(1.2)
            ax.spines[side].set_color('#444444')

        # ========== 图例 ==========
        legend_handles = [
            Patch(facecolor=orange_front, edgecolor='white', label='发生拆分'),
            Patch(facecolor=blue_front, edgecolor='white', label='无需拆分'),
            Line2D([0], [0], color='#D1495B', lw=2.6, linestyle='--',
                   label=f'平均拆分次数 = {avg_split:.2f}')
        ]

        leg = ax.legend(
            handles=legend_handles,
            loc='upper left',
            fontsize=13,
            frameon=True,
            fancybox=True,
            framealpha=0.96
        )
        leg.get_frame().set_facecolor('#F8F9FB')
        leg.get_frame().set_edgecolor('#C8CFD9')
        leg.get_frame().set_linewidth(1.2)

        # ========== 统计信息框 ==========
        info_text = (
            f'客户数：{customer_num}\n'
            f'平均拆分次数：{avg_split:.2f}\n'
            f'最大拆分次数：{int(max_split)}'
        )
        ax.text(
            0.97, 0.72, info_text,
            transform=ax.transAxes,
            ha='right', va='top',
            fontsize=13,
            bbox=dict(
                boxstyle='round,pad=0.35',
                facecolor='white',
                edgecolor='#C8CFD9',
                linewidth=1.2,
                alpha=0.96
            )
        )

        # 保存
        ensure_dir(save_path)
        fig.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close(fig)

        print(f'图片已生成：{save_path}')

    # =========================
    # 测试调用示例
    # =========================
    if __name__ == '__main__':
        # 这里替换成你自己的任务表读取方式
        # 例如：
        # tasks_df = pd.read_excel('data/tasks.xlsx')
        # 或者已经在别处 build_task_table() 得到 tasks_df

        # ===== 示例伪数据（你正式使用时删掉这段）=====
        demo_data = []
        rng = np.random.default_rng(42)
        for cid in range(2, 99):
            if 40 <= cid <= 75:
                cnt = rng.integers(2, 7)
            else:
                cnt = rng.integers(1, 3)
            if cid in [8, 31, 55]:
                cnt = rng.integers(7, 10)
            for k in range(cnt):
                demo_data.append({'任务编号': f'{cid}_{k + 1}', '原客户编号': cid})
        tasks_df = pd.DataFrame(demo_data)
        # ===== 示例伪数据结束 =====

        plot_split_counts_25d(tasks_df, save_path='split_counts_25d.png')