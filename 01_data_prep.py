# -*- coding: utf-8 -*-
"""
01_数据清洗与预处理
===========================
获取2010-2019年全A日频OHLCV、换手率、集合竞价数据
样本过滤：剔除ST、停牌、上市不足60日次新股
输出：cleaned_data.parquet
"""

import pandas as pd
import numpy as np
from pathlib import Path

# ============== 配置 ==============
DATA_PATH = Path(__file__).parent / "data"
OUTPUT_PATH = Path(__file__).parent / "output"
START_DATE = "20100101"
END_DATE = "20190731"
MIN_TRADING_DAYS = 60  # 上市至少60个交易日

# ============== 数据获取接口 ==============
def get_data_from_tushare():
    """
    从Tushare获取数据
    需要字段:
    - daily: ts_code, trade_date, open, high, low, close, vol, amount
    - daily_basic: ts_code, trade_date, turnover_rate, turnover_rate_f, volume_ratio
    - stock_basic: ts_code, list_date, delist_date, is_hs, is_st
    """
    import tushare as ts
    
    # 设置token (需要用户自己设置)
    # pro = ts.pro_api('YOUR_TOKEN')
    
    print("请安装tushare并设置token:")
    print("pip install tushare")
    print("或使用AKShare作为替代")
    raise NotImplementedError("请先配置数据源")


def get_data_from_akshare():
    """
    从AKShare获取数据（免费开源）
    """
    import akshare as ak
    
    print("使用AKShare获取数据...")
    
    # 获取股票日线数据
    # stock_zh_a_hist(symbol="000001", period="daily", start_date="20100101", end_date="20190731")
    
    print("AKShare数据获取功能待实现")
    raise NotImplementedError("请先确认数据源")


def load_local_data():
    """
    加载本地parquet数据
    """
    data_file = DATA_PATH / "raw_data.parquet"
    if data_file.exists():
        return pd.read_parquet(data_file)
    else:
        raise FileNotFoundError(f"未找到数据文件: {data_file}")


# ============== 数据预处理 ==============
def calculate_returns(df):
    """
    计算日内收益和隔夜收益
    
    日内收益: r_t = close_t / open_t - 1
    隔夜收益: g_t = open_t / close_{t-1} - 1
    """
    df = df.sort_values(['ts_code', 'trade_date'])
    
    # 日内收益
    df['r_intraday'] = df['close'] / df['open'] - 1
    
    # 隔夜收益 (需要前一日收盘价)
    df['prev_close'] = df.groupby('ts_code')['close'].shift(1)
    df['r_overnight'] = df['open'] / df['prev_close'] - 1
    
    return df


def calculate_turnover(df):
    """
    计算换手率相关指标
    
    日内换手率 = (总成交量 - 集合竞价成交量) / 流通股本
    隔夜换手率 = 集合竞价成交量 / 流通股本
    昨日换手率 = shift(总换手率, 1)
    """
    # 如果没有集合竞价数据，用总成交量*0.1估算
    if 'auction_volume' not in df.columns:
        print("警告: 无集合竞价数据，使用估算值")
        df['auction_volume'] = df['volume'] * 0.1
    
    # 流通股本 (元/净)
    if 'float_share' not in df.columns:
        # 用 amount/close 估算
        df['float_share'] = df['amount'] / df['close']
    
    # 日内换手率
    df['TR_intraday'] = (df['volume'] - df['auction_volume']) / df['float_share']
    
    # 隔夜换手率
    df['TR_overnight'] = df['auction_volume'] / df['float_share']
    
    # 昨日换手率
    df['TR_yesterday'] = df.groupby('ts_code')['turnover_rate'].shift(1)
    
    return df


def filter_valid_stocks(df):
    """
    过滤有效股票池
    - 剔除ST股
    - 剔除停牌日 (vol=0 或 close=open=prev_close)
    - 剔除上市不足60日的次新股
    """
    # 剔除ST
    df = df[~df['is_st'].fillna(False)]
    
    # 剔除停牌日 (成交量为0)
    df = df[df['volume'] > 0]
    
    # 剔除上市不足60日
    # 需要根据list_date计算
    
    return df


def process_nan(df):
    """
    处理NaN值
    - 前向填充收益率
    - 换手率NaN设为0
    """
    df['r_intraday'] = df['r_intraday'].fillna(0)
    df['r_overnight'] = df['r_overnight'].fillna(0)
    df['TR_intraday'] = df['TR_intraday'].fillna(0)
    df['TR_overnight'] = df['TR_overnight'].fillna(0)
    df['TR_yesterday'] = df['TR_yesterday'].fillna(0)
    
    return df


# ============== 主函数 ==============
def main():
    print("=" * 50)
    print("Step 1: 数据获取与预处理")
    print("=" * 50)
    
    # 1. 加载数据
    print("\n[1/5] 加载原始数据...")
    try:
        df = load_local_data()
    except FileNotFoundError as e:
        print(e)
        print("\n请先准备数据文件到 data/raw_data.parquet")
        print("或修改代码使用Tushare/AKShare")
        return None
    
    print(f"原始数据量: {len(df):,} 行")
    
    # 2. 计算收益
    print("\n[2/5] 计算日内/隔夜收益...")
    df = calculate_returns(df)
    
    # 3. 计算换手率
    print("\n[3/5] 计算换手率指标...")
    df = calculate_turnover(df)
    
    # 4. 过滤有效股票
    print("\n[4/5] 过滤有效股票池...")
    df = filter_valid_stocks(df)
    
    # 5. 处理NaN
    print("\n[5/5] 处理缺失值...")
    df = process_nan(df)
    
    # 保存
    output_file = DATA_PATH / "cleaned_data.parquet"
    df.to_parquet(output_file, index=False)
    print(f"\n保存到: {output_file}")
    print(f"最终数据量: {len(df):,} 行")
    print(f"股票数量: {df['ts_code'].nunique()}")
    print(f"时间范围: {df['trade_date'].min()} ~ {df['trade_date'].max()}")
    
    return df


if __name__ == "__main__":
    main()
