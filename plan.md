# 动量因子复现 - 开发计划

## 项目概述

复现东吴证券金工专题报告《成交量对动量因子的修正：日与夜的殊途同归》

## 一、数据接口设计 (01_data_prep.py)

### 1.1 架构

```
用户入口 (load_data)
      ↓
数据适配器 (DataAdapter)
      ↓
字段映射器 (FieldMapper) ← 配置化
      ↓
数据校验器 (DataValidator)
      ↓
统一输出 (UnifiedDataFrame)
```

### 1.2 统一输出格式

| 字段 | 类型 | 必填 | 说明 |
|-----|------|-----|------|
| ts_code | str | ✅ | 股票代码 |
| trade_date | str | ✅ | 交易日期 (YYYYMMDD) |
| open | float | ✅ | 开盘价 |
| high | float | ✅ | 最高价 |
| low | float | ✅ | 最低价 |
| close | float | ✅ | 收盘价 |
| volume | float | ✅ | 成交量 |
| turnover_rate | float | ❌ | 换手率 |
| turnover_rate_f | float | ❌ | 流通换手率 |
| float_share | float | ❌ | 流通股本 |
| is_st | bool | ❌ | 是否ST |
| list_date | str | ❌ | 上市日期 |

### 1.3 核心类

```python
class FieldMapper:
    """字段映射器 - 处理字段名不统一"""
    def detect_and_map(self, df)  # 自动检测+映射
    def estimate_missing(self, df)  # 估算缺失字段

class DataValidator:
    """数据校验器 - 多层校验"""
    def validate(self, df) -> ValidationReport

class DataAdapter(ABC):
    """数据适配器基类"""
    @abstractmethod
    def load_raw(self, **kwargs) -> pd.DataFrame

class DataLoader:
    """统一入口"""
    def load(self, **kwargs) -> pd.DataFrame
```

## 二、代码结构

### 2.1 模块划分

```
momentum_repro/
├── data/                    # 数据目录
│   └── raw/               # 原始数据
├── 01_data_prep.py         # 数据接口 + 清洗
├── 02_factor_build.py      # 因子构建
├── 03_backtest.py         # 回测框架
├── 04_robustness.py      # 稳健性检验
├── 05_visualize.py       # 绘图
├── src/                    # 公共模块
│   ├── __init__.py
│   ├── config.py          # 配置
│   ├── consts.py         # 常量
│   └── utils.py          # 工具函数
├── config/
│   └── field_mapping.yaml # 字段映射配置
└── output/                # 结果输出
```

## 三、加速策略

### 3.1 已验证

| 策略 | 测试结果 | 状态 |
|-----|---------|------|
| **Numba JIT** (累计收益) | 108x 加速 | ✅ 可用 |
| NumPy 向量化 | 基础优化 | ✅ 默认 |

### 3.2 优化措施

1. 向量化运算替代循环
2. Numba JIT 加速累计收益计算
3. Parquet 格式存储中间数据

## 四、执行顺序

```
Phase 1: 基础设施
├── 1.1 src/utils.py (工具函数)
├── 1.2 src/config.py (配置)
├── 1.3 01_data_prep.py (数据接口) ⭐
└── 1.4 字段映射配置

Phase 2: 因子构建
├── 2.1 02_factor_build.py

Phase 3: 回测分析
├── 3.1 03_backtest.py
├── 3.2 04_robustness.py
└── 3.3 05_visualize.py
```

## 五、数据校验规则

### L0: 必填字段
ts_code, trade_date, open, close, high, low, volume

### L1: 数据类型
数值型字段不能为字符串

### L2: 数值范围
- price > 0
- volume >= 0
- 0 <= turnover_rate <= 100

### L3: 业务逻辑
- high >= low
- high >= open, high >= close
- low <= open, low <= close

## 六、缺失字段估算

| 字段 | 估算方式 |
|-----|---------|
| auction_volume | volume * 0.1 |
| prev_close | close / (1 + return) |
| turnover_rate | volume / float_share * 100 |
| float_share | amount / close |

---

**更新**: 2026-03-29
**状态**: 编码中
