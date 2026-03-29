# Main analysis script - reads from data directory
import pandas as pd
import numpy as np
from scipy import stats
from pathlib import Path
import matplotlib.pyplot as plt

# Config
DATA_DIR = Path(__file__).parent / 'data'
OUTPUT_DIR = Path(__file__).parent / 'output'
MOCK_DIR = DATA_DIR / 'mock'

# Set style
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['figure.figsize'] = (10, 6)
plt.rcParams['font.size'] = 10

def load_data(data_dir=None):
    """Load data from directory"""
    if data_dir is None:
        data_dir = MOCK_DIR
    
    factors = pd.read_csv(data_dir / 'factors.csv')
    prices = pd.read_csv(data_dir / 'prices.csv')
    
    print(f"Loaded: {len(factors)} rows")
    return factors, prices

def run_backtest(factors, prices):
    """Run backtest"""
    # Merge
    m = factors.merge(prices, on=['ts_code', 'trade_date'])
    
    results = {}
    
    for fc in ['OLD_Momentum', 'NEW_Intra', 'NEW_Over', 'NEW_Momentum']:
        if fc not in m.columns:
            continue
            
        v = m[[fc, 'fwd']].dropna()
        if len(v) < 20:
            continue
        
        # IC
        ic, _ = stats.spearmanr(v[fc], v['fwd'])
        
        # Group
        v['rank'] = v[fc].rank(pct=True)
        v['g'] = pd.cut(v['rank'], bins=[0,0.2,0.4,0.6,0.8,1], labels=[1,2,3,4,5])
        
        g1_ret = v[v['g']==1]['fwd'].mean()
        g5_ret = v[v['g']==5]['fwd'].mean()
        ls = g1_ret - g5_ret
        
        # Metrics
        ann = ls * 12 * 100
        vol = v['fwd'].std() * np.sqrt(12) * 100
        ir = ann / vol if vol > 0 else 0
        win = (v['fwd'] > 0).mean() * 100
        
        results[fc] = {'IC': ic, 'Ann': ann, 'IR': ir, 'WinRate': win}
        
    return results, m

def plot_results(results, m, output_dir):
    """Plot results"""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Factor comparison table
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.axis('off')
    
    headers = ['Factor', 'IC', 'Ann.%', 'IR', 'Win%']
    rows = []
    for fc, r in results.items():
        rows.append([fc, f"{r['IC']:+.4f}", f"{r['Ann']:+.3f}", f"{r['IR']:+.3f}", f"{r['WinRate']:+.1f}"])
    
    table = ax.table(cellText=rows, colLabels=headers, loc='center', cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1.2, 1.8)
    ax.set_title('Factor Performance Comparison', fontsize=14, pad=20)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'factor_comparison.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    # 2. IC comparison bar chart
    fig, ax = plt.subplots(figsize=(8, 5))
    
    factors = list(results.keys())
    ic_vals = [results[f]['IC'] for f in factors]
    colors = ['green' if x < 0 else 'red' for x in ic_vals]
    
    ax.barh(factors, ic_vals, color=colors, alpha=0.7)
    ax.axvline(x=0, color='black', linewidth=0.5)
    ax.set_xlabel('IC')
    ax.set_title('IC Comparison')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'ic_comparison.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    # 3. 5-group net value trend (simulated)
    fig, ax = plt.subplots(figsize=(10, 5))
    
    # Simulated net value trend
    np.random.seed(42)
    days = np.arange(50)
    
    for g, color in [(1, 'red'), (3, 'gray'), (5, 'green')]:
        # Simulated net value
        net_value = 1 + np.cumsum(np.random.randn(50) * 0.01)
        ax.plot(days, net_value, label=f'Group {g}', color=color, linewidth=1.5)
    
    ax.axhline(y=1, color='black', linestyle='--', linewidth=0.5)
    ax.set_xlabel('Days')
    ax.set_ylabel('Net Value')
    ax.set_title('5-Group Net Value Trend (Simulated)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'group_net_value.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Plots saved to {output_dir}")

def save_results_text(results, output_dir):
    """Save text results"""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(output_dir / 'backtest_results.txt', 'w', encoding='utf-8') as f:
        f.write("=" * 55 + "\n")
        f.write("           Backtest Results\n")
        f.write("=" * 55 + "\n\n")
        
        f.write(f"{'Factor':<18} {'IC':>10} {'Ann.%':>10} {'IR':>10} {'Win%':>10}\n")
        f.write("-" * 55 + "\n")
        
        for fc, r in results.items():
            f.write(f"{fc:<18} {r['IC']:>+10.4f} {r['Ann']:>+10.3f} {r['IR']:>+10.3f} {r['WinRate']:>+10.1f}\n")
        
        f.write("-" * 55 + "\n\n")
        
        # Barra correlation (simulated)
        f.write("\n" + "=" * 55 + "\n")
        f.write("     NEW_Momentum vs Barra Style Factors\n")
        f.write("=" * 55 + "\n\n")
        
        barra_factors = ['Beta', 'Momentum', 'BooktoPrice', 'EarningsYield', 
                        'Growth', 'Leverage', 'ResidualVolatility', 'Liquidity', 
                        'Size', 'NonLinearSize']
        
        np.random.seed(42)
        for bf in barra_factors:
            corr = np.random.uniform(-0.1, 0.3)
            f.write(f"{bf:<20} {corr:>+10.4f}\n")
        
        f.write("\n" + "=" * 55 + "\n")
        f.write("Note: Barra correlations are simulated for testing\n")
    
    print(f"Results saved to {output_dir / 'backtest_results.txt'}")

def main():
    print("=" * 50)
    print("Momentum Factor Analysis")
    print("=" * 50)
    
    # 1. Generate mock data if not exists
    if not MOCK_DIR.exists() or not list(MOCK_DIR.glob('*.csv')):
        print("\n[1/5] Generating mock data...")
        from data.mock import generate_mock_data
        generate_mock_data(output_dir=MOCK_DIR)
    else:
        print("\n[1/5] Using existing data...")
    
    # 2. Load data
    print("\n[2/5] Loading data...")
    factors, prices = load_data()
    
    # 3. Run backtest
    print("\n[3/5] Running backtest...")
    results, merged = run_backtest(factors, prices)
    
    # 4. Save text results
    print("\n[4/5] Saving text results...")
    save_results_text(results, OUTPUT_DIR)
    
    # 5. Generate plots
    print("\n[5/5] Generating plots...")
    plot_results(results, merged, OUTPUT_DIR)
    
    print("\n" + "=" * 50)
    print("DONE!")
    print("=" * 50)
    print(f"\nOutput: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()