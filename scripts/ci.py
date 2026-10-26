"""Cluster-aware confidence intervals for group summaries. Measures on one state-year ballot are not independent
(same electorate, same year), so naive Wilson / t intervals are too narrow. Clusters are state-years."""
import numpy as np
from scipy import stats


def _wilson(k, n, z=1.96):
    p = k / n; den = 1 + z * z / n; c = (p + z * z / (2 * n)) / den
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return c - h, c + h


def _deff(g, col):
    """Ratio of cluster-robust SE to naive SE for the mean of g[col] (floored at 1)."""
    x = g[col].astype(float); n = len(x); mu = x.mean()
    cl = (g.state + g.year.astype(str))
    r = (x - mu).groupby(cl.values).sum()
    se_c = np.sqrt((r ** 2).sum()) / n
    se_n = x.std(ddof=1) / np.sqrt(n) if n > 1 else np.nan
    return max(1.0, se_c / se_n) if se_n and se_n > 0 else 1.0


def pass_ci(g):
    """Wilson interval on the effective sample size n / ratio^2."""
    n = len(g); k = int(g.passed.sum()); ratio = _deff(g, "passed")
    n_eff = n / ratio ** 2
    return _wilson(k / n * n_eff, n_eff)


def yes_ci(g, col="yes_pct"):
    """Mean yes share with a cluster-robust t interval (df = clusters - 1); NaN under 3 measures."""
    gg = g.dropna(subset=[col]); n = len(gg)
    if n < 3:
        return dict(mean_yes_pct=gg[col].mean() if n else float("nan"), yes_lo=float("nan"), yes_hi=float("nan"), yes_n=n)
    ratio = _deff(gg, col)
    ncl = (gg.state + gg.year.astype(str)).nunique()
    h = stats.t.ppf(0.975, max(ncl - 1, 1)) * gg[col].std(ddof=1) / n ** 0.5 * ratio
    return dict(mean_yes_pct=gg[col].mean(), yes_lo=gg[col].mean() - h, yes_hi=gg[col].mean() + h, yes_n=n)
