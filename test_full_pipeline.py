# -*- coding: utf-8 -*-
"""
跑通整个流程 - 测试脚本
"""
import pandas as pd
import numpy as np
from scipy import stats

np.random.seed(42)

print("=" * 50)
print("Test: Run Full Pipeline")
print("=" * 50)

# 1. Create mock data
print("\n[Step 1] Create mock data...")

n_stocks = 100
n_days = 50
dates = pd.date_range('2019-01-01', periods=n_days, freq='D')
dates = [d.strftime('%Y%m%d') for d in dates if d.weekday() < 5][:40]
n_days = len(dates)

stocks = [f'{str(i).zfill(6)}' for i in range(1, n_stocks+1)]

data = []
for code in stocks:
    prev = 10.0
    for d in dates:
        close = prev * (1 + np.random.randn() * 0.02)
        open_p = close * (1 + np.random.uniform(-0.01, 0.01))
        data.append({
            'ts_code': code, 'trade_date': d,
            'open': open_p, 'close': close, 'high': max(open_p,close), 'low': min(open_p,close),
            'volume': 1e6, 'turnover_rate': 5.0, 'prev_close': prev
        })
        prev = close

df = pd.DataFrame(data)
print(f"  Rows: {len(df):,}")

# 2. Returns
print("\n[Step 2] Calculate returns...")

df = df.sort_values(['ts_code', 'trade_date'])
df['return'] = df['close'] / df['prev_close'] - 1
df['r_intraday'] = df['close'] / df['open'] - 1
df['r_overnight'] = df['open'] / df['prev_close'] - 1
df['TR_yesterday'] = df.groupby('ts_code')['turnover_rate'].shift(1)

# 3. Factors
print("\n[Step 3] Build factors...")

lookback = 20
df['ym'] = df['trade_date'].astype(str).str[:6]

# OLD factors
df['OLD_Momentum'] = df.groupby('ts_code')['return'].transform(
    lambda x: x.rolling(lookback).apply(lambda y: np.prod(1+y) - 1, raw=False)
)

# Local factors
def local_factors(sub, sort_col, ret_col, pre):
    sub = sub.sort_values(sort_col)
    n = len(sub) // 5
    if n == 0: return {}
    return {f'{pre}_part{k+1}': sub.iloc[k*n:(k+1)*n if k<4 else len(sub)][ret_col].mean() for k in range(5)}

intraday_parts, overnight_parts = [], []

for (code, ym), g in df.groupby(['ts_code', 'ym']):
    if len(g) < lookback: continue
    h = g.tail(lookback)
    ip = local_factors(h, 'turnover_rate', 'r_intraday', 'Intra')
    op = local_factors(h, 'TR_yesterday', 'r_overnight', 'Over')
    ip = {k:v for k,v in ip.items()}
    op = {k:v for k,v in op.items()}
    if ip:
        ip['ts_code'], ip['trade_date'] = code, ym
        intraday_parts.append(ip)
    if op:
        op['ts_code'], op['trade_date'] = code, ym
        overnight_parts.append(op)

intra_df = pd.DataFrame(intraday_parts)
over_df = pd.DataFrame(overnight_parts)

factors = intra_df.merge(over_df, on=['ts_code', 'trade_date'], how='outer')

# z-score
def zscore(x):
    return (x - x.mean()) / x.std() if x.std() > 0 else 0

for s in ['ts_code', 'trade_date']:
    if s not in factors.columns: continue
    factors = factors.drop(columns=s)

factors['Intra_p1_z'] = factors.groupby('trade_date')['Intra_part1'].transform(zscore)
factors['Intra_p5_z'] = factors.groupby('trade_date')['Intra_part5'].transform(zscore)
factors['NEW_Intraday'] = -factors['Intra_p1_z'] + factors['Intra_p5_z']

factors['Over_p1_z'] = factors.groupby('trade_date')['Over_part1'].transform(zscore)
factors['Over_p5_z'] = factors.groupby('trade_date')['Over_part5'].transform(zscore)
factors['NEW_Overnight'] = factors['Over_p1_z'] - factors['Over_p5_z']

factors['z_Intra'] = factors.groupby('trade_date')['NEW_Intraday'].transform(zscore)
factors['z_Over'] = factors.groupby('trade_date')['NEW_Overnight'].transform(zscore)
factors['NEW_Momentum'] = factors['z_Intra'] + factors['z_Over']

print(f"  Factor rows: {len(factors):,}")

# 4. Backtest
print("\n[Step 4] Backtest...")

# Forward return
price = df[['ts_code','trade_date','close']].copy()
price = price.sort_values(['ts_code','trade_date'])
price['fwd_ret'] = price.groupby('ts_code')['close'].pct_change().shift(-1)

# Merge
m = factors.merge(price, on=['ts_code','trade_date'], how='inner')
print(f"  Merged: {len(m):,}")

# Test factors
fc_list = ['OLD_Momentum', 'NEW_Intraday', 'NEW_Overnight', 'NEW_Momentum']

# Add OLD factors
temp = df.groupby(['ts_code','ym'])['OLD_Momentum'].first().reset_index()
temp.columns = ['ts_code','trade_date','OLD_Momentum']
m = m.merge(temp, on=['ts_code','trade_date'], how='left')

print("\nResults:")
print("-" * 50)
print(f"{'Factor':<20} {'IC':>8} {'Ann%':>10} {'IR':>8}")
print("-" * 50)

for fc in fc_list:
    if fc not in m.columns: continue
    v = m[[fc, 'fwd_ret']].dropna()
    if len(v) < 20: continue
    
    ic, _ = stats.spearmanr(v[fc], v['fwd_ret'])
    
    try:
        v['g'] = pd.qcut(v[fc], 5, labels=[1,2,3,4,5], duplicates='drop')
        g1 = v[v['g']==1]['fwd_ret'].mean()
        g5 = v[v['g']==5]['fwd_ret'].mean()
        ls = g1 - g5
        ann = ls * 12 * 100
        vol = v['fwd_ret'].std() * 312
        ir = ann / vol if vol > 0 else 0
    except:
        ann, ir = 0, 0
    
    print(f"{fc:<20} {ic:>+8.4f} {ann:>+9.2f} {ir:>+8.2f}")

print("-" * 50)

# Save
print("\n[Step 5] Save...")

Path('output').mkdir(exist_ok=True)
factors.to_csv('output/factors.csv', index=False)
df[['ts_code','trade_date','close']].to_csv('output/prices.csv', index=False)

print("Saved to output/")
print("  factors.csv")
print("  prices.csv")

print("\n" + "=" * 50)
print("DONE!")
print("=" * 50)