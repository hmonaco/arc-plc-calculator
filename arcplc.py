"""ARC-CO and PLC payment calculations (2026 crop year, OBBBA rules).

All payments are returned in $ per BASE acre, i.e. already multiplied by the
85% payment-acre factor.

ARC-CO
    benchmark revenue  = benchmark yield x benchmark price
    guarantee          = 90% x benchmark revenue
    actual revenue     = actual county yield x max(MYA price, loan rate)
    payment rate       = min(max(guarantee - actual revenue, 0), 12% x benchmark revenue)
PLC
    payment rate       = max(effective ref. price - max(MYA price, loan rate), 0) x PLC yield
"""
from __future__ import annotations

import numpy as np

PAYMENT_ACRE_FACTOR = 0.85
ARC_GUARANTEE = 0.90
ARC_MAX_RATE = 0.12


def arc_co_payment(actual_yield, mya_price, bench_yield, bench_price, loan_rate,
                   guarantee=ARC_GUARANTEE, max_rate=ARC_MAX_RATE,
                   pay_factor=PAYMENT_ACRE_FACTOR):
    """ARC-CO payment, $/base acre. Works on scalars or numpy arrays."""
    bench_rev = bench_yield * bench_price
    actual_rev = np.asarray(actual_yield) * np.maximum(mya_price, loan_rate)
    shortfall = np.clip(guarantee * bench_rev - actual_rev, 0, max_rate * bench_rev)
    return shortfall * pay_factor


def plc_payment(mya_price, eff_ref_price, loan_rate, plc_yield,
                pay_factor=PAYMENT_ACRE_FACTOR):
    """PLC payment, $/base acre. Works on scalars or numpy arrays."""
    rate = np.maximum(eff_ref_price - np.maximum(mya_price, loan_rate), 0)
    return rate * plc_yield * pay_factor


def sensitivity(bench_yield, bench_price, eff_ref_price, loan_rate, plc_yield,
                yields, prices):
    """Return (arc_grid, plc_row) for a yield x price grid.

    arc_grid[i, j] = ARC-CO payment at yields[i], prices[j]
    plc_row[j]     = PLC payment at prices[j] (PLC does not depend on county yield)
    """
    Y, P = np.meshgrid(np.asarray(yields, float), np.asarray(prices, float), indexing="ij")
    arc = arc_co_payment(Y, P, bench_yield, bench_price, loan_rate)
    plc = plc_payment(np.asarray(prices, float), eff_ref_price, loan_rate, plc_yield)
    return arc, plc
