# -*- coding: utf-8 -*-
"""
工具函数
"""
import numpy as np
import pandas as pd
from typing import Optional
from numba import jit


# ========== 数值计算 ==========

def zscore(x: np.ndarray) -> np.ndarray:
    """z-score标准化"""
    mean = np.nanmean(x)
    std = np.nanstd(x)
    if std == 0 or np.isnan(std):
        return np.zeros_like(x)
    return (x - mean) / std


def zscore_df(df: pd.Series) -> pd.Series:
    """DataFrame列z-score标准化"""
    mean = df.mean()
    std = df.std()
    if std == 0:
        return df - df.mean()
    return (df - mean) / std


def winsorize(x: np.ndarray, std: float = 3.0) -> np.ndarray:
    """去极值 (3倍标准差)"""
    mean = np.nanmean(x)
    std = np.nanstd(x)
    lower = mean - std * std
    upper = mean + std * std
    return np.clip(x, lower, upper)


def neutralize(factor: np.ndarray, style: np.ndarray) -> np.ndarray:
    """中性化 (残差法)"""
    # 简单线性回归: factor = a * style + residual
    # residual = factor - a * style
    style = style.reshape(-1, 1) if style.ndim == 1 else style
    
    # 最小二乘
    coef = np.linalg.lstsq(np.c_[np.ones(len(style)), style, rcond=None)[0]
    residual = factor - np.dot(np.c_[np.ones(len(style)), coef)
    return residual


# ========== Numba加速函数 ==========

@jit(nopython=True)
def calc_cumprod(returns: np.ndarray) -> np.ndarray:
    """
    计算累计收益 (Numba加速)
    cumprod = prod(1 + r_i) - 1
    """
    n = len(returns)
    result = np.empty(n)
    prod = 1.0
    for i in range(n):
        prod *= (1.0 + returns[i])
        result[i] = prod - 1.0
    return result


@jit(nopython=True)
def calc_cumprod_grouped(returns: np.ndarray, group_idx: np.ndarray, n_groups: int) -> np.ndarray:
    """
    分组累计收益
    """
    n = len(returns)
    result = np.full(n, np.nan)
    
    for g in range(n_groups):
        mask = (group_idx == g)
        indices = np.where(mask)[0]
        if len(indices) == 0:
            continue
        prod = 1.0
        for i in indices:
            prod *= (1.0 + returns[i])
            result[i] = prod - 1.0
    return result


# ========== 数据处理 ==========

def safe_divide(a: np.ndarray, b: np.ndarray, fill_value: float = 0.0) -> np.ndarray:
    """安全除法 (避免除零)"""
    result = np.full_like(a, fill_value)
    mask = (b != 0) & (~np.isnan(b))
    result[mask] = a[mask] / b[mask]
    return result


def fill_forward(df: pd.DataFrame, columns: list) -> pd.DataFrame:
    """前向填充"""
    result = df.copy()
    for col in columns:
        if col in result.columns:
            result[col] = result[col].fillna(method='ffill')
    return result


# ========== 日期处理 ==========

def parse_date(date_str: str) -> str:
    """解析日期为 YYYYMMDD 格式"""
    if pd.isna(date_str):
        return None
    
    date_str = str(date_str).replace('-', '').replace('/', '')
    
    # 尝试解析
    try:
        if len(date_str) == 8:
            return date_str
        elif len(date_str) == 10:
            return date_str[:4] + date_str[5:7] + date_str[8:10]
    except:
        pass
    return None


def get_month_end(dates: pd.Series) -> pd.DatetimeIndex:
    """获取月末日期"""
    return pd.to_datetime(dates).to_period('M').to_timestamp('M')
