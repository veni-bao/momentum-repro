# 动量因子复现 - 开发计划

## 项目概述

复现东吴证券金工专题报告《成交量对动量因子的修正：日与夜的殊途同归》

## 一、数据接口设计

### 1.1 统一数据接口 (01_data_prep.py)

```python
class DataSource(ABC):
    """数据源抽象基类"""
    
    @abstractmethod
    def get_daily(self, start_date: str, end_date: str) -> pd.DataFrame:
        """获取日频行情数据"""
        pass
    
    @abstractmethod
    def get_basic_info(self) -> pd.DataFrame:
        """获取股票基本信息 (ST、上市日期等)"""
        pass

class TushareSource(DataSource):
    """Tushare数据源"""
    def __init__(self, token: str): ...

class AKShareSource(DataSource):
    """AKShare数据源"""
    ...

class LocalSource(DataSource):
    """本地数据源"""
    def __init__(self, data_dir: str): ...
```

### 1.2 数据格式

| 字段 | 类型 | 说明 |
|-----|------|------|
| ts_code | str | 股票代码 |
| trade_date | str | 交易日期 (YYYYMMDD) |
| open | float | 开盘价 |
| high | float | 最高价 |
| low | float | 最低价 |
| close | float | 收盘价 |
| volume | float | 成交量 |
| turnover_rate | float | 换手率(%) |
| turnover_rate_f | float | 流通换手率(%) |
| float_share | float | 流通股本 |
| is_st | bool | 是否ST |
| list_date | str | 上市日期 |

### 1.3 数据加载方法

```python
def load_unified_data(source: DataSource, start: str, end: str) -> pd.DataFrame:
    """
    统一数据加载接口
    1. 调用 source.get_daily() 获取原始数据
    2. 统一字段名称
    3. 计算衍生字段 (收益率、换手率等)
    4. 处理停牌、ST等
    5. 返回标准化DataFrame
    """
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
└── output/                # 结果输出
```

### 2.2 核心类/函数

**01_data_prep.py:**
- `DataSource` - 抽象基类
- `TushareSource` - Tushare实现
- `AKShareSource` - AKShare实现
- `load_unified_data()` - 统一加载入口
- `preprocess()` - 数据预处理

**02_factor_build.py:**
- `TraditionalFactors` - 传统因子类
- `LocalIntradayFactors` - 局部日内因子
- `LocalOvernightFactors` - 局部隔夜因子
- `NewFactors` - 新因子合成

**03_backtest.py:**
- `ICAnalyzer` - IC分析
- `BacktestEngine` - 回测引擎
- `PerformanceMetrics` - 绩效指标

## 三、加速策略

### 3.1 数据处理加速

| 策略 | 预期提升 | 实现难度 |
|-----|---------|----------|
| **向量化运算** | 3-5x | 低 |
| **Polars替代Pandas** | 2-3x | 中 |
| **Numba JIT编译** | 2-10x | 中 |
| **并行处理 (multiprocessing)** | 2-4x | 中 |
| **Dask分布式** | 5-10x | 高 |
| **Numba + Polars组合** | 5-15x | 高 |

### 3.2 具体优化措施

1. **避免循环**
   ```python
   # 慢
   for i in range(len(df)):
       df.loc[i, 'new_col'] = df.loc[i, 'a'] + df.loc[i, 'b']
   
   # 快
   df['new_col'] = df['a'] + df['b']
   ```

2. **使用Polars**
   ```python
   import polars as pl
   df = pl.scan_csv("data.csv")  # 惰性加载
   df = df.filter(pl.col("volume") > 0)
   df = df.with_columns([
       (pl.col("close") / pl.col("open") - 1).alias("return")
   ])
   ```

3. **Numba加速**
   ```python
   from numba import jit
   
   @jit(nopython=True)
   def calc_cum_ret(returns):
       result = np.empty(len(returns))
       prod = 1.0
       for i in range(len(returns)):
           prod *= (1 + returns[i])
           result[i] = prod - 1
       return result
   ```

4. **并行因子计算**
   ```python
   from concurrent.futures import ProcessPoolExecutor
   
   def calc_factors_parallel(stocks_df):
       with ProcessPoolExecutor(max_workers=8) as executor:
           results = executor.map(calc_single_stock, stocks_df)
       return pd.concat(results)
   ```

5. **内存优化**
   - 使用 `category` 类型存储股票代码
   - 使用 `float32` 替代 `float64`
   - 按需加载列 (`usecols`)

### 3.3 缓存策略

- 中间结果缓存 (joblib, pickle)
- Parquet格式存储中间数据
- 只重新计算变更部分

## 四、执行顺序

```
Phase 1: 基础设施
├── 1.1 完成数据接口设计 (plan.md) ✅
├── 1.2 实现 DataSource 基类
├── 1.3 实现 Tushare/AKShare/本地加载器
└── 1.4 统一数据格式转换

Phase 2: 因子构建
├── 2.1 传统因子 (OLD_Momentum等)
├── 2.2 局部日内因子 (按换手率排序)
├── 2.3 局部隔夜因子 (按昨日换手率排序)
└── 2.4 新因子合成

Phase 3: 回测分析
├── 3.1 IC分析
├── 3.2 分组回测
└── 3.3 绩效评估

Phase 4: 优化加速
├── 4.1 性能分析 (cProfile)
├── 4.2 Polars迁移
└── 4.3 Numba优化

Phase 5: 稳健性检验
├── 5.1 不同回看天数
├── 5.2 不同样本空间
└── 5.3 Barra中性化
```

## 五、预期产出

| 指标 | 目标值 | 实际值 |
|-----|-------|-------|
| 年化ICIR | -3.04 | ? |
| 信息比率 | 2.89 | ? |
| 月度胜率 | 86.15% | ? |
| 最大回撤 | 6.33% | ? |

## 六、风险与应对

| 风险 | 影响 | 应对方案 |
|-----|-----|---------|
| 数据缺失 | 因子无法计算 | 备用数据源、估算 |
| 性能不足 | 运行时间过长 | 多进程、Numba |
| 结果不符 | 复现失败 | 逐项对比、调整参数 |

---

**计划制定**: 2026-03-29
**等待批准后开始编码**
