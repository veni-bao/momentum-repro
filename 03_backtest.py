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
from pathlib import Path
from collections import defaultdict

# ============== 配置 ==============
DATA_PATH = Path(__file__).parent / "data"
OUTPUT_PATH = Path(__file__).parent / "output"

# ============== IC分析 ==============
def calc_ic(factor_df, price_df, factor_col, return_col='next_return'):
    """
    计算月度IC (Spearman相关系数)
    IC = SpearmanCorr(因子值_t, 下期收益_t+1)
    """
    # 合并因子和收益
    merged = factor_df.merge(price_df, on=['ts_code', 'trade_date'])
    
    # 按月计算IC
    ic_series = []
    for month, group in merged.groupby('trade_date'):
        if len(group) < 10:
            continue
            
        # 过滤NaN
        valid = group[[factor_col, return_col]].dropna()
        if len(valid) < 10:
            continue
            
        # Spearman相关
        ic, _ = stats.spearmanr(valid[factor_col], valid[return_col])
        if not np.isnan(ic):
            ic_series.append({'trade_date': month, 'IC': ic})
    
    return pd.DataFrame(ic_series)


def calc_ic_metrics(ic_df):
    """
    计算IC相关指标
    - IC均值
    - IC标准差
    - 年化ICIR = mean(IC) / std(IC) * sqrt(12)
    - IC的T统计量
    """
    ic_mean = ic_df['IC'].mean()
    ic_std = ic_df['IC'].std()
    ic_ir = ic_mean / ic_std * np.sqrt(12) if ic_std > 0 else 0
    
    # T统计量
    n = len(ic_df)
    ic_t = ic_mean / (ic_std / np.sqrt(n)) if ic_std > 0 else 0
    
    return {
        'IC均值': ic_mean,
        'IC标准差': ic_std,
        '年化ICIR': ic_ir,
        'IC_T统计量': ic_t,
        '月度胜率': (ic_df['IC'] > 0).mean()
    }


# ============== 5分组回测 ==============
def calc_group_returns(factor_df, price_df, factor_col, n_groups=5):
    """
    5分组回测
    每月末按因子值分组，次月持有
    """
    results = []
    
    for month, group in factor_df.groupby('trade_date'):
        # 获取下月收益
        next_month = str(int(month) + 1)
        if next_month not in price_df['yearmonth'].values:
            continue
            
        # 合并
        merged = group.merge(
            price_df[price_df['yearmonth'] == next_month],
            on='ts_code',
            suffixes=('_factor', '_return')
        )
        
        if len(merged) < 10:
            continue
        
        # 分组
        try:
            merged['group'] = pd.qcut(merged[factor_col], n_groups, labels=range(1, n_groups+1), duplicates='drop')
        except:
            continue
        
        # 计算各组收益
        for g in range(1, n_groups+1):
            gdata = merged[merged['group'] == g]
            if len(gdata) > 0:
                results.append({
                    'trade_date': next_month,
                    'group': g,
                    'return': gdata['next_return'].mean()
                })
    
    return pd.DataFrame(results)


def calc_ls_return(group_returns):
    """
    计算多空对冲收益
    Long: 分组1 (低因子值)
    Short: 分组5 (高因子值)
    """
    # 按月计算多空收益
    ls = []
    for month, group in group_returns.groupby('trade_date'):
        g1 = group[group['group'] == 1]['return'].mean()
        g5 = group[group['group'] == 5]['return'].mean()
        if not (np.isnan(g1) or np.isnan(g5)):
            ls.append({
                'trade_date': month,
                'ls_return': g1 - g5
            })
    
    return pd.DataFrame(ls)


def calc_performance_metrics(returns_df):
    """
    计算绩效指标
    - 年化收益率
    - 年化波动率
    - 信息比率 IR = mean / std * sqrt(12)
    - 月度胜率
    - 最大回撤
    """
    if len(returns_df) == 0:
        return {}
    
    rets = returns_df['ls_return'].dropna()
    
    # 年化收益
    annual_return = rets.mean() * 12
    
    # 年化波动
    annual_vol = rets.std() * np.sqrt(12)
    
    # 信息比率
    ir = annual_return / annual_vol if annual_vol > 0 else 0
    
    # 月度胜率
    win_rate = (rets > 0).mean()
    
    # 最大回撤
    cum_ret = (1 + rets).cumprod()
    running_max = cum_ret.cummax()
    drawdown = (cum_ret - running_max) / running_max
    max_dd = drawdown.min()
    
    return {
        '年化收益率': f"{annual_return*100:.2f}%",
        '年化波动率': f"{annual_vol*100:.2f}%",
        '信息比率': f"{ir:.2f}",
        '月度胜率': f"{win_rate*100:.2f}%",
        '最大回撤': f"{max_dd*100:.2f}%"
    }


# ============== 主函数 ==============
def main():
    print("=" * 50)
    print("Step 3: 分组回测与IC分析")
    print("=" * 50)
    
    # 加载因子数据
    factor_file = OUTPUT_PATH / "factors.parquet"
    if not factor_file.exists():
        print(f"错误: 未找到因子文件 {factor_file}")
        print("请先运行 02_factor_build.py")
        return
    
    factor_df = pd.read_parquet(factor_file)
    print(f"加载因子数据: {len(factor_df):,} 行")
    
    # 加载价格数据计算收益
    price_file = DATA_PATH / "cleaned_data.parquet"
    price_df = pd.read_parquet(price_file)
    
    # 计算下月收益
    price_df = price_df.sort_values(['ts_code', 'trade_date'])
    price_df['next_return'] = price_df.groupby('ts_code')['return'].shift(-1)
    price_df['yearmonth'] = price_df['trade_date'].astype(str).str[:6]
    
    # 因子列表
    factors = [
        'OLD_Momentum', 'OLD_Intraday', 'OLD_Overnight',
        'NEW_Intraday', 'NEW_Overnight', 'NEW_Momentum',
        'Intraday_part1', 'Intraday_part5',
        'Overnight_part1', 'Overnight_part5'
    ]
    
    results = {}
    
    for factor in factors:
        if factor not in factor_df.columns:
            print(f"跳过 {factor} (不存在)")
            continue
            
        print(f"\n>>> 分析因子: {factor}")
        
        # IC分析
        ic_df = calc_ic(factor_df, price_df, factor)
        ic_metrics = calc_ic_metrics(ic_df)
        
        # 分组回测
        group_ret = calc_group_returns(factor_df, price_df, factor)
        ls_ret = calc_ls_return(group_ret)
        perf = calc_performance_metrics(ls_ret)
        
        results[factor] = {**ic_metrics, **perf}
        
        # 打印结果
        print(f"  IC均值: {ic_metrics['IC均值']:.4f}")
        print(f"  年化ICIR: {ic_metrics['年化ICIR']:.2f}")
        if perf:
            print(f"  年化收益: {perf.get('年化收益率', 'N/A')}")
            print(f"  信息比率: {perf.get('信息比率', 'N/A')}")
    
    # 保存结果
    results_df = pd.DataFrame(results).T
    output_file = OUTPUT_PATH / "backtest_results.csv"
    results_df.to_csv(output_file)
    print(f"\n保存结果到: {output_file}")
    
    return results_df


if __name__ == "__main__":
    main()
