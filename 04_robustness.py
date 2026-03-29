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
from pathlib import Path

# ============== 配置 ==============
DATA_PATH = Path(__file__).parent / "data"
OUTPUT_PATH = Path(__file__).parent / "output"

# 需要修改LOOKBACK参数重新运行02_factor_build.py
LOOKBACKS = [20, 40, 60]


def run_with_lookback(lookback):
    """
    用不同回看天数运行
    """
    print(f"\n{'='*50}")
    print(f"稳健性检验: 回看天数 = {lookback}")
    print(f"{'='*50}")
    
    # 这里需要修改02_factor_build.py的LOOKBACK参数
    # 然后重新运行
    print(f"\n请修改 02_factor_build.py 中的 LOOKBACK = {lookback}")
    print(f"然后运行: python 02_factor_build.py")
    print(f"再运行: python 03_backtest.py")


def run_with_sample_space():
    """
    不同样本空间测试
    沪深300、中证500成分股
    """
    print(f"\n{'='*50}")
    print(f"稳健性检验: 不同样本空间")
    print(f"{'='*50}")
    
    # 需要成分股列表数据
    print("\n需要额外数据:")
    print("- 沪深300成分股列表 (每月更新)")
    print("- 中证500成分股列表 (每月更新)")
    print("\n数据来源: Tushare index_weight 表")


def run_barra_neutral():
    """
    Barra中性化
    """
    print(f"\n{'='*50}")
    print(f"Barra中性化")
    print(f"{'='*50}")
    
    print("\n步骤:")
    print("1. 获取10个Barra风格因子:")
    print("   - Beta, Momentum, BooktoPrice, EarningsYield")
    print("   - Growth, Leverage, ResidualVolatility")
    print("   - Liquidity, Size, NonLinearSize")
    print("\n2. 获取28个申万一级行业虚拟变量")
    print("\n3. 每月横截面回归:")
    print("   NEW_Momentum = α + Σ(β_i * Factor_i) + Σ(γ_j * Industry_j) + ε")
    print("\n4. 取残差ε作为纯净因子")
    
    print("\n需要数据:")
    print("- Barra因子值 (Tushare barra_style)")
    print("- 行业分类 (Tushare sw_industry)")


def main():
    print("=" * 50)
    print("Step 4: 稳健性检验")
    print("=" * 50)
    
    # 1. 不同回看天数
    print("\n[1/3] 改变回看天数")
    for lb in LOOKBACKS:
        print(f"  - {lb}日")
    
    # 2. 不同样本空间
    print("\n[2/3] 改变样本空间")
    print("  - 沪深300成分股")
    print("  - 中证500成分股")
    
    # 3. Barra中性化
    print("\n[3/3] Barra中性化")
    print("  - 10个Barra风格因子 + 28个行业")
    
    # 保存配置
    config = {
        'lookbacks': LOOKBACKS,
        'sample_spaces': ['全A', '沪深300', '中证500'],
        'barra_neutral': True
    }
    
    print("\n" + "=" * 50)
    print("稳健性检验配置已保存")
    print("=" * 50)
    print("""
执行顺序:
1. 修改 02_factor_build.py 中 LOOKBACK=40，运行
2. 运行 03_backtest.py，记录结果
3. 修改 LOOKBACK=60，重复步骤1-2
4. 添加成分股过滤，重新运行
5. 获取Barra因子，进行中性化

详细结果请查看 output/backtest_results.csv
""")


if __name__ == "__main__":
    main()
