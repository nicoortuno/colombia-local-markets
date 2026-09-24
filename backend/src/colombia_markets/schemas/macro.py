"""Public response schemas for official Colombian macro data."""

from datetime import date

from pydantic import BaseModel, Field


class MacroObservationPoint(BaseModel):
    observation_date: date
    value: float


class MacroSeriesSummary(BaseModel):
    series_key: str
    series_name: str
    frequency: str
    unit: str
    source: str
    provider: str
    latest_date: date
    latest_value: float
    previous_date: date | None = None
    previous_value: float | None = None
    change_abs: float | None = None
    change_pct: float | None = None


class MacroSeriesCatalogResponse(BaseModel):
    series: list[MacroSeriesSummary] = Field(default_factory=list)


class MacroSeriesHistoryResponse(BaseModel):
    series_key: str
    series_name: str
    frequency: str
    unit: str
    source: str
    provider: str
    latest_date: date
    start_date: date
    end_date: date
    points: list[MacroObservationPoint] = Field(default_factory=list)


class MacroSnapshotMetric(BaseModel):
    value: float
    observation_date: date
    unit: str
    source: str


class MacroDerivedMetric(BaseModel):
    value: float
    observation_date: date
    unit: str
    source: str = "calculated"
    comparison_date: date | None = None


class MacroSnapshotResponse(BaseModel):
    as_of_date: date
    policy_rate: MacroSnapshotMetric
    ibr_overnight: MacroSnapshotMetric
    ibr_policy_spread_bp: MacroDerivedMetric
    headline_inflation: MacroSnapshotMetric
    core_inflation: MacroSnapshotMetric
    unemployment: MacroSnapshotMetric
    real_gdp_yoy: MacroDerivedMetric
    current_account_gdp: MacroSnapshotMetric
    net_reserves: MacroSnapshotMetric
    net_reserves_usd_bn: MacroDerivedMetric
