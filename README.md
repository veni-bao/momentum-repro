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
│   └── mock/                 # 模拟数据生成
│       └── test_run.py
├── output/                   # 结果输出
├── src/                      # 源代码
│   ├── utils.py             # 工具函数 (含Numba加速)
│   ├── data/                # 数据模块
│   │   └── 01_data_prep.py # 数据接口
│   └── factors/             # 因子模块
│       └── 02_factor_build.py # 因子构建
├── config/                   # 配置
├── pyproject.toml            # uv环境配置
└── README.md
```

## 环境配置

```bash
# 使用uv安装依赖
uv sync

# 运行测试
python -m data.mock.test_run
```

或使用提供的脚本:

```powershell
.\run_tests.ps1 -All
```

## 核心公式

### 收益率定义

- 日内收益: $r_t = \frac{close_t}{open_t} - 1$
- 隔夜收益: $g_t = \frac{open_t}{close_{t-1}} - 1$

### 传统因子

$$OLD\_Momentum = \prod_{t=1}^{N}(1+r_t+g_t) - 1$$

### 局部因子

- 局部日内因子：按当日换手率排序分组
- 局部隔夜因子：按昨日换手率排序分组

### 新因子合成

$$NEW\_Intraday = -zscore(Part_1) + zscore(Part_5)$$

$$NEW\_Overnight = +zscore(Part_1) - zscore(Part_5)$$

$$NEW\_Momentum = zscore(NEW\_Intraday) + zscore(NEW\_Overnight)$$

## 数据要求

| 字段 | 类型 | 必填 | 说明 |
|-----|------|-----|------|
| ts_code | str | ✅ | 股票代码 |
| trade_date | str | ✅ | 交易日期 (YYYYMMDD) |
| open | float | ✅ | 开盘价 |
| close | float | ✅ | 收盘价 |
| high | float | ✅ | 最高价 |
| low | float | ✅ | 最低价 |
| volume | float | ✅ | 成交量 |
| turnover_rate | float | ❌ | 换手率 |
| prev_close | float | ❌ | 昨日收盘价 |

## 性能指标

| 指标 | 说明 |
|-----|------|
| IC均值 | Spearman相关系数均值 |
| 年化ICIR | IC均值/IC标准差×√12 |
| 年化收益率 | 多空对冲年化收益 |
| 信息比率(IR) | 年化收益/年化波动 |
| 月度胜率 | 对冲收益>0的月份占比 |
| 最大回撤 | 净值最大回撤 |

## 依赖

```toml
dependencies = [
    "pandas>=1.5.0",
    "numpy>=1.23.0",
    "scipy>=1.9.0",
    "matplotlib>=3.6.0",
    "seaborn>=0.12.0",
    "numba>=0.56.0",
    "pyyaml>=6.0",
]
```

## 参考

- 原始研报: 东吴证券金融工程专题报告 (2019年9月)
- 作者: 高子剑, 沈芷琦