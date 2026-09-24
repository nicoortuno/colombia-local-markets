/** Matches the existing FastAPI /fx/usdcop/* response contracts. */
export interface FxDailyPoint {
  trade_date: string;
  open_price: number;
  high_price: number;
  low_price: number;
  close_price: number;
  change_1d_cop: number | null;
  change_1d_pct: number | null;
}

export interface FxHistoryResponse {
  pair: string;
  source: string;
  latest_date: string;
  points: FxDailyPoint[];
}
