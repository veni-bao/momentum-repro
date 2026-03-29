# 动量因子复现项目

> 复现东吴证券金工专题报告《成交量对动量因子的修正：日与夜的殊途同归》(2019年9月)

## 项目概述

本项目复现东吴证券金融工程专题报告中关于动量因子的量化研究，通过引入成交量信息来改进传统动量因子的选股能力。

### 核心发现

- **日内价量**：高换手率强化日内动量信号（锦上添花）
- **隔夜价量**：昨日换手率影响隔夜收益方向（雪中送炭）
- **最终效果**：新动量因子年化ICIR=-3.04，月度胜率86.15%，最大回撤仅6.33%

## 项目结构

```
momentum_repro/
├── data/                     # 数据目录
│   ├── mock/                # 模拟数据（自动生成）
│   └── input/              # 真实数据输入目录
├── output/                  # 结果输出
│   ├── backtest_results.txt
│   ├── factor_comparison.png
│   ├── ic_comparison.png
│   └── group_net_value.png
├── src/                     # 源代码
│   ├── utils.py           # 工具函数
│   ├── data/              # 数据模块
│   │   └── 01_data_prep.py
│   ├── factors/           # 因子模块
│   │   └── 02_factor_build.py
│   ├── backtest/          # 回测模块
│   │   ├── 03_backtest.py
│   │   ├── 04_robustness.py
│   │   └── 05_visualize.py
│   └── main.py            # 主程序
├── pyproject.toml          # uv环境配置
└── README.md
```

## 快速开始

```bash
# 安装依赖
uv sync

# 运行分析
python -m src.main
```

或使用PowerShell脚本:
```powershell
.\run_tests.ps1
```

## 输出结果

运行后会在 `output/` 目录生成:

- `backtest_results.txt` - 文本结果
- `factor_comparison.png` - 因子对比表格
- `ic_comparison.png` - IC对比柱状图
- `group_net_value.png` - 5分组净值走势图

## 核心公式

### 收益率定义

- 日内收益: $r_t = \frac{close_t}{open_t} - 1$
- 隔夜收益: $g_t = \frac{open_t}{close_{t-1}} - 1$

### 传统因子

$$OLD\_Momentum = \prod_{t=1}^{N}(1+r_t+g_t) - 1$$

### 新因子合成

$$NEW\_Intraday = -zscore(Part_1) + zscore(Part_5)$$

$$NEW\_Overnight = +zscore(Part_1) - zscore(Part_5)$$

$$NEW\_Momentum = zscore(NEW\_Intraday) + zscore(NEW\_Overnight)$$

## 数据要求

| 字段 | 类型 | 必填 |
|-----|------|-----|
| ts_code | str | ✅ |
| trade_date | str | ✅ |
| open/close/high/low | float | ✅ |
| volume | float | ✅ |
| turnover_rate | float | ❌ |

## 依赖

- pandas >= 1.5.0
- numpy >= 1.23.0
- scipy >= 1.9.0
- matplotlib >= 3.6.0
- numba >= 0.56.0
- pyyaml >= 6.0

## 参考

- 原始研报: 东吴证券金融工程专题报告 (2019年9月)
- 作者: 高子剑, 沈芷琦