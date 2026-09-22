export interface TesCurvePoint {
  security_id: string;
  maturity_date: string;

  close_price: number | null;
  close_yield: number | null;

  change_1d_bp: number | null;
  change_5d_bp: number | null;

  nominal_volume_cop_mn: number;
  trade_count: number;
}

export interface TesCurveResponse {
  trade_date: string;
  latest_date: string;
  previous_date: string | null;
  next_date: string | null;
  available_dates: string[];
  points: TesCurvePoint[];
}
