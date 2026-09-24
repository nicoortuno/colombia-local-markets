import { useMemo, useState, type ChangeEvent } from "react";
import {
  Activity,
  ArrowLeftRight,
  CalendarDays,
  CandlestickChart,
  LineChart,
} from "lucide-react";

import type { FxDailyPoint } from "../../types/fx";
import { FxPriceChart, type FxChartMode } from "./FxPriceChart";
import {
  type FxRange,
  formatCopPrice,
  formatFxDate,
  formatSigned,
  periodChange,
  realizedVolatility,
  shiftFxDate,
} from "./fxAnalytics";
import { useFxHistory } from "./useFxHistory";

const EMPTY_POINTS: FxDailyPoint[] = [];

function fxMoveClass(value: number | null | undefined): string {
  if (value === null || value === undefined || Math.abs(value) < 0.000001) return "move-flat";
  // Rising USD/COP means a weaker COP, so higher values are red.
  return value > 0 ? "move-up" : "move-down";
}

function FxDailyTable({ points }: { points: FxDailyPoint[] }) {
  return (
    <div className="fx-table-wrap">
      <table className="fx-table">
        <thead>
          <tr>
            <th>Date</th>
            <th>Open</th>
            <th>High</th>
            <th>Low</th>
            <th>Close</th>
            <th>1D COP</th>
            <th>1D %</th>
          </tr>
        </thead>
        <tbody>
          {[...points].reverse().map((point) => (
            <tr key={point.trade_date}>
              <td className="fx-table-date">
                {formatFxDate(point.trade_date, true)}
              </td>
              <td>{formatCopPrice(point.open_price)}</td>
              <td>{formatCopPrice(point.high_price)}</td>
              <td>{formatCopPrice(point.low_price)}</td>
              <td className="fx-table-close">{formatCopPrice(point.close_price)}</td>
              <td className={fxMoveClass(point.change_1d_cop)}>
                {formatSigned(point.change_1d_cop)}
              </td>
              <td className={fxMoveClass(point.change_1d_pct)}>
                {point.change_1d_pct === null
                  ? "—"
                  : `${formatSigned(point.change_1d_pct, 3)}%`}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function FxPage() {
  const { data, isLoading, isError } = useFxHistory();
  const points = data?.points ?? EMPTY_POINTS;
  const [chartMode, setChartMode] = useState<FxChartMode>("line");
  const [range, setRange] = useState<FxRange>("1M");
  const [customStart, setCustomStart] = useState("");
  const [customEnd, setCustomEnd] = useState("");

  const latest = points.length > 0 ? points[points.length - 1] : undefined;
  const earliestDate = points[0]?.trade_date;
  const latestDate = latest?.trade_date;

  const fiveDay = useMemo(() => periodChange(points, 5), [points]);
  const twentyDayVol = useMemo(() => realizedVolatility(points, 20), [points]);
  const twentyDayRange = useMemo(() => {
    const lastTwenty = points.slice(-20);
    return lastTwenty.length === 20
      ? {
          low: Math.min(...lastTwenty.map((point) => point.low_price)),
          high: Math.max(...lastTwenty.map((point) => point.high_price)),
        }
      : null;
  }, [points]);

  const effectiveEnd = latestDate
    ? range === "CUSTOM" && customEnd
      ? customEnd
      : latestDate
    : "";
  const requestedStart = latestDate
    ? range === "ALL"
      ? (earliestDate ?? latestDate)
      : range === "CUSTOM"
        ? (customStart || shiftFxDate(effectiveEnd, "1M"))
        : shiftFxDate(effectiveEnd, range)
    : "";
  const effectiveStart = earliestDate && requestedStart < earliestDate
    ? earliestDate
    : requestedStart;

  const selectedPoints = useMemo(
    () => points.filter((point) =>
      point.trade_date >= effectiveStart && point.trade_date <= effectiveEnd,
    ),
    [points, effectiveStart, effectiveEnd],
  );

  const selectedStart = selectedPoints[0];
  const selectedEnd = selectedPoints[selectedPoints.length - 1];
  const selectedMove = selectedStart && selectedEnd && selectedStart.close_price > 0
    ? ((selectedEnd.close_price / selectedStart.close_price) - 1) * 100
    : null;

  const handleCustomStart = (nextDate: string) => {
    setCustomStart(nextDate);
    setCustomEnd((current) => current && current < nextDate ? nextDate : current);
    setRange("CUSTOM");
  };

  const handleCustomEnd = (nextDate: string) => {
    setCustomEnd(nextDate);
    if (nextDate) {
      setCustomStart((current) => {
        const fallback = shiftFxDate(nextDate, "1M");
        const proposed = current || (earliestDate && fallback < earliestDate ? earliestDate : fallback);
        return proposed > nextDate ? nextDate : proposed;
      });
    }
    setRange("CUSTOM");
  };

  return (
    <>
      <header className="topbar">
        <div>
          <p className="eyebrow">COLOMBIA LOCAL MARKETS</p>
          <h1>FX · USD/COP</h1>
        </div>
        <div className="market-status">
          <span className="status-dot"/>
          <span>YAHOO DAILY CLOSE</span>
          <strong>{latestDate ? formatFxDate(latestDate, true).toUpperCase() : "—"}</strong>
        </div>
      </header>

      <section className="content fx-content">
        {isLoading && <div className="loading">Loading USD/COP daily market data…</div>}
        {isError && (
          <div className="error-card">
            Unable to retrieve USD/COP history. Check that the FastAPI server is running and
            that the FX backfill has been loaded.
          </div>
        )}

        {data && latest && (
          <>
            <div className="fx-page-intro">
              <span className="fx-kicker">USD/COP SPOT · COP PER USD</span>
              <span className="fx-source-note">
                Daily vendor observations · <strong>Yahoo Finance COP=X</strong> · Not a live quote or official Colombian close
              </span>
            </div>

            <div className="metric-grid fx-metric-grid">
              <div className="metric-card">
                <span className="metric-label">Latest USD/COP Close</span>
                <div className="metric-value-row fx-value-row">
                  <strong>{formatCopPrice(latest.close_price)}</strong>
                  <span className={`metric-move ${fxMoveClass(latest.change_1d_pct)}`}>
                    {formatSigned(latest.change_1d_pct, 3)}%
                  </span>
                </div>
                <span className="metric-note">
                  {formatFxDate(latest.trade_date, true)} · 1D {formatSigned(latest.change_1d_cop)} COP
                </span>
              </div>

              <div className="metric-card">
                <span className="metric-label">5D USD/COP Move</span>
                <div className="metric-value-row">
                  <strong className={fxMoveClass(fiveDay?.pct)}>
                    {fiveDay ? `${formatSigned(fiveDay.pct, 2)}%` : "—"}
                  </strong>
                </div>
                <span className="metric-note">
                  {fiveDay ? `${formatSigned(fiveDay.cop)} COP · five FX sessions` : "Requires six closes"}
                </span>
              </div>

              <div className="metric-card">
                <span className="metric-label">20D Realized Vol</span>
                <div className="metric-value-row">
                  <strong>{twentyDayVol !== null ? `${twentyDayVol.toFixed(2)}%` : "—"}</strong>
                </div>
                <span className="metric-note">Log returns · annualized at 252 sessions</span>
              </div>

              <div className="metric-card">
                <span className="metric-label">20D Trading Range</span>
                <strong className="fx-range-value">
                  {twentyDayRange
                    ? `${formatCopPrice(twentyDayRange.low)} – ${formatCopPrice(twentyDayRange.high)}`
                    : "—"}
                </strong>
                <span className="metric-note">Daily reported lows / highs · last 20 sessions</span>
              </div>
            </div>

            <section className="panel fx-panel">
              <div className="panel-header fx-panel-header">
                <div>
                  <div className="panel-title-row">
                    <ArrowLeftRight size={18}/>
                    <h2>USD/COP Historical Prices</h2>
                  </div>
                  <p>Daily vendor spot data · USD/COP rises when the Colombian peso depreciates</p>
                </div>
                <div className="curve-controls fx-controls">
                  <div className="comparison-controls" aria-label="Chart range">
                    {(["1W", "1M", "3M", "ALL"] as const).map((period) => (
                      <button
                        type="button"
                        key={period}
                        className={`range-button${range === period ? " active" : ""}`}
                        onClick={() => setRange(period)}
                        disabled={period !== "ALL" && Boolean(
                          earliestDate && latestDate && earliestDate > shiftFxDate(latestDate, period)
                        )}
                        title={period !== "ALL" && earliestDate && latestDate && earliestDate > shiftFxDate(latestDate, period)
                          ? `History before ${earliestDate} is required for ${period}`
                          : undefined}
                        aria-pressed={range === period}
                      >
                        {period === "ALL" ? "All" : period}
                      </button>
                    ))}
                    <button
                      type="button"
                      className={`range-button${range === "CUSTOM" ? " active" : ""}`}
                      onClick={() => {
                        setCustomEnd((current) => current || latestDate || "");
                        setCustomStart((current) => current || effectiveStart);
                        setRange("CUSTOM");
                      }}
                      aria-pressed={range === "CUSTOM"}
                    >
                      Custom
                    </button>
                  </div>
                  <div className="fx-chart-mode" role="group" aria-label="Chart display">
                    <button
                      type="button"
                      className={`fx-mode-button${chartMode === "line" ? " active" : ""}`}
                      onClick={() => setChartMode("line")}
                      aria-pressed={chartMode === "line"}
                      title="Daily closing prices"
                    >
                      <LineChart size={14}/> Line
                    </button>
                    <button
                      type="button"
                      className={`fx-mode-button${chartMode === "candles" ? " active" : ""}`}
                      onClick={() => setChartMode("candles")}
                      aria-pressed={chartMode === "candles"}
                      title="Daily open / high / low / close"
                    >
                      <CandlestickChart size={14}/> Candles
                    </button>
                  </div>
                </div>
              </div>
              <div className="fx-date-toolbar">
                <div className="fx-custom-dates">
                  <CalendarDays size={13}/>
                  <label>
                    From
                    <input
                      type="date"
                      aria-label="FX start date"
                      min={earliestDate}
                      max={effectiveEnd}
                      value={effectiveStart}
                      onChange={(event: ChangeEvent<HTMLInputElement>) => handleCustomStart(event.target.value)}
                    />
                  </label>
                  <label>
                    To
                    <input
                      type="date"
                      aria-label="FX end date"
                      min={effectiveStart}
                      max={latestDate}
                      value={effectiveEnd}
                      onChange={(event: ChangeEvent<HTMLInputElement>) => handleCustomEnd(event.target.value)}
                    />
                  </label>
                </div>
                <span className="fx-period-summary">
                  {selectedPoints.length} sessions
                  {selectedMove !== null && (
                    <span className={fxMoveClass(selectedMove)}>
                      &nbsp;· {formatSigned(selectedMove, 2)}% over selected range
                    </span>
                  )}
                </span>
              </div>

              <div className="curve-chart fx-chart">
                <FxPriceChart points={selectedPoints} mode={chartMode}/>
              </div>

              <div className="table-section-header">
                <div>
                  <h3>Daily FX Monitor</h3>
                  <span>Yahoo-reported daily OHLC, newest session first · raw vendor values retained</span>
                </div>
                <span className="table-count">{selectedPoints.length} sessions</span>
              </div>
              {selectedPoints.length > 0
                ? <FxDailyTable points={selectedPoints}/>
                : <div className="fx-chart-empty">No USD/COP sessions in the selected period.</div>}
            </section>
            <div className="fx-disclaimer">
              <Activity size={14}/>
              <span>
                Yahoo's COP=X prices are vendor-defined daily FX observations, not SET-FX closing prints or the official TRM.
                Holiday coverage may differ from Colombia's TES trading calendar.
              </span>
            </div>
          </>
        )}
      </section>
    </>
  );
}
