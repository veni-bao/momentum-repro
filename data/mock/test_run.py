# Mock data generator - with enhanced output
import pandas as pd
import numpy as np
from scipy import stats
from pathlib import Path

np.random.seed(42)
print("=" * 50)
print("Mock Data Generator")
print("=" * 50)

# 1. Create mock data
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

# 2. Calculate OLD_Momentum
lb = 20
df['OLD_Momentum'] = df.groupby('ts_code')['ret'].transform(
    lambda g: g.rolling(lb).apply(lambda x: np.prod(1+x)-1, raw=False)
)

# 3. NEW factors
df['NEW_Intra'] = np.random.randn(len(df)) * 0.1 + df['OLD_Momentum'] * 0.5
df['NEW_Over'] = np.random.randn(len(df)) * 0.1 - df['OLD_Momentum'] * 0.3
df['NEW_Momentum'] = df['NEW_Intra'] + df['NEW_Over']

# 4. Forward return
pr = df[['ts_code','trade_date','close']].copy().sort_values(['ts_code','trade_date'])
pr['fwd'] = pr.groupby('ts_code')['close'].pct_change().shift(-1)

m = df.merge(pr, on=['ts_code','trade_date'])

# 5. Enhanced Backtest with more decimal places
print("\n" + "=" * 55)
print("                    Backtest Results")
print("=" * 55)
print(f"{'Factor':<18} {'IC':>10} {'Ann.%':>10} {'IR':>10} {'Win%':>10}")
print("-" * 55)

results = {}

for fc in ['OLD_Momentum', 'NEW_Intra', 'NEW_Over', 'NEW_Momentum']:
    v = m[[fc,'fwd']].dropna()
    if len(v) < 20: continue
    
    ic, _ = stats.spearmanr(v[fc], v['fwd'])
    
    try:
        v['rank'] = v[fc].rank(pct=True)
        v['g'] = pd.cut(v['rank'], bins=[0,0.2,0.4,0.6,0.8,1], labels=[1,2,3,4,5])
        g1 = v[v['g']==1]['fwd'].mean()
        g5 = v[v['g']==5]['fwd'].mean()
        ls = g1 - g5
        ann = ls * 12 * 100
        vol = v['fwd'].std() * np.sqrt(12) * 100
        ir = ann / vol if vol > 0 else 0
        win = (v['fwd'] > 0).mean() * 100
    except:
        ann, ir, win = 0, 0, 0
    
    # Enhanced formatting: IC to 4 decimals, others to 3
    print(f"{fc:<18} {ic:>+10.4f} {ann:>+10.3f} {ir:>+10.3f} {win:>+10.1f}")
    
    results[fc] = {
        'IC': ic,
        'Ann': ann,
        'IR': ir,
        'WinRate': win
    }

print("-" * 55)
print("SUCCESS!")

# 6. Save results to text file
output = Path(__file__).parent.parent / 'output'
output.mkdir(exist_ok=True)

# Write detailed results
with open(output / 'backtest_results.txt', 'w', encoding='utf-8') as f:
    f.write("=" * 55 + "\n")
    f.write("           Backtest Results\n")
    f.write("=" * 55 + "\n\n")
    f.write(f"{'Factor':<18} {'IC':>10} {'Ann.%':>10} {'IR':>10} {'Win%':>10}\n")
    f.write("-" * 55 + "\n")
    
    for fc, res in results.items():
        f.write(f"{fc:<18} {res['IC']:>+10.4f} {res['Ann']:>+10.3f} {res['IR']:>+10.3f} {res['WinRate']:>+10.1f}\n")
    
    f.write("-" * 55 + "\n\n")
    
    # Mock Barra correlation (random for testing)
    f.write("\n" + "=" * 55 + "\n")
    f.write("     NEW_Momentum vs Barra Style Factors\n")
    f.write("=" * 55 + "\n")
    
    barra_factors = ['Beta', 'Momentum', 'BooktoPrice', 'EarningsYield', 
                    'Growth', 'Leverage', 'ResidualVolatility', 'Liquidity', 
                    'Size', 'NonLinearSize']
    
    np.random.seed(42)
    for bf in barra_factors:
        corr = np.random.uniform(-0.1, 0.3)
        f.write(f"{bf:<20} {corr:>+10.4f}\n")
    
    f.write("\n" + "=" * 55 + "\n")
    f.write("Note: Barra correlations are simulated for testing\n")
    f.write("=" * 55 + "\n")

print(f"\nResults saved to: {output/ 'backtest_results.txt'}")

# Save CSV
df.to_csv(output / 'test_factors.csv', index=False)
pr.to_csv(output / 'test_prices.csv', index=False)