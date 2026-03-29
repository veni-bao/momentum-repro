# -*- coding: utf-8 -*-
"""
03_分组回测与IC分析
===========================
- IC分析: Spearman相关系数
- 5分组回测
- 绩效指标计算
"""

import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, List, Tuple
import warnings


# ========== 1. IC分析 ==========

def calc_ic(
    factors_df: pd.DataFrame,
    returns_df: pd.DataFrame,
    factor_col: str,
    date_col: str = 'trade_date',
    code_col: str = 'ts_code'
) -> pd.Series:
    """
    计算月度IC (Spearman相关系数)
    
    IC = SpearmanCorr(因子值_t, 下期收益_t+1)
    
    Args:
        factors_df: 因子DataFrame
        returns_df: 收益DataFrame
        factor_col: 因子列名
        date_col: 日期列名
        code_col: 股票代码列名
    
    Returns:
        月度IC序列
    """
    # 合并因子和收益
    merged = factors_df.merge(
        returns_df,
        on=[code_col, date_col]
    )
    
    if merged.empty:
        warnings.warn("合并后数据为空")
        return pd.Series()
    
    # 按月计算IC
    ic_series = []
    
    for date, group in merged.groupby(date_col):
        if len(group) < 10:
            continue
        
        valid = group[[factor_col, 'forward_return']].dropna()
        if len(valid) < 10:
            continue
        
        try:
            ic, _ = stats.spearmanr(valid[factor_col], valid['forward_return'])
            if not np.isnan(ic):
                ic_series.append({'date': date, 'IC': ic})
        except:
            continue
    
    return pd.DataFrame(ic_series).set_index('date')['IC']


def calc_ic_metrics(
    ic_series: pd.Series,
    annualize: bool = True
) -> Dict[str, float]:
    """
    计算IC相关指标
    
    Args:
        ic_series: 月度IC序列
        annualize: 是否年化
    
    Returns:
        指标字典
    """
    if ic_series.empty:
        return {
            'IC均值': np.nan,
            'IC标准差': np.nan,
            'ICIR': np.nan,
            'IC_T统计量': np.nan,
            '月度胜率': np.nan
        }
    
    ic_mean = ic_series.mean()
    ic_std = ic_series.std()
    n = len(ic_series)
    
    # ICIR
    if annualize:
        ic_ir = ic_mean / ic_std * np.sqrt(12) if ic_std > 0 else np.nan
    else:
        ic_ir = ic_mean / ic_std if ic_std > 0 else np.nan
    
    # T统计量
    ic_t = ic_mean / (ic_std / np.sqrt(n)) if ic_std > 0 else np.nan
    
    # 月度胜率
    win_rate = (ic_series > 0).mean()
    
    return {
        'IC均值': ic_mean,
        'IC标准差': ic_std,
        'ICIR': ic_ir,
        'IC_T统计量': ic_t,
        '月度胜率': win_rate
    }


# ========== 2. 分组回测 ==========

def group_returns(
    factors_df: pd.DataFrame,
    returns_df: pd.DataFrame,
    factor_col: str,
    n_groups: int = 5,
    date_col: str = 'trade_date',
    code_col: str = 'ts_code'
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    分组回测
    
    Args:
        factors_df: 因子DataFrame
        returns_df: 收益DataFrame
        factor_col: 因子列名
        n_groups: 分组数
        date_col: 日期列名
        code_col: 股票代码列名
    
    Returns:
        (分组收益, 多空对冲收益)
    """
    # 合并
    merged = factors_df.merge(
        returns_df,
        on=[code_col, date_col]
    )
    
    if merged.empty:
        warnings.warn("合并后数据为空")
        return pd.DataFrame(), pd.DataFrame()
    
    # 分组
    try:
        merged['group'] = pd.qcut(
            merged[factor_col], 
            n_groups, 
            labels=range(1, n_groups+1),
            duplicates='drop'
        )
    except:
        return pd.DataFrame(), pd.DataFrame()
    
    # 计算各组收益
    group_returns = []
    ls_returns = []
    
    for date, month_data in merged.groupby(date_col):
        group_ret = month_data.groupby('group')['forward_return'].mean()
        
        for g, ret in group_ret.items():
            group_returns.append({
                'date': date,
                'group': g,
                'return': ret
            })
        
        # 多空对冲: 做多低因子，做空高因子
        if 1 in group_ret.index and n_groups in group_ret.index:
            ls = group_ret[1] - group_ret[n_groups]
            ls_returns.append({
                'date': date,
                'return': ls
            })
    
    return pd.DataFrame(group_returns), pd.DataFrame(ls_returns)


def calc_performance_metrics(
    returns_df: pd.DataFrame,
    annualize: bool = True
) -> Dict[str, float]:
    """
    计算绩效指标
    
    Args:
        returns_df: 收益序列 (有 return 列)
        annualize: 是否年化
    
    Returns:
        绩效指标字典
    """
    if returns_df.empty:
        return {
            '年化收益率': np.nan,
            '年化波动率': np.nan,
            '信息比率': np.nan,
            '月度胜率': np.nan,
            '最大回撤': np.nan
        }
    
    rets = returns_df['return'].dropna()
    
    if len(rets) == 0:
        return {
            '年化收益率': np.nan,
            '年化波动率': np.nan,
            '信息比率': np.nan,
            '月度胜率': np.nan,
            '最大回撤': np.nan
        }
    
    # 年化收益
    annual_return = rets.mean() * 12 if annualize else rets.mean()
    
    # 年化波动
    annual_vol = rets.std() * np.sqrt(12) if annualize else rets.std()
    
    # 信息比率
    if annual_vol > 0:
        ir = annual_return / annual_vol
    else:
        ir = np.nan
    
    # 月度胜率
    win_rate = (rets > 0).mean()
    
    # 最大回撤
    cum_ret = (1 + rets).cumprod()
    running_max = cum_ret.cummax()
    drawdown = (cum_ret - running_max) / running_max
    max_dd = drawdown.min()
    
    return {
        '年化收益率': annual_return * 100,
        '年化波动率': annual_vol * 100,
        '信息比率': ir,
        '月度胜率': win_rate * 100,
        '最大回撤': max_dd * 100
    }


# ========== 3. 主函数 ==========

def run_backtest(
    factors_df: pd.DataFrame,
    price_df: pd.DataFrame,
    lookback: int = 20,
    factor_cols: List[str] = None
) -> Dict[str, Dict]:
    """
    运行完整回测
    
    Args:
        factors_df: 因子DataFrame (需包含 factor_col, ts_code, trade_date)
        price_df: 价格DataFrame (需包含 close, ts_code, trade_date)
        lookback: 回看天数
        factor_cols: 要测试的因子列表
    
    Returns:
        因子名 -> 指标字典
    """
    if factor_cols is None:
        factor_cols = [
            'OLD_Momentum', 'OLD_Intraday', 'OLD_Overnight',
            'NEW_Intraday', 'NEW_Overnight', 'NEW_Momentum'
        ]
    
    # 计算下期收益
    price_df = price_df.copy()
    price_df = price_df.sort_values(['ts_code', 'trade_date'])
    price_df['forward_return'] = price_df.groupby('ts_code')['close'].pct_change().shift(-1)
    
    print("=" * 50)
    print("回测分析")
    print("=" * 50)
    
    results = {}
    
    for factor in factor_cols:
        if factor not in factors_df.columns:
            print(f"跳过 {factor} (不存在)")
            continue
        
        print(f"\n>>> 因子: {factor}")
        
        # IC��析
        ic_series = calc_ic(factors_df, price_df, factor)
        ic_metrics = calc_ic_metrics(ic_series)
        
        # 分组回测
        group_ret, ls_ret = group_returns(factors_df, price_df, factor)
        
        if ls_ret.empty:
            print(f"  回测数据为空")
            continue
        
        perf = calc_performance_metrics(ls_ret)
        
        # 合并结果
        results[factor] = {**ic_metrics, **perf}
        
        # 打印
        print(f"  IC均值: {ic_metrics['IC均值']:.4f}")
        print(f"  ICIR: {ic_metrics['ICIR']:.2f}")
        print(f"  年化收益: {perf['年化收益率']:.2f}%")
        print(f"  信息比率: {perf['信息比率']:.2f}")
        print(f"  月度胜率: {perf['月度胜率']:.2f}%")
        print(f"  最大回撤: {perf['最大回撤']:.2f}%")
    
    return results


def main():
    """测试"""
    # 简单测试
    np.random.seed(42)
    
    dates = pd.date_range('2019-01-01', periods=30).strftime('%Y%m%d')
    stocks = ['000001', '000002', '000003']
    
    # 因子数据
    factors = []
    for s in stocks:
        for d in dates:
            factors.append({
                'ts_code': s,
                'trade_date': d,
                'OLD_Momentum': np.random.randn() * 0.1,
                'NEW_Momentum': np.random.randn() * 0.1
            })
    
    # 价格数据
    prices = []
    for s in stocks:
        for d in dates:
            prices.append({
                'ts_code': s,
                'trade_date': d,
                'close': 10 + np.random.randn() * 0.5
            })
    
    factors_df = pd.DataFrame(factors)
    prices_df = pd.DataFrame(prices)
    
    results = run_backtest(factors_df, prices_df)
    print("\n结果:")
    print(results)


if __name__ == "__main__":
    import numpy as np
    main()