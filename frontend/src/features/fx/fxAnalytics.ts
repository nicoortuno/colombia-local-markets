import type { FxDailyPoint } from "../../types/fx";

export type FxRange = "1W" | "1M" | "3M" | "ALL" | "CUSTOM";

export function shiftFxDate(iso: string, period: "1W" | "1M" | "3M"): string {
  const date = new Date(`${iso}T00:00:00Z`);
  if (period === "1W") {
    date.setUTCDate(date.getUTCDate() - 7);
  } else {
    const months = period === "1M" ? 1 : 3;
    const originalDay = date.getUTCDate();
    date.setUTCDate(1);
    date.setUTCMonth(date.getUTCMonth() - months);
    const lastDayInTargetMonth = new Date(
      Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + 1, 0),
    ).getUTCDate();
    date.setUTCDate(Math.min(originalDay, lastDayInTargetMonth));
  }
  return date.toISOString().slice(0, 10);
}

/** Returns sample-standard-deviation 20-session log-return vol, annualized at 252 sessions. */
export function realizedVolatility(
  points: Pick<FxDailyPoint, "close_price">[],
  sessions = 20,
): number | null {
  if (points.length < sessions + 1 || sessions < 2) return null;
  const closes = points.slice(-(sessions + 1)).map((p) => p.close_price);
  if (closes.some((close) => !Number.isFinite(close) || close <= 0)) return null;
  const returns = closes.slice(1).map((close, index) =>
    Math.log(close / closes[index]),
  );
  const mean = returns.reduce((sum, value) => sum + value, 0) / sessions;
  const variance = returns.reduce((sum, value) => sum + (value - mean) ** 2, 0)
    / (sessions - 1);
  return Math.sqrt(variance * 252) * 100;
}

export function periodChange(
  points: Pick<FxDailyPoint, "close_price">[],
  sessions: number,
): { cop: number; pct: number } | null {
  if (points.length < sessions + 1) return null;
  const last = points[points.length - 1].close_price;
  const earlier = points[points.length - sessions - 1].close_price;
  if (!Number.isFinite(last) || !Number.isFinite(earlier) || earlier <= 0) {
    return null;
  }
  return { cop: last - earlier, pct: ((last / earlier) - 1) * 100 };
}

/** Keep vendor values untouched in the DB and table; adjust only tiny candle artifacts. */
export function displayCandle(point: FxDailyPoint, toleranceCop = 0.05): number[] | null {
  const raw = [point.open_price, point.high_price, point.low_price, point.close_price];
  if (raw.some((value) => !Number.isFinite(value) || value <= 0)) return null;
  const highShortfall = Math.max(point.open_price, point.close_price, point.low_price)
    - point.high_price;
  const lowShortfall = point.low_price
    - Math.min(point.open_price, point.close_price, point.high_price);
  if (highShortfall > toleranceCop || lowShortfall > toleranceCop) return null;
  return [
    point.open_price,
    point.close_price,
    Math.min(point.low_price, point.open_price, point.close_price),
    Math.max(point.high_price, point.open_price, point.close_price),
  ];
}

export function formatFxDate(iso: string, includeYear = false): string {
  return new Date(`${iso}T00:00:00Z`).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    ...(includeYear ? { year: "numeric" } : {}),
    timeZone: "UTC",
  });
}

export function formatCopPrice(value: number): string {
  return value.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function formatSigned(value: number | null | undefined, decimals = 2): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  return `${value > 0 ? "+" : ""}${value.toFixed(decimals)}`;
}
