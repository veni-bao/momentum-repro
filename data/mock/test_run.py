# Mock data generator
import pandas as pd
import numpy as np
from scipy import stats

np.random.seed(42)
print("=" * 50)
print("Mock Data Generator")
print("=" * 50)

# 1. 创建模拟数据
dates = [f'2019{str(m).zfill(2)}{str(d).zfill(2)}' for m in range(1,13) for d in range(1,29)][:50]
stocks = [f'{i:06d}' for i in range(1,51)]

data = []
for code in stocks:
    p = 10.0
    for d in dates:
        c = p * (1 + np.random.randn() * 0.02)
        data.append(dict(ts_code=code, trade_date=d, close=c, prev_close=p))
        p = c

df = pd.DataFrame(data).sort_values(['ts_code','trade_date'])
df['ret'] = df['close'] / df['prev_close'] - 1

# 2. 计算OLD_Momentum
lb = 20
df['OLD_Momentum'] = df.groupby('ts_code')['ret'].transform(
    lambda g: g.rolling(lb).apply(lambda x: np.prod(1+x)-1, raw=False)
)

# 3. 构造NEW因子
df['NEW_Intra'] = np.random.randn(len(df)) * 0.1 + df['OLD_Momentum'] * 0.5
df['NEW_Over'] = np.random.randn(len(df)) * 0.1 - df['OLD_Momentum'] * 0.3
df['NEW_Momentum'] = df['NEW_Intra'] + df['NEW_Over']

# 4. Forward return
pr = df[['ts_code','trade_date','close']].copy().sort_values(['ts_code','trade_date'])
pr['fwd'] = pr.groupby('ts_code')['close'].pct_change().shift(-1)

m = df.merge(pr, on=['ts_code','trade_date'])

# 5. Backtest
print("\nResults:")
print("-"*50)

for fc in ['OLD_Momentum', 'NEW_Intra', 'NEW_Over', 'NEW_Momentum']:
    v = m[[fc,'fwd']].dropna()
    if len(v) < 20: continue
    
    ic, _ = stats.spearmanr(v[fc], v['fwd'])
    
    v['rank'] = v[fc].rank(pct=True)
    v['g'] = pd.cut(v['rank'], bins=[0,0.2,0.4,0.6,0.8,1], labels=[1,2,3,4,5])
    g1 = v[v['g']==1]['fwd'].mean()
    g5 = v[v['g']==5]['fwd'].mean()
    ls = g1 - g5
    ann = ls * 12 * 100
    vol = v['fwd'].std() * 312
    ir = ann / vol if vol > 0 else 0
    
    print(f"{fc:<15} IC:{ic:+.3f}  Ann:{ann:+.1f}%  IR:{ir:+.2f}")

print("-"*50)
print("SUCCESS!")

# 保存
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from pathlib import Path

output = Path(__file__).parent.parent / 'output'
output.mkdir(exist_ok=True)

df.to_csv(output / 'test_factors.csv', index=False)
pr.to_csv(output / 'test_prices.csv', index=False)

print(f"\nSaved to {output}: test_factors.csv, test_prices.csv")