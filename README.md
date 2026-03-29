# 动量因子成交量修正 - 复现项目

> 量化交易研报复现 - 东吴证券金工专题报告 (2019年9月)

## 研报概述

本项目复现东吴金工专题报告《成交量对动量因子的修正：日与夜的殊途同归》。

核心发现：
- **日内价量**：高换手率强化日内动量信号（锦上添花）
- **隔夜价量**：昨日换手率影响隔夜收益方向（雪中送炭）

## 项目结构

```
momentum_repro/
├── data/                    # 原始数据 (parquet格式)
│   └── raw_data.parquet    # 原始行情数据
│   └── cleaned_data.parquet # 清洗后数据
├── 01_data_prep.py         # 数据清洗与预处理
├── 02_factor_build.py       # 因子构造
├── 03_backtest.py           # 分组回测与IC分析
├── 04_robustness.py        # 稳健性检验
├── 05_visualize.py         # 绘图
└── output/                  # 结果输出
    ├── factors.parquet      # 因子数据
    ├── backtest_results.csv # 回测结果
    └── *.png               # 图表
```

## 数据需求

| 字段 | 说明 |
|-----|------|
| ts_code | 股票代码 |
| trade_date | 交易日期 |
| open/high/low/close | OHLC价格 |
| volume | 成交量 |
| turnover_rate | 换手率 |
| float_share | 流通股本 |
| is_st | 是否ST |
| list_date | 上市日期 |

**关键**: 需要集合竞价成交量(auction_volume)，如无则用总成交量×10%估算

## 快速开始

### 1. 准备数据

```python
# 方式1: Tushare (需要token)
import tushare as ts
pro = ts.pro_api('YOUR_TOKEN')

# 方式2: AKShare (免费)
import akshare as ak
```

### 2. 运行流程

```bash
# Step 1: 数据预处理
python 01_data_prep.py

# Step 2: 因子构建
python 02_factor_build.py

# Step 3: 回测分析
python 03_backtest.py

# Step 4: 稳健性检验
python 04_robustness.py

# Step 5: 绘图
python 05_visualize.py
```

## 核心公式

### 收益定义
- 日内收益: `r_t = close_t / open_t - 1`
- 隔夜收益: `g_t = open_t / close_{t-1} - 1`

### 新因子合成
```python
# 日内因子
NEW_Intraday = -zscore(part1) + zscore(part5)

# 隔夜因子 (方向相反!)
NEW_Overnight = +zscore(part1) - zscore(part5)

# 合成
NEW_Momentum = zscore(NEW_Intraday) + zscore(NEW_Overnight)
```

## 预期结果

| 因子 | 年化收益 | IR | 月度胜率 | 最大回撤 |
|-----|---------|-----|---------|----------|
| 传统动量 | 19.71% | 1.04 | 66.15% | 15.89% |
| 新日内 | 13.71% | 1.83 | 80.00% | 8.37% |
| 新隔夜 | 13.97% | 2.31 | 78.46% | 5.14% |
| **新动量** | **18.65%** | **2.89** | **86.15%** | **6.33%** |

## 依赖

```txt
pandas >= 1.5
numpy >= 1.23
scipy >= 1.9
statsmodels >= 0.14
matplotlib >= 3.6
tushare / akshare
```

## 参考

- 原始研报: 东吴证券金融工程专题报告 (2019年9月)
- 作者: 高子剑, 沈芷琦
