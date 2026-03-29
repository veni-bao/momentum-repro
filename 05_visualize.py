# -*- coding: utf-8 -*-
"""
05_可视化
===========================
- 净值曲线 (5分组、多空对冲)
- IC时序图、IC柱状图
- 绩效对比表格
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List
from pathlib import Path
import warnings

# 设置中文
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


# ========== 1. IC图 ==========

def plot_ic_series(
    ic_df: pd.DataFrame,
    title: str = "IC时序图",
    save_path: str = None
):
    """
    绘制IC时序图
    
    Args:
        ic_df: IC序列 (date, IC)
        title: 标题
        save_path: 保存路径
    """
    fig, ax = plt.subplots(figsize=(12, 4))
    
    # 柱状图
    colors = ['green' if x > 0 else 'red' for x in ic_df['IC']]
    ax.bar(range(len(ic_df)), ic_df['IC'], color=colors, alpha=0.7)
    
    # 基准线
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax.axhline(y=ic_df['IC'].mean(), color='blue', linestyle='--', 
              label=f"IC均值={ic_df['IC'].mean():.4f}")
    
    ax.set_xlabel('月份')
    ax.set_ylabel('IC')
    ax.set_title(title)
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"保存到: {save_path}")
    
    plt.close()


def plot_ic_comparison(
    ic_results: Dict[str, Dict],
    title: str = "因子IC对比",
    save_path: str = None
):
    """
    绘制多因子IC对比柱状图
    
    Args:
        ic_results: 因子名 -> IC指标字典
        title: 标题
        save_path: 保存路径
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # 提取数据
    factors = list(ic_results.keys())
    ic_means = [ic_results[f].get('IC均值', 0) for f in factors]
    ic_irs = [ic_results[f].get('ICIR', 0) for f in factors]
    
    # 颜色
    colors = ['green' if x < 0 else 'red' for x in ic_means]
    
    x = np.arange(len(factors))
    width = 0.35
    
    # IC均值
    ax.bar(x - width/2, ic_means, width, label='IC均值', color=colors, alpha=0.7)
    
    # ICIR
    ax.bar(x + width/2, ic_irs, width, label='ICIR', color='blue', alpha=0.5)
    
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(factors, rotation=45, ha='right')
    ax.set_ylabel('值')
    ax.set_title(title)
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"保存到: {save_path}")
    
    plt.close()


# ========== 2. 净值曲线 ==========

def plot_cum_net_value(
    returns_df: pd.DataFrame,
    title: str = "多空对冲净值走势",
    save_path: str = None
):
    """
    绘制多空对冲净值走势
    
    Args:
        returns_df: 收益序列 (date, return)
        title: 标题
        save_path: 保存路径
    """
    fig, ax = plt.subplots(figsize=(12, 4))
    
    # 累计净值
    cum_ret = (1 + returns_df['return']).cumprod()
    ax.plot(cum_ret.index, cum_ret.values, linewidth=2, color='blue')
    ax.axhline(y=1, color='black', linestyle='--', linewidth=0.5)
    
    ax.set_xlabel('月份')
    ax.set_ylabel('净值')
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"保存到: {save_path}")
    
    plt.close()


def plot_group_returns(
    group_returns: pd.DataFrame,
    title: str = "5分组收益",
    save_path: str = None
):
    """
    绘制5分组收益柱状图
    
    Args:
        group_returns: 分组收益 (date, group, return)
        title: 标题
        save_path: 保存路径
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # 各组平均收益
    group_mean = group_returns.groupby('group')['return'].mean()
    
    # 颜色 (红->绿)
    colors = plt.cm.RdYlGn_r(np.linspace(0.1, 0.9, len(group_mean)))
    
    ax.bar(group_mean.index, group_mean.values * 100, color=colors)
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    
    ax.set_xlabel('分组 (1=低因子, 5=高因子)')
    ax.set_ylabel('月均收益 (%)')
    ax.set_title(title)
    ax.grid(True, alpha=0.3, axis='y')
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"保存到: {save_path}")
    
    plt.close()


# ========== 3. 绩效对比表 ==========

def plot_performance_table(
    results: Dict[str, Dict],
    title: str = "绩效对比表",
    save_path: str = None
):
    """
    绘制绩效对比表格
    
    Args:
        results: 因子名 -> 指标字典
        title: 标题
        save_path: 保存路径
    """
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.axis('off')
    
    # 准备表格数据
    headers = ['因子', 'IC均值', 'ICIR', '年化收益', '信息比率', '月度胜率', '最大回撤']
    
    rows = []
    for factor, metrics in results.items():
        row = [
            factor,
            f"{metrics.get('IC均值', 0):.4f}",
            f"{metrics.get('ICIR', 0):.2f}",
            f"{metrics.get('年化收益率', 0):.2f}%",
            f"{metrics.get('信息比率', 0):.2f}",
            f"{metrics.get('月度胜率', 0):.2f}%",
            f"{metrics.get('最大回撤', 0):.2f}%"
        ]
        rows.append(row)
    
    # 绘制表格
    table = ax.table(
        cellText=rows,
        colLabels=headers,
        loc='center',
        cellLoc='center'
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 1.8)
    
    ax.set_title(title, fontsize=14, pad=20)
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"保存到: {save_path}")
    
    plt.close()


# ========== 4. 综合绘图 ==========

def plot_all(
    results: Dict[str, Dict],
    output_dir: str = "output"
):
    """
    绘制所有图表
    
    Args:
        results: 回测结果
        output_dir: 输出目录
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    print("=" * 50)
    print("绘制图表")
    print("=" * 50)
    
    # 绩效对比表
    plot_performance_table(
        results,
        save_path=output_path / 'performance_table.png'
    )
    
    # IC对比
    plot_ic_comparison(
        results,
        save_path=output_path / 'ic_comparison.png'
    )
    
    print(f"\n图表已保存到: {output_path}")


# ========== 5. 主函数 ==========

def main():
    """测试"""
    # 示例数据
    results = {
        'OLD_Momentum': {
            'IC均值': -0.03,
            'ICIR': 1.04,
            '年化收益率': 19.71,
            '信息比率': 1.04,
            '月度胜率': 66.15,
            '最大回撤': 15.89
        },
        'NEW_Momentum': {
            'IC均值': -0.055,
            'ICIR': -3.04,
            '年化收益率': 18.65,
            '信息比率': 2.89,
            '月度胜率': 86.15,
            '最大回撤': 6.33
        }
    }
    
    print("绘制示例图表...")
    plot_all(results, "output")
    print("\n完成!")


if __name__ == "__main__":
    main()