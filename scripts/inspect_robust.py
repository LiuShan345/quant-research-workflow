import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

import backtest as bt
import data as d
import signals as s
from common import load_config

cfg = load_config()
prices = d.load_prices()
wide = d.to_wide(prices)
bps = cfg["execution"]["one_way_cost_bps"]
for lb, k in [(3, 3), (9, 3), (6, 2), (6, 5), (6, 3)]:
    sig = s.build_signals(wide, lb, k)
    _, _, m, _ = bt.run_backtest(wide, sig, bps)
    print(f"lookback={lb} top_k={k}: ann={m['annualized_return']:.4f} sharpe={m['sharpe_ratio']:.3f} maxdd={m['max_drawdown']:.4f}")
