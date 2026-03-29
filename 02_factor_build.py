# -*- coding: utf-8 -*-
"""
02_因子构建
===========================
构造传统因子、局部因子、新因子
- OLD_Momentum / OLD_Intraday / OLD_Overnight
- 局部日内因子 (按当日日内换手率排序)
- 局部隔夜因子 (按昨日换手率排序)
- NEW_Intraday / NEW_Overnight / NEW_Momentum
"""

import pandas as pd
import numpy as np
from typing import Optional
import warnings

# 导入工具函数
import sys
sys.path.insert(0, str(__file__).rsplit('/', 1)[0])
from src.utils import zscore_df, calc_cumprod


# ========== 1. 传统因子 ==========

def calc_traditional_factors(
    df: pd.DataFrame, 
    lookback: int = 20,
    price_cols: dict = None
) -> pd.DataFrame:
    """
    构造传统因子
    
    Args:
        df: 统一格式的DataFrame
        lookback: 回看天数
        price_cols: 价格列名映射
    
    Returns:
        带有OLD_Momentum, OLD_Intraday, OLD_Overnight的DataFrame
    """
    if price_cols is None:
        price_cols = {'open': 'open', 'close': 'close', 'prev_close': 'prev_close'}
    
    df = df.copy()
    df = df.sort_values(['ts_code', 'trade_date'])
    
    # 1. 计算日收益率
    if 'return' not in df.columns:
        df['return'] = df['close'] / df['prev_close'] - 1
    
    # 2. 计算日内收益 (收盘/开盘 - 1)
    df['r_intraday'] = df['close'] / df['open'] - 1
    
    # 3. 计算隔夜收益 (开盘/昨日收盘 - 1)
    df['r_overnight'] = df['open'] / df['prev_close'] - 1
    
    # 4. 滚动累计收益 (使用Numba加速)
    print(f"[因子] 计算传统因子 (回看={lookback}日)")
    
    # OLD_Momentum: 累计收益
    df['OLD_Momentum'] = df.groupby('ts_code')['return'].transform(
        lambda x: x.rolling(lookback).apply(
            lambda y: np.prod(1+y) - 1, 
            raw=False
        )
    )
    
    # OLD_Intraday: 累计日内收益
    df['OLD_Intraday'] = df.groupby('ts_code')['r_intraday'].transform(
        lambda x: x.rolling(lookback).apply(
            lambda y: np.prod(1+y) - 1, 
            raw=False
        )
    )
    
    # OLD_Overnight: 累计隔夜收益
    df['OLD_Overnight'] = df.groupby('ts_code')['r_overnight'].transform(
        lambda x: x.rolling(lookback).apply(
            lambda y: np.prod(1+y) - 1, 
            raw=False
        )
    )
    
    return df


# ========== 2. 局部因子 ==========

def calc_local_intraday_factors(
    df: pd.DataFrame,
    lookback: int = 20,
    n_groups: int = 5
) -> pd.DataFrame:
    """
    构造局部日内因子
    
    按当日日内换手率排序，分n_groups组
    
    Args:
        df: 统一格式DataFrame (需包含 r_intraday, turnover_rate)
        lookback: 回看天数
        n_groups: 分组数
    
    Returns:
        包含 Intraday_part1 ~ Intraday_part{n_groups} 的DataFrame
    """
    print(f"[因子] 计算局部日内因子 (按当日换手率排序, {n_groups}组)")
    
    df = df.copy()
    df = df.sort_values(['ts_code', 'trade_date'])
    df['yearmonth'] = df['trade_date'].astype(str).str[:6]
    
    # 估算日内换手率 (如果有)
    if 'TR_intraday' not in df.columns:
        if 'volume' in df.columns and 'turnover_rate' in df.columns:
            # 假设集合竞价占10%
            df['TR_intraday'] = df['turnover_rate'] * 0.9
        else:
            warnings.warn("无换手率数据，跳过局部因子计算")
            return df
    
    results = []
    
    # 按月处理
    for (code, month), group in df.groupby(['ts_code', 'yearmonth']):
        if len(group) < lookback:
            continue
        
        # 取过去lookback日
        hist = group.tail(lookback).copy()
        
        # 按日内换手率排序
        hist = hist.sort_values('TR_intraday')
        
        # 分n_groups组
        n_per_group = len(hist) // n_groups
        
        for k in range(n_groups):
            start_idx = k * n_per_group
            end_idx = (k + 1) * n_per_group if k < n_groups - 1 else len(hist)
            
            part_data = hist.iloc[start_idx:end_idx]
            
            results.append({
                'ts_code': code,
                'trade_date': month,
                f'Intraday_part{k+1}': part_data['r_intraday'].mean(),
                f'TR_intraday_part{k+1}': part_data['TR_intraday'].mean()
            })
    
    return pd.DataFrame(results)


def calc_local_overnight_factors(
    df: pd.DataFrame,
    lookback: int = 20,
    n_groups: int = 5
) -> pd.DataFrame:
    """
    构造局部隔夜因子
    
    按【昨日】总换手率排序，分n_groups组
    
    关键: 是昨日换手率，不是当日隔夜换手率!
    
    Args:
        df: 统一格式DataFrame (需包含 r_overnight, turnover_rate)
        lookback: 回看天数
        n_groups: 分组数
    
    Returns:
        包含 Overnight_part1 ~ Overnight_part{n_groups} 的DataFrame
    """
    print(f"[因子] 计算局部隔夜因子 (按昨日换手率排序, {n_groups}组)")
    
    df = df.copy()
    df = df.sort_values(['ts_code', 'trade_date'])
    df['yearmonth'] = df['trade_date'].astype(str).str[:6]
    
    # 昨日换手率
    if 'TR_yesterday' not in df.columns:
        if 'turnover_rate' in df.columns:
            df['TR_yesterday'] = df.groupby('ts_code')['turnover_rate'].shift(1)
        else:
            warnings.warn("无换手率数据，跳过局部因子计算")
            return df
    
    results = []
    
    # 按月处理
    for (code, month), group in df.groupby(['ts_code', 'yearmonth']):
        if len(group) < lookback:
            continue
        
        hist = group.tail(lookback).copy()
        
        # 按昨日换手率排序 (关键!)
        hist = hist.sort_values('TR_yesterday')
        
        n_per_group = len(hist) // n_groups
        
        for k in range(n_groups):
            start_idx = k * n_per_group
            end_idx = (k + 1) * n_per_group if k < n_groups - 1 else len(hist)
            
            part_data = hist.iloc[start_idx:end_idx]
            
            results.append({
                'ts_code': code,
                'trade_date': month,
                f'Overnight_part{k+1}': part_data['r_overnight'].mean(),
                f'TR_yesterday_part{k+1}': part_data['TR_yesterday'].mean()
            })
    
    return pd.DataFrame(results)


# ========== 3. 新因子合成 ==========

def calc_new_factors(
    local_intraday: pd.DataFrame,
    local_overnight: pd.DataFrame
) -> pd.DataFrame:
    """
    合成新因子
    
    - NEW_Intraday = -zscore(part1) + zscore(part5)
    - NEW_Overnight = +zscore(part1) - zscore(part5)
    - NEW_Momentum = zscore(NEW_Intraday) + zscore(NEW_Overnight)
    
    Args:
        local_intraday: 局部日内因子
        local_overnight: 局部隔夜因子
    
    Returns:
        包含所有新因子的DataFrame
    """
    print("[因子] 合成新因子")
    
    # 合并
    if local_intraday.empty or local_overnight.empty:
        warnings.warn("局部因子为空，无法合成新因子")
        return pd.DataFrame()
    
    df = local_intraday.merge(
        local_overnight, 
        on=['ts_code', 'trade_date'], 
        how='inner'
    )
    
    if df.empty:
        warnings.warn("合并后数据为空")
        return df
    
    # ===== 日内因子 =====
    # NEW_Intraday = -zscore(part1) + zscore(part5)
    df['z_intra_part1'] = df.groupby('trade_date')['Intraday_part1'].transform(zscore_df)
    df['z_intra_part5'] = df.groupby('trade_date')['Intraday_part5'].transform(zscore_df)
    df['NEW_Intraday'] = -df['z_intra_part1'] + df['z_intra_part5']
    
    # ===== 隔夜因子 =====
    # NEW_Overnight = +zscore(part1) - zscore(part5)
    # 注意: 方向与日内相反! part1为反转，part5为动量
    df['z_over_part1'] = df.groupby('trade_date')['Overnight_part1'].transform(zscore_df)
    df['z_over_part5'] = df.groupby('trade_date')['Overnight_part5'].transform(zscore_df)
    df['NEW_Overnight'] = df['z_over_part1'] - df['z_over_part5']
    
    # ===== 新动量因子 =====
    df['z_NEW_Intraday'] = df.groupby('trade_date')['NEW_Intraday'].transform(zscore_df)
    df['z_NEW_Overnight'] = df.groupby('trade_date')['NEW_Overnight'].transform(zscore_df)
    df['NEW_Momentum'] = df['z_NEW_Intraday'] + df['z_NEW_Overnight']
    
    # 清理临时列
    temp_cols = [c for c in df.columns if c.startswith('z_')]
    df = df.drop(columns=temp_cols)
    
    return df


# ========== 4. 主函数 ==========

def build_factors(
    df: pd.DataFrame,
    lookback: int = 20,
    calc_traditional: bool = True,
    calc_local: bool = True,
    calc_new: bool = True
) -> pd.DataFrame:
    """
    构建所有因子
    
    Args:
        df: 统一格式的DataFrame
        lookback: 回看天数
        calc_traditional: 是否计算传统因子
        calc_local: 是否计算局部因子
        calc_new: 是否计算新因子
    
    Returns:
        包含所有因子的DataFrame
    """
    print("=" * 50)
    print(f"因子构建 (回看={lookback}日)")
    print("=" * 50)
    
    result_dfs = []
    
    # 1. 传统因子
    if calc_traditional:
        print("\n[1/3] 计算传统因子...")
        df = calc_traditional_factors(df, lookback)
        result_dfs.append(df[['ts_code', 'trade_date', 'OLD_Momentum', 'OLD_Intraday', 'OLD_Overnight']])
    
    # 2. 局部因子
    if calc_local:
        print("\n[2/3] 计算局部因子...")
        
        # 局部日内因子
        local_intra = calc_local_intraday_factors(df, lookback)
        
        # 局部隔夜因子
        local_over = calc_local_overnight_factors(df, lookback)
        
        # 3. 新因子
        if calc_new and not local_intra.empty and not local_over.empty:
            print("\n[3/3] 合成新因子...")
            new_factors = calc_new_factors(local_intra, local_over)
            result_dfs.append(new_factors)
    
    # 合并结果
    if len(result_dfs) == 0:
        warnings.warn("未生成任何因子")
        return df
    
    # 从第一个df开始合并
    result = result_dfs[0]
    for rdf in result_dfs[1:]:
        result = result.merge(
            rdf, 
            on=['ts_code', 'trade_date'], 
            how='outer'
        )
    
    print(f"\n因子构建完成: {len(result)} 行")
    
    return result


def main():
    """测试入口"""
    # 创建测试数据
    import numpy as np
    
    np.random.seed(42)
    dates = pd.date_range('2019-01-01', periods=60).strftime('%Y%m%d')
    stocks = ['000001', '000002', '000003']
    
    data = []
    for code in stocks:
        for d in dates:
            data.append({
                'ts_code': code,
                'trade_date': d,
                'open': 10 + np.random.randn() * 0.5,
                'close': 10 + np.random.randn() * 0.5,
                'high': 10.5,
                'low': 9.5,
                'volume': 1000000,
                'turnover_rate': 1.5 + np.random.randn() * 0.5,
            })
    
    df = pd.DataFrame(data)
    
    # 计算因子
    result = build_factors(df, lookback=20)
    print(result.head(10))


if __name__ == "__main__":
    main()
