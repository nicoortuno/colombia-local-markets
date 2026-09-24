import type { MacroObservationPoint } from "../../types/macro";

export type MacroRange = "1Y" | "3Y" | "5Y" | "ALL";

export function formatMacroDate(isoDate: string, monthOnly = false): string {
  const date = new Date(`${isoDate}T00:00:00Z`);
  return date.toLocaleDateString("en-US", {
    month: "short",
    ...(monthOnly ? {} : { day: "2-digit" }),
    year: "numeric",
    timeZone: "UTC",
  });
}

export function formatQuarter(isoDate: string): string {
  const date = new Date(`${isoDate}T00:00:00Z`);
  const quarter = Math.floor(date.getUTCMonth() / 3) + 1;
  return `Q${quarter} ${date.getUTCFullYear()}`;
}

export function shiftMacroDate(latestDate: string, range: Exclude<MacroRange, "ALL">): string {
  const date = new Date(`${latestDate}T00:00:00Z`);
  const years = range === "1Y" ? 1 : range === "3Y" ? 3 : 5;
  date.setUTCFullYear(date.getUTCFullYear() - years);
  return date.toISOString().slice(0, 10);
}

export function filterMacroPoints(
  points: MacroObservationPoint[],
  startDate: string,
  endDate: string,
): MacroObservationPoint[] {
  return points.filter(
    (point) => point.observation_date >= startDate && point.observation_date <= endDate,
  );
}

export function deriveGdpYoy(points: MacroObservationPoint[]): MacroObservationPoint[] {
  const byDate = new Map(points.map((point) => [point.observation_date, point.value]));

  return points.flatMap((point) => {
    const date = new Date(`${point.observation_date}T00:00:00Z`);
    date.setUTCFullYear(date.getUTCFullYear() - 1);
    const priorDate = date.toISOString().slice(0, 10);
    const priorValue = byDate.get(priorDate);

    if (priorValue === undefined || priorValue === 0) {
      return [];
    }

    return [{
      observation_date: point.observation_date,
      value: (point.value / priorValue - 1) * 100,
    }];
  });
}

export function reservesToUsdBn(points: MacroObservationPoint[]): MacroObservationPoint[] {
  return points.map((point) => ({
    observation_date: point.observation_date,
    value: point.value / 1000,
  }));
}

export function signed(value: number, decimals = 2): string {
  return `${value > 0 ? "+" : ""}${value.toFixed(decimals)}`;
}
