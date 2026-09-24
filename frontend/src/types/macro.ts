export interface MacroObservationPoint {
  observation_date: string;
  value: number;
}

export interface MacroSeriesSummary {
  series_key: string;
  series_name: string;
  frequency: string;
  unit: string;
  source: string;
  provider: string;
  latest_date: string;
  latest_value: number;
  previous_date: string | null;
  previous_value: number | null;
  change_abs: number | null;
  change_pct: number | null;
}

export interface MacroSeriesCatalogResponse {
  series: MacroSeriesSummary[];
}

export interface MacroSeriesHistoryResponse {
  series_key: string;
  series_name: string;
  frequency: string;
  unit: string;
  source: string;
  provider: string;
  latest_date: string;
  start_date: string;
  end_date: string;
  points: MacroObservationPoint[];
}

export interface MacroSnapshotMetric {
  value: number;
  observation_date: string;
  unit: string;
  source: string;
}

export interface MacroDerivedMetric extends MacroSnapshotMetric {
  comparison_date: string | null;
}

export interface MacroSnapshotResponse {
  as_of_date: string;
  policy_rate: MacroSnapshotMetric;
  ibr_overnight: MacroSnapshotMetric;
  ibr_policy_spread_bp: MacroDerivedMetric;
  headline_inflation: MacroSnapshotMetric;
  core_inflation: MacroSnapshotMetric;
  unemployment: MacroSnapshotMetric;
  real_gdp_yoy: MacroDerivedMetric;
  current_account_gdp: MacroSnapshotMetric;
  net_reserves: MacroSnapshotMetric;
  net_reserves_usd_bn: MacroDerivedMetric;
}

export type MacroSeriesKey =
  | "policy_rate"
  | "ibr_overnight"
  | "headline_inflation"
  | "core_inflation"
  | "real_gdp"
  | "unemployment"
  | "current_account_gdp"
  | "net_reserves";
