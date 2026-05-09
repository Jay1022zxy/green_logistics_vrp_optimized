# Green Logistics VRP Optimization

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9%2B-blue" />
  <img src="https://img.shields.io/badge/Algorithm-ALNS%20%7C%20LNS--VNS-green" />
  <img src="https://img.shields.io/badge/Model-VRP%20%7C%20Green%20Logistics-orange" />
  <img src="https://img.shields.io/badge/Status-Completed-brightgreen" />
</p>

## 项目简介

本项目围绕 **城市绿色物流配送调度优化问题** 展开，综合考虑 **异质车队、双容量约束、软时间窗、时变交通速度、绿色配送区限行政策和动态订单扰动** 等因素，构建了一个从静态配送优化、绿色政策约束到动态事件响应的递进式优化框架。

项目以 **总配送成本最小化** 为核心目标，使用 Python 完成数据读取、任务拆分、路径构造、成本评估、启发式优化、结果分析和可视化输出，最终形成完整的建模代码、结果文件、论文图表和 LaTeX 论文源文件。

---

## 摘要流程图

> 请将流程图图片放在 `figures/paper/summary_flowchart.png`，GitHub 会自动显示。

<p align="center">
  <img src="figures/paper/liuchengtu0.png" width="850" alt="整体流程图" />
</p>

---

## 研究问题

| 问题 | 场景 | 核心任务 | 求解方法 |
|---|---|---|---|
| 问题一 | 无绿色限行的静态调度 | 在完成全部配送任务的前提下，最小化固定成本、能耗成本、碳排成本、等待成本和迟到成本 | ALNS 多随机种子搜索 |
| 问题二 | 绿色配送区限行调度 | 在 8:00--16:00 燃油车禁入绿色区的约束下重新规划车辆路径 | 嵌入限行约束的改进 ALNS |
| 问题三 | 动态订单扰动响应 | 面对订单取消、新增、地址变更和时间窗收紧，进行局部路径修复 | 状态冻结 + LNS--VNS 局部重优化 |

---

## 项目亮点

- **统一建模框架**：三个问题共用任务集合、车辆集合、约束体系和成本评价口径，使不同场景下的结果具有可比性。
- **绿色物流约束建模**：显式刻画绿色配送区限行政策对车辆分配、路径时序、配送距离和成本结构的影响。
- **动态调度机制**：针对实际配送中的订单扰动，采用“状态冻结 + 任务更新 + 局部重优化”的滚动响应策略。
- **多随机种子验证**：通过多个随机种子重复求解，降低启发式算法随机性的影响，提高结果稳定性。
- **完整工程化输出**：包含源代码、运行脚本、结果文件、论文图表、LaTeX 论文和项目说明文档。

---

## 核心结果

| 指标 | 问题一：静态调度 | 问题二：绿色限行 | 变化 |
|---|---:|---:|---:|
| 启用车辆数 | 140 | 141 | +1 |
| 总配送距离 | 18537.97 km | 18632.96 km | +94.98 km |
| 总配送成本 | 115512.59 元 | 120037.28 元 | +4524.70 元 |
| 等待成本 | 14942.76 元 | 15975.28 元 | +1032.52 元 |
| 迟到成本 | 148.58 元 | 2723.80 元 | +2575.23 元 |
| 估算碳排放量 | 12146.42 kg | 12292.33 kg | +145.91 kg |

问题三中，针对订单取消、新增订单、地址变更和时间窗收紧四类动态事件进行局部重优化后，均能够较初始响应方案降低剩余运营成本，同时将路径调整数量控制在较小范围内，说明该动态响应策略兼顾了成本优化与路径稳定性。

---

## 目录结构

```text
green_logistics_vrp_optimized/
├── src/                         # 完整 Python 源代码
│   ├── main_p1.py                # 问题一：静态调度入口
│   ├── main_p2.py                # 问题二：绿色限行入口
│   ├── main_p3.py                # 问题三：动态响应入口
│   ├── alns_p1.py                # ALNS 核心算法
│   ├── config.py                 # 全局参数配置
│   ├── cost.py                   # 成本计算模块
│   ├── data_loader.py            # 数据读取与预处理
│   ├── initial_solution.py       # 初始解构造
│   ├── route_eval.py             # 路径评价模块
│   ├── route_merge.py            # 路径合并模块
│   ├── task_eval.py              # 任务评价模块
│   ├── main_init.py              # 初始方案生成入口
│   ├── main_plot.py              # 基础数据可视化入口
│   ├── plot_data.py              # 基础数据图表
│   ├── plot_p1_results.py        # 问题一结果图表
│   └── plot_p2_results.py        # 问题二结果图表
├── data/
│   ├── raw/                      # 原始 Excel 数据
│   └── processed/                # 中间处理数据
├── results/
│   ├── problem1/                 # 问题一结果
│   ├── problem2/                 # 问题二结果与日志
│   └── problem3/                 # 问题三结果
├── figures/
│   ├── paper/                    # 论文使用图片
│   ├── problem1/                 # 问题一可视化图表
│   ├── problem2/                 # 问题二可视化图表
│   └── problem3/                 # 问题三可视化图表
├── paper/
│   └── main.tex                  # LaTeX 论文源文件
├── scripts/                      # Windows 快速运行脚本
├── docs/                         # 项目说明文档
├── requirements.txt              # Python 依赖
└── README.md
```

---

## 环境依赖

建议使用 Python 3.9 及以上版本。

```bash
pip install -r requirements.txt
```

主要依赖包括：

```text
pandas
numpy
matplotlib
openpyxl
```

---

## 数据准备

请将原始 Excel 数据放入 `data/raw/` 目录，文件名建议保持如下格式：

```text
data/raw/
├── 订单信息.xlsx
├── 距离矩阵.xlsx
├── 客户坐标信息.xlsx
└── 时间窗.xlsx
```

如果文件名发生变化，需要同步修改 `src/data_loader.py` 或相关入口脚本中的读取路径。

---

## 运行方式

在项目根目录下执行：

```bash
python src/main_p1.py
python src/main_p2.py
python src/main_p3.py
```

也可以在 Windows 环境下双击 `scripts/` 中的 `.bat` 文件快速运行：

```text
scripts/
├── run_problem1.bat
├── run_problem2.bat
├── run_problem3.bat
├── plot_problem1.bat
├── plot_problem2.bat
└── plot_data.bat
```

---

## 图表生成

生成基础数据分析图：

```bash
python src/main_plot.py
```

生成问题一结果图：

```bash
python src/plot_p1_results.py
```

生成问题二结果图：

```bash
python src/plot_p2_results.py
```

图表默认输出到：

```text
figures/problem1/
figures/problem2/
figures/problem3/
figures/paper/
```

---

## 结果文件说明

| 路径 | 内容 |
|---|---|
| `results/problem1/problem1_summary.csv` | 问题一最终方案汇总 |
| `results/problem1/problem1_routes.csv` | 问题一路径明细 |
| `results/problem1/problem1_multiseed_summary.csv` | 问题一多随机种子结果 |
| `results/problem2/problem2_summary.csv` | 问题二最终方案汇总 |
| `results/problem2/problem2_compare_with_p1.csv` | 问题一与问题二对比 |
| `results/problem2/problem2_policy_check.csv` | 绿色限行约束检查结果 |
| `results/problem3/problem3_event_results.csv` | 动态事件优化结果 |
| `results/problem3/problem3_event_routes.csv` | 动态事件调整路径 |

---

## 方法概览

### 问题一：ALNS 静态优化

问题一将配送调度建模为带有异质车队、载重与容积双容量约束、软时间窗和时变车速的车辆路径优化问题。算法流程包括：

1. 构造满足基本容量约束的初始解；
2. 使用破坏算子移除部分任务；
3. 使用修复算子重新插入任务；
4. 计算固定成本、能耗成本、碳排成本、等待成本和迟到成本；
5. 通过模拟退火接受准则保留优质解；
6. 使用多随机种子独立运行并选取最优可行方案。

### 问题二：绿色限行扩展

在问题一模型基础上，进一步加入绿色配送区限行约束：

- 新能源车辆可以在任意时间进入绿色配送区；
- 燃油车辆在 8:00--16:00 期间不得进入绿色配送区；
- 候选路径在插入和评价阶段均需进行限行可行性检查。

### 问题三：动态扰动响应

问题三以问题二方案为基准，针对动态事件采用局部重优化策略：

- 冻结已经执行或正在执行的路径状态；
- 更新受事件影响的任务集合；
- 选择受影响路径及邻近路径构成局部子问题；
- 使用 LNS--VNS 对局部路径进行低扰动修复；
- 输出剩余运营成本、节约金额和路径调整数量。

---

## 可视化示例

项目输出了多类结果图表，可在以下目录查看：

```text
figures/problem1/
figures/problem2/
figures/problem3/
figures/paper/
```

示例图包括：

- 客户空间分布图；
- 车辆路径成本分布图；
- 车辆类型使用情况图；
- 绿色限行前后成本对比图；
- 动态事件响应结果图。

---

## 论文文件

论文源文件位于：

```text
paper/main.tex
```

使用 XeLaTeX 编译：

```bash
xelatex paper/main.tex
```

---

## 后续改进方向

- 增加命令行参数配置，支持选择不同问题和随机种子；
- 将数据读取、模型求解和图表输出进一步解耦；
- 增加日志系统，记录每次运行的参数与结果；
- 补充单元测试，验证成本计算、时间窗判断和限行约束检查；
- 增加更多动态事件组合场景，提高模型的实际应用能力。

---

## License

本项目主要用于数学建模与课程学习展示。如需复用代码或结果，请注明来源。
