# -*- coding: utf-8 -*-
"""
05_绘图
===========================
- 净值曲线 (5分组、多空对冲)
- IC时序图、IC柱状图
- 绩效对比表格
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# ============== 配置 ==============
OUTPUT_PATH = Path(__file__).parent / "output"
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def plot_ic_series(ic_df, title="IC时序图"):
    """绘制IC时序图"""
    fig, ax = plt.subplots(figsize=(12, 4))
    
    ax.bar(range(len(ic_df)), ic_df['IC'], color=['green' if x > 0 else 'red' for x in ic_df['IC']])
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax.axhline(y=ic_df['IC'].mean(), color='blue', linestyle='--', label=f"IC均值={ic_df['IC'].mean():.4f}")
    
    ax.set_xlabel('月份')
    ax.set_ylabel('IC')
    ax.set_title(title)
    ax.legend()
    
    return fig


def plot_cum_net_value(returns_df, title="多空对冲净值走势"):
    """绘制多空对冲净值走势"""
    fig, ax = plt.subplots(figsize=(12, 4))
    
    cum_ret = (1 + returns_df['ls_return']).cumprod()
    ax.plot(cum_ret.index, cum_ret.values, linewidth=2)
    ax.axhline(y=1, color='black', linestyle='--', linewidth=0.5)
    
    ax.set_xlabel('月份')
    ax.set_ylabel('净值')
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    
    return fig


def plot_group_returns(group_returns, title="5分组收益"):
    """绘制5分组收益柱状图"""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # 各组平均收益
    group_mean = group_returns.groupby('group')['return'].mean()
    
    ax.bar(group_mean.index, group_mean.values * 100, color=plt.cm.RdYlGn_r(np.linspace(0, 1, 5)))
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    
    ax.set_xlabel('分组 (1=低因子, 5=高因子)')
    ax.set_ylabel('月均收益 (%)')
    ax.set_title(title)
    
    return fig


def plot_ic_comparison(factors_ic, title="因子IC对比"):
    """绘制因子IC对比柱状图"""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    ic_means = [f['IC均值'] for f in factors_ic.values()]
    labels = list(factors_ic.keys())
    
    colors = ['green' if x < 0 else 'red' for x in ic_means]  # 负IC为反转因子
    
    ax.barh(labels, ic_means, color=colors)
    ax.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
    
    ax.set_xlabel('IC均值')
    ax.set_title(title)
    
    return fig


def plot_performance_table(results_dict, title="绩效对比表"):
    """绘制绩效对比表格"""
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.axis('off')
    
    # 准备数据
    table_data = []
    headers = ['因子', 'IC均值', '年化ICIR', '年化收益', '信息比率', '月度胜率', '最大回撤']
    
    for name, metrics in results_dict.items():
        row = [
            name,
            f"{metrics.get('IC均值', 0):.4f}",
            f"{metrics.get('年化ICIR', 0):.2f}",
            metrics.get('年化收益率', 'N/A'),
            metrics.get('信息比率', 'N/A'),
            metrics.get('月度胜率', 'N/A'),
            metrics.get('最大回撤', 'N/A')
        ]
        table_data.append(row)
    
    table = ax.table(cellText=table_data, colLabels=headers, loc='center', cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.2, 1.5)
    
    ax.set_title(title, fontsize=14, pad=20)
    
    return fig


def main():
    print("=" * 50)
    print("Step 5: 绘图")
    print("=" * 50)
    
    # 加载结果数据
    results_file = OUTPUT_PATH / "backtest_results.csv"
    if not results_file.exists():
        print(f"警告: 未找到结果文件 {results_file}")
        print("请先运行 03_backtest.py")
        return
    
    results_df = pd.read_csv(results_file, index_col=0)
    print(f"加载结果: {len(results_df)} 个因子")
    
    # 绘制对比表格
    print("\n[1/1] 绘制绩效对比表格...")
    results_dict = results_df.to_dict('index')
    fig = plot_performance_table(results_dict, "因子绩效对比")
    
    output_file = OUTPUT_PATH / "performance_comparison.png"
    fig.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"保存到: {output_file}")
    
    plt.show()
    print("\n完成!")


if __name__ == "__main__":
    main()
