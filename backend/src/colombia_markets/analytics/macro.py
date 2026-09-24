"""Pure macro calculations used by the API service layer."""


def basis_point_spread(rate_pct: float, benchmark_pct: float) -> float:
    """Return rate minus benchmark in basis points when inputs are percent rates."""
    return round((rate_pct - benchmark_pct) * 100, 3)


def year_over_year_growth(latest_level: float, prior_year_level: float) -> float:
    """Calculate percent growth versus the same period one year earlier."""
    if prior_year_level == 0:
        raise ValueError("prior-year level must be non-zero")
    return round((latest_level / prior_year_level - 1) * 100, 6)


def usd_mn_to_bn(value_usd_mn: float) -> float:
    return round(value_usd_mn / 1000, 6)
