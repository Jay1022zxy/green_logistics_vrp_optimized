# === Project path bootstrap ===
from pathlib import Path
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
# ==============================

from data_loader import build_problem_data, build_task_table
from plot_data import (
    plot_customer_map,
    plot_weight_hist,
    plot_volume_hist,
    plot_time_windows,
    plot_split_counts
)


def main():
    problem_data = build_problem_data()
    tasks_df = build_task_table(
        problem_data,
        max_weight=1500.0,
        max_volume=8.5
    )

    # 2D 版：论文正文推荐
    plot_customer_map(problem_data, "figures/paper/fig1_customer_map_2d.png")
    plot_weight_hist(problem_data, "figures/paper/fig2_weight_hist_2d.png", mode="2d")
    plot_volume_hist(problem_data, "figures/paper/fig3_volume_hist_2d.png", mode="2d")
    plot_time_windows(problem_data, "figures/paper/fig4_time_windows_2d.png")
    plot_split_counts(tasks_df, "figures/paper/fig5_split_counts_2d.png", mode="2d")

    # 伪 3D 版：答辩 / 附录推荐
    plot_weight_hist(problem_data, "figures/paper/fig2_weight_hist_3d.png", mode="3d")
    plot_volume_hist(problem_data, "figures/paper/fig3_volume_hist_3d.png", mode="3d")
    plot_split_counts(tasks_df, "figures/paper/fig5_split_counts_3d.png", mode="3d")

    print("图片已生成：")
    print("figures/paper/fig1_customer_map_2d.png")
    print("figures/paper/fig2_weight_hist_2d.png")
    print("figures/paper/fig3_volume_hist_2d.png")
    print("figures/paper/fig4_time_windows_2d.png")
    print("figures/paper/fig5_split_counts_2d.png")
    print("figures/paper/fig2_weight_hist_3d.png")
    print("figures/paper/fig3_volume_hist_3d.png")
    print("figures/paper/fig5_split_counts_3d.png")


if __name__ == "__main__":
    main()