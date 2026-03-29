# -*- coding: utf-8 -*-
"""
01_数据接口与预处理
===========================
统一数据加载接口，支持多种数据源
"""

import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
import yaml
import warnings


# ========== 1. 统一数据格式 ==========

@dataclass
class UnifiedDataSchema:
    """统一数据格式定义"""
    # 必填字段
    ts_code: str = ""          # 股票代码
    trade_date: str = ""       # 交易日期 YYYYMMDD
    open: float = 0.0          # 开盘价
    high: float = 0.0          # 最高价
    low: float = 0.0            # 最低价
    close: float = 0.0         # 收盘价
    volume: float = 0.0         # 成交量
    
    # 选填字段 (可估算)
    turnover_rate: Optional[float] = None     # 换手率
    turnover_rate_f: Optional[float] = None   # 流通换手率
    float_share: Optional[float] = None      # 流通股本
    amount: Optional[float] = None         # 成交额
    is_st: bool = False                    # 是否ST
    list_date: Optional[str] = None         # 上市日期
    prev_close: Optional[float] = None      # 昨日收盘价
    
    @classmethod
    def get_required_columns(cls) -> List[str]:
        return ['ts_code', 'trade_date', 'open', 'high', 'low', 'close', 'volume']
    
    @classmethod
    def get_optional_columns(cls) -> List[str]:
        return ['turnover_rate', 'turnover_rate_f', 'float_share', 
                'amount', 'is_st', 'list_date', 'prev_close']


# ========== 2. 字段映射器 ==========

class FieldMapper:
    """
    字段映射器
    处理不同数据源的字段名差异
    """
    
    # 默认字段映射 (标准名 -> 常见别名)
    DEFAULT_MAPPING = {
        'ts_code': ['ts_code', 'stock_code', 'code', 'symbol', '股票代码', '代码'],
        'trade_date': ['trade_date', 'date', '日期', 'datetime', '交易日期'],
        'open': ['open', 'open_price', '开盘价', 'openprice'],
        'high': ['high', 'high_price', '最高价', 'highprice'],
        'low': ['low', 'low_price', '最低价', 'lowprice'],
        'close': ['close', 'close_price', '收盘价', 'closeprice'],
        'volume': ['volume', 'vol', '成交量', 'amount'],  # 注意: amount 实际是成交额
        'turnover_rate': ['turnover_rate', 'turnover', '换手率', 'turn'],
        'turnover_rate_f': ['turnover_rate_f', 'turnover_f', '流通换手率'],
    }
    
    def __init__(self, custom_mapping: Optional[Dict[str, List[str]]] = None):
        """
        Args:
            custom_mapping: 自定义映射, 格式 {"标准名": ["别名1", "别名2"]}
        """
        self.mapping = self.DEFAULT_MAPPING.copy()
        if custom_mapping:
            self.mapping.update(custom_mapping)
    
    def detect_and_map(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        自动检测并映射字段
        
        Returns:
            映射后的DataFrame
        """
        result = pd.DataFrame()
        unmapped = []
        
        # 创建反向映射 (别名 -> 标准名)
        alias_to_std = {}
        for std, aliases in self.mapping.items():
            for alias in aliases:
                alias_to_std[alias.lower()] = std
        
        # 匹配列名
        for col in df.columns:
            col_lower = col.lower().strip()
            if col_lower in alias_to_std:
                std_name = alias_to_std[col_lower]
                result[std_name] = df[col]
            else:
                # 尝试精确匹配
                if col in self.mapping:
                    result[col] = df[col]
                else:
                    unmapped.append(col)
        
        if unmapped:
            warnings.warn(f"未映射的列: {unmapped[:5]}")
        
        return result
    
    def estimate_missing(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        估算缺失字段
        """
        result = df.copy()
        
        # 1. 估算 prev_close (昨日收盘价)
        if 'prev_close' not in result.columns and 'close' in result.columns:
            result = result.sort_values(['ts_code', 'trade_date'])
            result['prev_close'] = result.groupby('ts_code')['close'].shift(1)
        
        # 2. 估算 turnover_rate (换手率)
        if 'turnover_rate' not in result.columns:
            if 'amount' in result.columns and 'float_share' in result.columns:
                result['turnover_rate'] = result['amount'] / result['float_share'] * 100
            elif 'volume' in result.columns and 'float_share' in result.columns:
                result['turnover_rate'] = result['volume'] / result['float_share'] * 100
        
        # 3. 估算 float_share (流通股本)
        if 'float_share' not in result.columns:
            if 'amount' in result.columns and 'close' in result.columns:
                # 市值 / 价格 = 股本
                result['float_share'] = result['amount'] / result['close']
        
        return result


# ========== 3. 数据校验器 ==========

@dataclass
class ValidationReport:
    """校验报告"""
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)


class DataValidator:
    """
    数据校验器
    L0: 必填字段
    L1: 数据类型
    L2: 数值范围
    L3: 业务逻辑
    """
    
    def __init__(self, strict: bool = False):
        self.strict = strict
    
    def validate(self, df: pd.DataFrame) -> ValidationReport:
        """执行校验"""
        report = ValidationReport()
        
        # L0: 必填字段检查
        required = UnifiedDataSchema.get_required_columns()
        missing = [c for c in required if c not in df.columns]
        if missing:
            report.errors.append(f"缺少必填字段: {missing}")
            report.is_valid = False
        
        if not report.is_valid:
            return report
        
        # L1: 数据类型检查
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            if col in df.columns:
                if not pd.api.types.is_numeric_dtype(df[col]):
                    report.warnings.append(f"{col} 不是数值类型")
        
        # L2: 数值范围检查
        for col in ['open', 'close', 'high', 'low']:
            if col in df.columns:
                if (df[col] <= 0).any():
                    n_invalid = (df[col] <= 0).sum()
                    report.warnings.append(f"{col} 有 {n_invalid} 个非正值")
        
        if 'volume' in df.columns:
            if (df['volume'] < 0).any():
                report.errors.append("volume 不能为负")
                report.is_valid = False
        
        # L3: 业务逻辑检查
        if all(c in df.columns for c in ['high', 'low']):
            if (df['high'] < df['low']).any():
                n_invalid = (df['high'] < df['low']).sum()
                report.warnings.append(f"high < low: {n_invalid} 条")
        
        if all(c in df.columns for c in ['high', 'open', 'close']):
            if ((df['high'] < df['open']) | (df['high'] < df['close'])).any():
                report.warnings.append("存在 high < open 或 high < close")
        
        # 统计信息
        report.stats = {
            'total_rows': len(df),
            'total_stocks': df['ts_code'].nunique() if 'ts_code' in df.columns else 0,
            'date_range': (df['trade_date'].min(), df['trade_date'].max()) if 'trade_date' in df.columns else None,
        }
        
        return report


# ========== 4. 数据适配器 ==========

class DataAdapter(ABC):
    """数据适配器基类"""
    
    @abstractmethod
    def load_raw(self, **kwargs) -> pd.DataFrame:
        """加载原始数据"""
        pass


class TushareAdapter(DataAdapter):
    """Tushare适配器"""
    
    def __init__(self, token: str):
        self.token = token
    
    def load_raw(self, start_date: str, end_date: str, **kwargs) -> pd.DataFrame:
        try:
            import tushare as ts
            pro = ts.pro_api(self.token)
            
            # 获取所有A股
            df = pro.daily(
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', '')
            )
            return df
        except ImportError:
            raise ImportError("请安装tushare: pip install tushare")
        except Exception as e:
            raise RuntimeError(f"Tushare加载失败: {e}")


class AKShareAdapter(DataAdapter):
    """AKShare适配器"""
    
    def load_raw(self, symbol: str = "000001", start_date: str = "20100101", 
                 end_date: str = "20190731", **kwargs) -> pd.DataFrame:
        try:
            import akshare as ak
            # 需要手动循环获取多只股票
            # 这里简化返回空DataFrame
            warnings.warn("AKShare需要逐个股票获取，请使用其他方式")
            return pd.DataFrame()
        except ImportError:
            raise ImportError("请安装akshare: pip install akshare")


class CSVAdapter(DataAdapter):
    """CSV文件适配器"""
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
    
    def load_raw(self, **kwargs) -> pd.DataFrame:
        if not self.file_path.exists():
            raise FileNotFoundError(f"文件不存在: {self.file_path}")
        
        # 自动检测分隔符
        for sep in [',', '\t', ';', '|']:
            try:
                df = pd.read_csv(self.file_path, sep=sep, nrows=5)
                if len(df.columns) > 1:
                    return pd.read_csv(self.file_path, sep=sep)
            except:
                continue
        
        raise ValueError("无法解析CSV文件")


class DataFrameAdapter(DataAdapter):
    """DataFrame适配器 (内存数据)"""
    
    def __init__(self, df: pd.DataFrame):
        self.df = df
    
    def load_raw(self, **kwargs) -> pd.DataFrame:
        return self.df.copy()


# ========== 5. 统一入口 ==========

class DataLoader:
    """
    统一数据加载入口
    """
    
    def __init__(
        self, 
        adapter: DataAdapter,
        field_mapping: Optional[Dict[str, List[str]]] = None,
        strict: bool = False
    ):
        """
        Args:
            adapter: 数据适配器
            field_mapping: 自定义字段映射
            strict: 是否严格模式
        """
        self.adapter = adapter
        self.mapper = FieldMapper(field_mapping)
        self.validator = DataValidator(strict)
    
    def load(self, **kwargs) -> pd.DataFrame:
        """
        加载并处理数据
        
        Returns:
            统一格式的DataFrame
        """
        # 1. 加载原始数据
        print("[1/4] 加载原始数据...")
        raw_df = self.adapter.load_raw(**kwargs)
        print(f"    原始数据: {len(raw_df):,} 行")
        
        # 2. 字段映射
        print("[2/4] 字段映射...")
        mapped_df = self.mapper.detect_and_map(raw_df)
        
        # 3. 估算缺失
        print("[3/4] 估算缺失字段...")
        estimated_df = self.mapper.estimate_missing(mapped_df)
        
        # 4. 校验
        print("[4/4] 数据校验...")
        report = self.validator.validate(estimated_df)
        
        if report.errors:
            print(f"    错误: {report.errors[0]}")
        if report.warnings:
            print(f"    警告: {len(report.warnings)} 项")
        
        print(f"    有效数据: {len(estimated_df):,} 行")
        
        if report.stats:
            print(f"    股票数: {report.stats.get('total_stocks', 'N/A')}")
        
        return estimated_df


# ========== 6. 便捷函数 ==========

def load_data(
    source: str = "csv",
    file_path: str = None,
    token: str = None,
    df: pd.DataFrame = None,
    field_mapping: Dict[str, List[str]] = None,
    **kwargs
) -> pd.DataFrame:
    """
    便捷数据加载函数
    
    Examples:
        # 从CSV加载
        df = load_data("csv", "data/stocks.csv")
        
        # 从DataFrame加载
        df = load_data("df", df=my_dataframe)
        
        # 从Tushare加载
        df = load_data("tushare", token="xxx", start_date="20100101", end_date="20190731")
    
    Args:
        source: 数据源类型 ("csv", "tushare", "akshare", "df")
        file_path: CSV文件路径
        token: Tushare token
        df: 内存DataFrame
        field_mapping: 自定义字段映射
    
    Returns:
        统一格式的DataFrame
    """
    if source == "csv" and file_path:
        adapter = CSVAdapter(file_path)
    elif source == "tushare" and token:
        adapter = TushareAdapter(token)
    elif source == "df" and df is not None:
        adapter = DataFrameAdapter(df)
    else:
        raise ValueError(f"未知数据源: {source}")
    
    loader = DataLoader(adapter, field_mapping)
    return loader.load(**kwargs)


# ========== 7. 主函数 ==========

def main():
    """测试入口"""
    print("=" * 50)
    print("数据接口测试")
    print("=" * 50)
    
    # 测试: 创建示例数据
    test_data = pd.DataFrame({
        '股票代码': ['000001', '000001', '000002', '000002'],
        '交易日期': ['20190101', '20190102', '20190101', '20190102'],
        '开盘价': [10.0, 10.5, 20.0, 20.5],
        '收盘价': [10.5, 10.2, 20.5, 21.0],
        '最高价': [10.8, 10.8, 21.0, 21.2],
        '最低价': [9.8, 10.0, 19.5, 20.0],
        '成交量': [1000000, 1200000, 800000, 900000],
    })
    
    # 加载
    df = load_data("df", df=test_data)
    print("\n加载完成!")
    print(df.head())


if __name__ == "__main__":
    main()
