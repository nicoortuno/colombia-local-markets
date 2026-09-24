import pytest

from colombia_markets.analytics.macro import (
    basis_point_spread,
    usd_mn_to_bn,
    year_over_year_growth,
)


def test_macro_calculations():
    assert basis_point_spread(12.002, 12.0) == pytest.approx(0.2)
    assert year_over_year_growth(256893.7, 248150.38) == pytest.approx(3.5234, rel=1e-4)
    assert usd_mn_to_bn(67816.9) == pytest.approx(67.8169)
