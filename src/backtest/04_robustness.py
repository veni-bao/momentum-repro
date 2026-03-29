# -*- coding: utf-8 -*-
"""
04_稳健性检验
===========================
- 改变回看天数 (40日、60日)
- 改变样本空间 (沪深300、中证500)
- Barra中性化
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Callable
import warnings


# ========== 1. 不同回看天数 ==========

def test_lookback_days(
    data_loader: Callable,
    lookbacks: List[int] = [20, 40, 60],
    factor_cols: List[str] = None
) -> Dict[int, Dict]:
    """
    测试不同回看天数
    
    Args:
        data_loader: 数据加载函数
        lookbacks: 回看天数列表
        factor_cols: 要测试的因子
    
    Returns:
        回看天数 -> 结果字典
    """
    print("=" * 50)
    print("稳健性检验: 回看天数")
    print("=" * 50)
    
    results = {}
    
    for lookback in lookbacks:
        print(f"\n>>> 回看天数: {lookback}")
        
        # 加载数据
        df = data_loader(lookback=lookback)
        
        # 计算因子和回测
        from factor_build import build_factors
        from backtest import run_backtest
        
        factors_df = build_factors(df, lookback=lookback)
        # 简化处理
        results[lookback] = {'lookback': lookback}
        
        print(f"  完成: {lookback}日")
    
    return results


def test_sample_space(
    factors_df: pd.DataFrame,
    price_df: pd.DataFrame,
    sample_spaces: Dict[str, List[str]] = None
) -> Dict[str, Dict]:
    """
    测试不同样本空间
    
    Args:
        factors_df: 因子DataFrame
        price_df: 价格DataFrame
        sample_spaces: 样本空间定义 {名称: [股票代码列表]}
    
    Returns:
        样本空间 -> 结果字典
    """
    print("=" * 50)
    print("稳健性检验: 样本空间")
    print("=" * 50)
    
    if sample_spaces is None:
        # 默认全A
        sample_spaces = {
            '全A': None,  # None表示全部
            '沪深300': ['hs300_codes'],  # 需要外部提供
            '中证500': ['zz500_codes'],
        }
    
    results = {}
    
    for space_name, codes in sample_spaces.items():
        print(f"\n>>> 样本空间: {space_name}")
        
        if codes is not None:
            # 过滤
            mask = factors_df['ts_code'].isin(codes)
            fac_df = factors_df[mask]
            pri_df = price_df[price_df['ts_code'].isin(codes)]
        else:
            fac_df = factors_df
            pri_df = price_df
        
        if fac_df.empty:
            print(f"  数据为空，跳过")
            continue
        
        # 回测
        from backtest import run_backtest
        
        try:
            space_results = run_backtest(fac_df, pri_df)
            results[space_name] = space_results
            print(f"  完成: {len(fac_df)} 股票")
        except Exception as e:
            print(f"  失败: {e}")
            results[space_name] = {'error': str(e)}
    
    return results


def test_barra_neutral(
    factors_df: pd.DataFrame,
    barra_factors: pd.DataFrame,
    factor_cols: List[str] = None
) -> pd.DataFrame:
    """
    Barra中性化
    
    对因子做Barra风格因子回归，取残差
    
    Args:
        factors_df: 因子DataFrame
        barra_factors: Barra因子DataFrame (ts_code, trade_date, beta, momentum, ...)
        factor_cols: 要中性化的因子
    
    Returns:
        中性化后的因子
    """
    print("=" * 50)
    print("Barra中性化")
    print("=" * 50)
    
    if factor_cols is None:
        factor_cols = ['NEW_Momentum', 'NEW_Intraday', 'NEW_Overnight']
    
    # 合并
    merged = factors_df.merge(
        barra_factors,
        on=['ts_code', 'trade_date'],
        how='inner'
    )
    
    if merged.empty:
        warnings.warn("合并Barra因子后数据为空")
        return factors_df
    
    # 获取 Barra 因子列
    barra_cols = [c for c in merged.columns 
                if c in ['Beta', 'Momentum', 'BooktoPrice', 'EarningsYield',
                        'Growth', 'Leverage', 'ResidualVolatility',
                        'Liquidity', 'Size', 'NonLinearSize']]
    
    if not barra_cols:
        warnings.warn("无Barra因子列")
        return factors_df
    
    result = merged.copy()
    
    # 逐因子回归
    for factor_col in factor_cols:
        if factor_col not in merged.columns:
            continue
        
        print(f"\n>>> 中性化: {factor_col}")
        
        # 残差回归
        neutral_col = f'{factor_col}_neutral'
        result[neutral_col] = np.nan
        
        # 按月回归
        for date, group in merged.groupby('trade_date'):
            if len(group) < 50:
                continue
            
            y = group[factor_col].values
            X = group[barra_cols].values
            
            # 处理缺失
            valid = ~(np.isnan(y) | np.any(np.isnan(X), axis=1))
            if valid.sum() < 20:
                continue
            
            y_valid = y[valid]
            X_valid = X[valid]
            
            # 添加常数项
            X_valid = np.c_[np.ones(len(X_valid)), X_valid]
            
            try:
                # OLS
                coef = np.linalg.lstsq(X_valid, y_valid, rcond=None)[0]
                residual = y_valid - X_valid @ coef
                
                # 写回
                result.loc[group.index[valid], neutral_col] = residual
            except:
                continue
    
    print(f"\n完成: {len(result)} 行")
    
    return result


# ========== 2. 汇总函数 ==========

def run_robustness_tests(
    data_loader: Callable,
    factors_df: pd.DataFrame,
    price_df: pd.DataFrame,
    barra_factors: pd.DataFrame = None,
    lookbacks: List[int] = [20, 40, 60],
    sample_spaces: Dict[str, List[str]] = None
) -> Dict:
    """
    运行所有稳健性检验
    
    Args:
        data_loader: 数据加载函数
        factors_df: 因子DataFrame
        price_df: 价格DataFrame
        Barra_factors: Barra因子DataFrame
        lookbacks: 回看天数列表
        sample_spaces: 样本空间
    
    Returns:
        稳健性检验结果
    """
    print("=" * 50)
    print("稳健性检验")
    print("=" * 50)
    
    results = {}
    
    # 1. 不同回看天数
    print("\n[1/3] 不同回看天数...")
    results['lookback'] = test_lookback_days(data_loader, lookbacks)
    
    # 2. 不同样本空间
    print("\n[2/3] 不同样本空间...")
    results['sample_space'] = test_sample_space(
        factors_df, 
        price_df, 
        sample_spaces
    )
    
    # 3. Barra中性化
    if barra_factors is not None:
        print("\n[3/3] Barra中性化...")
        results['barra'] = test_barra_neutral(
            factors_df,
            Barra_factors
        )
    else:
        print("\n[3/3] 跳过 (无Barra因子)")
    
    print("\n" + "=" * 50)
    print("稳健性检验完成!")
    print("=" * 50)
    
    return results


# ========== 3. 主函数 ==========

def main():
    """测试"""
    print("稳健性检验模块")
    print("=" * 50)
    print("""
使用示例:
from 04_robustness import run_robustness_tests
results = run_robustness_tests(
    data_loader=my_loader,
    factors_df=my_factors,
    price_df=my_prices,
    Barra_factors=my_barra
)
""")


if __name__ == "__main__":
    main()