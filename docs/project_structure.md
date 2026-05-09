# 项目目录说明

## src：完整源代码

`src/` 现在包含全部 Python 源代码，不再只放公共模块：

- `main_p1.py`：问题一入口
- `main_p2.py`：问题二入口
- `main_p3.py`：问题三入口
- `plot_p1_results.py`：问题一可视化
- `plot_p2_results.py`：问题二可视化
- `main_plot.py` / `plot_data.py`：基础数据可视化
- `alns_p1.py`、`cost.py`、`route_eval.py` 等：算法与评价公共模块

## scripts：快速运行脚本

`scripts/` 只保留 `.bat` 快速运行脚本，避免和源代码混淆。

## results / figures

`results/` 和 `figures/` 按问题编号拆分，方便论文引用和结果复查。
