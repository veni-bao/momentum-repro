# -*- coding: utf-8 -*-
"""
跑通整个流程 - 测试脚本
"""
import pandas as pd
import numpy as np
from scipy import stats

np.random.seed(42)

# Create mock data
n_stocks = 100
dates = [f'2019{str(m).zfill(2)}{str(d).zfill(2)}' for m in range(1,13) for d in range(1,29)][:120]
dates = dates[:50]

data = []
for code in [f'{i:06d}' for i in range(1,n_stocks+1)]:
    prev = 10.0
    for d in dates:
        close = prev * (1 + np.random.randn() * 0.02)
        data.append({'ts_code':code, 'trade_date':d, 'close':close, 'prev_close':prev})
        prev = close

df = pd.DataFrame(data).sort_values(['ts_code','trade_date'])
df['return'] = df['close']/df['prev_close'] - 1

# Build OLD_Momentum
lookback = 20
df['OLD_Momentum'] = df.groupby('ts_code')['return'].transform(
    lambda x: x.rolling(lookback).apply(lambda y: np.prod(1+y)-1, raw=False) if len(y)>0 else np.nan
)

# Add some random NEW factors
df['NEW_Intraday'] = np.random.randn(len(df)) * 0.1 + df['OLD_Momentum'] * 0.5
df['NEW_Overnight'] = np.random.randn(len(df)) * 0.1 - df['OLD_Momentum'] * 0.3
df['NEW_Momentum'] = df['NEW_Intraday'] + df['NEW_Overnight']

# Forward return for testing
price = df[['ts_code','trade_date','close']].copy()
price = price.sort_values(['ts_code','trade_date'])
price['fwd_ret'] = price.groupby('ts_code')['close'].pct_change().shift(-1)

# Merge
m = df.merge(price, on=['ts_code','trade_date'], suffixes=('_f','_p'))
m = m.rename(columns={'close_f':'close'})

# IC test
print("="*50)
print("Backtest Results:")
print("="*50)

for fc in ['OLD_Momentum', 'NEW_Intraday', 'NEW_Overnight', 'NEW_Momentum']:
    v = m[[fc,'fwd_ret']].dropna()
    if len(v) < 20: continue
    
    ic, _ = stats.spearmanr(v[fc], v['fwd_ret'])
    
    try:
        v['g'] = pd.qcut(v[fc], 5, labels=[1,2,3,4,5], duplicates='skip')
        ls = v[v['g']==1]['fwd_ret'].mean() - v[v['g']==5]['fwd_ret'].mean()
        ann = ls * 12 * 100
        vol = v['fwd_ret'].std() * np.sqrt(12) * 100
        ir = ann / vol if vol > 0 else 0
    except:
        ann, ir = 0, 0
    
    print(f"{fc:<18} IC:{ic:+.4f}  Ann:{ann:+.2f}%  IR:{ir:+.2f}")

print("="*50)
print("Pipeline OK!")

# Save output
from pathlib import Path
Path('output').mkdir(exist_ok=True)
df.to_csv('output/test_factors.csv', index=False)
print("Data saved to output/test_factors.csv")