# Data generator for testing
import pandas as pd
import numpy as np
from pathlib import Path

def generate_mock_data(n_stocks=100, n_days=50, output_dir=None):
    """生成模拟数据"""
    np.random.seed(42)
    
    # 生成日期
    dates = [f'2019{str(m).zfill(2)}{str(d).zfill(2)}' for m in range(1,13) for d in range(1,29)][:n_days]
    stocks = [f'{i:06d}' for i in range(1,n_stocks+1)]
    
    data = []
    for code in stocks:
        prev = 10.0
        for d in dates:
            close = prev * (1 + np.random.randn() * 0.02)
            data.append({
                'ts_code': code, 'trade_date': d,
                'open': close * 0.99, 'close': close,
                'high': close * 1.01, 'low': close * 0.99,
                'volume': np.random.uniform(1e6, 1e7),
                'turnover_rate': np.random.uniform(1, 10),
                'prev_close': prev
            })
            prev = close
    
    df = pd.DataFrame(data)
    df = df.sort_values(['ts_code', 'trade_date'])
    df['return'] = df['close'] / df['prev_close'] - 1
    
    # 计算因子
    lb = 20
    df['OLD_Momentum'] = df.groupby('ts_code')['return'].transform(
        lambda g: g.rolling(lb).apply(lambda x: np.prod(1+x)-1, raw=False)
    )
    
    df['NEW_Intra'] = np.random.randn(len(df)) * 0.1 + df['OLD_Momentum'] * 0.5
    df['NEW_Over'] = np.random.randn(len(df)) * 0.1 - df['OLD_Momentum'] * 0.3
    df['NEW_Momentum'] = df['NEW_Intra'] + df['NEW_Over']
    
    # 前瞻收益
    pr = df[['ts_code','trade_date','close']].copy().sort_values(['ts_code','trade_date'])
    pr['fwd'] = pr.groupby('ts_code')['close'].pct_change().shift(-1)
    
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_dir / 'factors.csv', index=False)
        pr.to_csv(output_dir / 'prices.csv', index=False)
        print(f"Data saved to {output_dir}")
    
    return df, pr

if __name__ == "__main__":
    # 默认生成到 data/mock
    output = Path(__file__).parent / 'mock'
    generate_mock_data(output_dir=output)
