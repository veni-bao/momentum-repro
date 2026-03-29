# -*- coding: utf-8 -*-
"""
Numba JIT speed test
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import time

print("=" * 50)
print("Numba JIT Test")
print("=" * 50)

# Test 1: Check numba
print("\n[Test 1] Check numba availability...")
try:
    from numba import jit, __version__
    print(f"OK: Numba version: {__version__}")
    numba_ok = True
except ImportError as e:
    print(f"FAIL: Numba not installed: {e}")
    print("Install: pip install numba")
    numba_ok = False
    sys.exit(1)

# Test 2: Simple JIT
print("\n[Test 2] Simple JIT function...")
try:
    @jit(nopython=True)
    def sum_arrays(arr):
        total = 0.0
        for i in range(len(arr)):
            total += arr[i]
        return total
    
    test_arr = [1.0] * 1000
    _ = sum_arrays(test_arr)
    print("OK: Simple JIT compiled")
except Exception as e:
    print(f"FAIL: JIT compile error: {e}")
    sys.exit(1)

# Test 3: Performance
print("\n[Test 3] Performance comparison...")
import numpy as np

n = 10_000_000
arr = np.random.randn(n)

@jit(nopython=True)
def numba_sum(arr):
    total = 0.0
    for i in range(len(arr)):
        total += arr[i]
    return total

# Warmup
_ = numba_sum(arr)

results = {}

# NumPy
start = time.time()
numpy_result = np.sum(arr)
results['NumPy'] = time.time() - start

# Numba
start = time.time()
numba_result = numba_sum(arr)
results['Numba'] = time.time() - start

print(f"\nArray size: {n:,}")
print(f"Results: NumPy={numpy_result:.2f}, Numba={numba_result:.2f}")
print("\nTime:")
for method, t in results.items():
    print(f"  {method}: {t:.4f}s")

speedup = results['NumPy'] / results['Numba']
print(f"\nSpeedup: {speedup:.1f}x")

if speedup > 2:
    print("OK: Good speedup")
else:
    print("WARN: Low speedup, consider NumPy only")

# Test 4: Cumulative return
print("\n" + "=" * 50)
print("[Test 4] Cumulative return (factor core)")
print("=" * 50)

def calc_cumprod_python(returns):
    result = np.empty(len(returns))
    prod = 1.0
    for i in range(len(returns)):
        prod *= (1 + returns[i])
        result[i] = prod - 1
    return result

@jit(nopython=True)
def calc_cumprod_numba(returns):
    result = np.empty(len(returns))
    prod = 1.0
    for i in range(len(returns)):
        prod *= (1.0 + returns[i])
        result[i] = prod - 1.0
    return result

returns = np.random.randn(n) * 0.01
_ = calc_cumprod_numba(returns)

start = time.time()
python_cum = calc_cumprod_python(returns)
t_python = time.time() - start

start = time.time()
numba_cum = calc_cumprod_numba(returns)
t_numba = time.time() - start

print(f"\nCumulative return ({n:,} days)")
print(f"  Python: {t_python:.4f}s")
print(f"  Numba:  {t_numba:.4f}s")
print(f"  Speedup: {t_python/t_numba:.1f}x")

diff = np.max(np.abs(python_cum - numba_cum))
print(f"  Diff: {diff:.2e}")

if diff < 1e-10:
    print("OK: Results match")
else:
    print("FAIL: Results mismatch!")

print("\n" + "=" * 50)
print("ALL TESTS COMPLETE!")
print("=" * 50)
