# -*- coding: utf-8 -*-
"""
02_因子构造
===========================
构造传统因子、局部因子、新因子
- OLD_Momentum / OLD_Intraday / OLD_Overnight
- 局部日内因子 (按当日日内换手率排序)
- 局部隔夜因子 (按昨日换手率排序)
- NEW_Intraday / NEW_Overnight / NEW_Momentum
"""

import pandas as pd
import numpy as np
from pathlib import Path

# ============== 配置 ==============
DATA_PATH = Path(__file__).parent / "data"
OUTPUT_PATH = Path(__file__).parent / "output"
LOOKBACK = 20  # 回看天数

# ============== 传统因子 ==============
def calc_traditional_factors(df, lookback=20):
    """
    构造传统因子
    - OLD_Momentum: 过去N日累计收益
    - OLD_Intraday: 过去N日累计日内收益
    - OLD_Overnight: 过去N日累计隔夜收益
    """
    print(f"\n[传统因子] 回看天数={lookback}")
    
    df = df.sort_values(['ts_code', 'trade_date'])
    
    # 累计收益 (使用滚动窗口)
    for col, name in [('return', 'Momentum'), 
                      ('r_intraday', 'Intraday'), 
                      ('r_overnight', 'Overnight')]:
        if col == 'return':
            df['return'] = df['close'] / df.groupby('ts_code')['close'].shift(1) - 1
        
        # 滚动累计收益
        old_col = f'OLD_{name}'
        df[old_col] = df.groupby('ts_code')[col].transform(
            lambda x: x.rolling(lookback).apply(lambda y: np.prod(1+y) - 1, raw=False)
        )
    
    return df


# ============== 局部因子 ==============
def calc_local_intraday_factors(df, lookback=20):
    """
    构造局部日内因子
    1. 每月末，对每只股票过去N个交易日的日内收益
    2. 按当日日内换手率升序排序
    3. 等分为5组，计算组内均值
    """
    print(f"\n[局部日内因子] 按当日日内换手率排序")
    
    df = df.sort_values(['ts_code', 'trade_date'])
    
    # 每月末
    df['yearmonth'] = df['trade_date'].astype(str).str[:6]
    
    results = []
    
    for (code, month), group in df.groupby(['ts_code', 'yearmonth']):
        if len(group) < lookback:
            continue
            
        # 取过去lookback日
        hist = group.tail(lookback).copy()
        
        # 按日内换手率排序
        hist = hist.sort_values('TR_intraday')
        
        # 等分5组
        n = len(hist) // 5
        for k in range(5):
            start_idx = k * n
            end_idx = (k + 1) * n if k < 4 else len(hist)
            
            part_data = hist.iloc[start_idx:end_idx]
            mean_ret = part_data['r_intraday'].mean()
            
            results.append({
                'ts_code': code,
                'trade_date': month,
                f'Intraday_part{k+1}': mean_ret,
                f'TR_intraday_part{k+1}': part_data['TR_intraday'].mean()
            })
    
    result_df = pd.DataFrame(results)
    return result_df


def calc_local_overnight_factors(df, lookback=20):
    """
    构造局部隔夜因子
    1. 每月末，对每只股票过去N个交易日的隔夜收益
    2. 按【昨日】总换手率升序排序 (不是当日隔夜换手率!)
    3. 等分为5组，计算组内均值
    """
    print(f"\n[局部隔夜因子] 按昨日换手率排序")
    
    df = df.sort_values(['ts_code', 'trade_date'])
    df['yearmonth'] = df['trade_date'].astype(str).str[:6]
    
    results = []
    
    for (code, month), group in df.groupby(['ts_code', 'yearmonth']):
        if len(group) < lookback:
            continue
            
        hist = group.tail(lookback).copy()
        
        # 按昨日换手率排序 (关键区别!)
        hist = hist.sort_values('TR_yesterday')
        
        n = len(hist) // 5
        for k in range(5):
            start_idx = k * n
            end_idx = (k + 1) * n if k < 4 else len(hist)
            
            part_data = hist.iloc[start_idx:end_idx]
            mean_ret = part_data['r_overnight'].mean()
            
            results.append({
                'ts_code': code,
                'trade_date': month,
                f'Overnight_part{k+1}': mean_ret,
                f'TR_yesterday_part{k+1}': part_data['TR_yesterday'].mean()
            })
    
    result_df = pd.DataFrame(results)
    return result_df


# ============== 新因子合成 ==============
def zscore(x):
    """横截面z-score标准化"""
    return (x - x.mean()) / x.std()


def calc_new_factors(local_intraday, local_overnight):
    """
    合成新因子
    - NEW_Intraday = -zscore(part1) + zscore(part5)
    - NEW_Overnight = +zscore(part1) - zscore(part5)  # 注意方向相反
    - NEW_Momentum = zscore(NEW_Intraday) + zscore(NEW_Overnight)
    """
    print("\n[新因子合成]")
    
    # 合并
    df = local_intraday.merge(local_overnight, on=['ts_code', 'trade_date'])
    
    # 日内因子
    df['z_part1_intra'] = df.groupby('trade_date')['Intraday_part1'].transform(zscore)
    df['z_part5_intra'] = df.groupby('trade_date')['Intraday_part5'].transform(zscore)
    df['NEW_Intraday'] = -df['z_part1_intra'] + df['z_part5_intra']
    
    # 隔夜因子 (方向相反)
    df['z_part1_over'] = df.groupby('trade_date')['Overnight_part1'].transform(zscore)
    df['z_part5_over'] = df.groupby('trade_date')['Overnight_part5'].transform(zscore)
    df['NEW_Overnight'] = df['z_part1_over'] - df['z_part5_over']
    
    # 合成新动量因子
    df['z_NEW_Intraday'] = df.groupby('trade_date')['NEW_Intraday'].transform(zscore)
    df['z_NEW_Overnight'] = df.groupby('trade_date')['NEW_Overnight'].transform(zscore)
    df['NEW_Momentum'] = df['z_NEW_Intraday'] + df['z_NEW_Overnight']
    
    return df


# ============== 主函数 ==============
def main():
    print("=" * 50)
    print("Step 2: 因子构造")
    print("=" * 50)
    
    # 加载清洗后的数据
    data_file = DATA_PATH / "cleaned_data.parquet"
    if not data_file.exists():
        print(f"错误: 未找到数据文件 {data_file}")
        print("请先运行 01_data_prep.py")
        return
    
    df = pd.read_parquet(data_file)
    print(f"加载数据: {len(df):,} 行")
    
    # 1. 传统因子
    df = calc_traditional_factors(df, LOOKBACK)
    
    # 2. 局部日内因子
    local_intraday = calc_local_intraday_factors(df, LOOKBACK)
    
    # 3. 局部隔夜因子
    local_overnight = calc_local_overnight_factors(df, LOOKBACK)
    
    # 4. 新因子
    factor_df = calc_new_factors(local_intraday, local_overnight)
    
    # 保存
    output_file = OUTPUT_PATH / "factors.parquet"
    factor_df.to_parquet(output_file, index=False)
    print(f"\n保存到: {output_file}")
    print(f"因子数据: {len(factor_df):,} 行")
    
    return factor_df


if __name__ == "__main__":
    main()
