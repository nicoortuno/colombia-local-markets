import {
  Activity,
  BarChart3,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  CircleDollarSign,
  Database,
  Landmark,
  LineChart,
} from "lucide-react";
import {
  useMemo,
  useState,
  type ChangeEvent,
} from "react";
import { BrowserRouter, NavLink, Route, Routes, Navigate } from "react-router-dom";

import { TesYieldCurve } from "./features/rates/TesYieldCurve";
import { FxPage } from "./features/fx/FxPage";
import { MacroPage } from "./features/macro/MacroPage";
import { useTesCurve } from "./features/rates/useTesCurve";
import type {
  TesCurvePoint,
} from "./types/rates";


type ComparisonRange =
  | "1W"
  | "1M"
  | "3M"
  | null;


function formatDateDisplay(
  isoDate: string,
): string {
  const date = new Date(
    `${isoDate}T00:00:00Z`,
  );

  return date
    .toLocaleDateString(
      "en-US",
      {
        day: "2-digit",
        month: "short",
        year: "numeric",
        timeZone: "UTC",
      },
    )
    .toUpperCase();
}


function formatMaturity(
  isoDate: string,
): string {
  const date = new Date(
    `${isoDate}T00:00:00Z`,
  );

  return date.toLocaleDateString(
    "en-US",
    {
      month: "short",
      year: "2-digit",
      timeZone: "UTC",
    },
  );
}


function formatCopMillions(
  valueCopMn: number,
): string {
  if (valueCopMn >= 1_000_000) {
    return `COP ${(valueCopMn / 1_000_000).toFixed(2)}tn`;
  }

  if (valueCopMn >= 1_000) {
    return `COP ${(valueCopMn / 1_000).toFixed(1)}bn`;
  }

  return `COP ${valueCopMn.toFixed(0)}mm`;
}


function formatBp(
  value: number | null,
): string {
  if (value === null) {
    return "—";
  }

  return `${value > 0 ? "+" : ""}${value.toFixed(1)}bp`;
}


function bpClass(
  value: number | null,
): string {
  if (value === null || value === 0) {
    return "move-flat";
  }

  return value > 0
    ? "move-up"
    : "move-down";
}


function shiftDate(
  isoDate: string,
  range: Exclude<ComparisonRange, null>,
): string {
  const date = new Date(
    `${isoDate}T00:00:00Z`,
  );

  if (range === "1W") {
    date.setUTCDate(
      date.getUTCDate() - 7,
    );
  }

  if (range === "1M") {
    date.setUTCMonth(
      date.getUTCMonth() - 1,
    );
  }

  if (range === "3M") {
    date.setUTCMonth(
      date.getUTCMonth() - 3,
    );
  }

  return date
    .toISOString()
    .slice(0, 10);
}


function findComparisonDate(
  currentDate: string,
  availableDates: string[],
  range: Exclude<ComparisonRange, null>,
): string | null {
  const targetDate = shiftDate(
    currentDate,
    range,
  );

  const eligibleDates = availableDates.filter(
    (availableDate) =>
      availableDate <= targetDate &&
      availableDate < currentDate,
  );

  return eligibleDates.length > 0
    ? eligibleDates[
        eligibleDates.length - 1
      ]
    : null;
}


function findClosestTenorPoint(
  tradeDate: string,
  points: TesCurvePoint[],
  tenorYears: number,
): TesCurvePoint | undefined {
  const targetMaturity = new Date(
    `${tradeDate}T00:00:00Z`,
  );

  targetMaturity.setUTCFullYear(
    targetMaturity.getUTCFullYear() + tenorYears,
  );

  const targetTime = targetMaturity.getTime();

  return points
    .filter(
      (point) => point.close_yield !== null,
    )
    .reduce<TesCurvePoint | undefined>(
      (closest, point) => {
        if (!closest) {
          return point;
        }

        const pointDistance = Math.abs(
          new Date(
            `${point.maturity_date}T00:00:00Z`,
          ).getTime() - targetTime,
        );

        const closestDistance = Math.abs(
          new Date(
            `${closest.maturity_date}T00:00:00Z`,
          ).getTime() - targetTime,
        );

        return pointDistance < closestDistance
          ? point
          : closest;
      },
      undefined,
    );
}


function tenorMoveBp(
  latestPoint: TesCurvePoint | undefined,
  selectedPoint: TesCurvePoint | undefined,
  isHistoricalDate: boolean,
): number | null {
  if (!latestPoint || latestPoint.close_yield === null) {
    return null;
  }

  if (!isHistoricalDate) {
    return latestPoint.change_1d_bp;
  }

  if (!selectedPoint || selectedPoint.close_yield === null) {
    return null;
  }

  return Number(
    (
      (latestPoint.close_yield - selectedPoint.close_yield) * 100
    ).toFixed(1),
  );
}


function MetricMove({
  value,
}: {
  value: number | null;
}) {
  return (
    <span
      className={`metric-move ${bpClass(value)}`}
    >
      {formatBp(value)}
    </span>
  );
}


function BondTable({
  points,
  selectedSecurityId,
  onSelectSecurity,
}: {
  points: TesCurvePoint[];
  selectedSecurityId: string | null;
  onSelectSecurity: (securityId: string) => void;
}) {
  return (
    <div className="bond-table-wrap">
      <table className="bond-table">
        <thead>
          <tr>
            <th>Maturity</th>
            <th>Yield</th>
            <th>1D</th>
            <th>5D</th>
            <th>Price</th>
            <th>Volume</th>
            <th>Trades</th>
          </tr>
        </thead>

        <tbody>
          {points.map((point) => (
            <tr
              key={point.security_id}
              className={
                point.security_id === selectedSecurityId
                  ? "selected"
                  : ""
              }
              onClick={() =>
                onSelectSecurity(
                  point.security_id,
                )
              }
            >
              <td>
                <div className="bond-maturity">
                  {formatMaturity(
                    point.maturity_date,
                  )}
                </div>
                <div className="bond-security-id">
                  {point.security_id}
                </div>
              </td>

              <td className="number-cell yield-cell">
                {point.close_yield !== null
                  ? `${point.close_yield.toFixed(3)}%`
                  : "—"}
              </td>

              <td
                className={`number-cell ${bpClass(point.change_1d_bp)}`}
              >
                {formatBp(
                  point.change_1d_bp,
                )}
              </td>

              <td
                className={`number-cell ${bpClass(point.change_5d_bp)}`}
              >
                {formatBp(
                  point.change_5d_bp,
                )}
              </td>

              <td className="number-cell">
                {point.close_price !== null
                  ? point.close_price.toFixed(3)
                  : "—"}
              </td>

              <td className="number-cell">
                {formatCopMillions(
                  point.nominal_volume_cop_mn,
                )}
              </td>

              <td className="number-cell">
                {point.trade_count.toLocaleString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}


function RatesPage() {
  const [selectedDate, setSelectedDate] =
    useState<string>();
  const [selectedSecurityId, setSelectedSecurityId] =
    useState<string | null>(null);
  const [comparisonRange, setComparisonRange] =
    useState<ComparisonRange>(null);

  const {
    data,
    isLoading,
    isError,
  } = useTesCurve(selectedDate);

  const {
    data: latestData,
  } = useTesCurve();

  const isHistoricalDate = Boolean(
    data && data.trade_date !== data.latest_date,
  );

  const comparisonDate = useMemo(() => {
    if (!data) {
      return null;
    }

    // Historical views always keep the latest SEN close on screen
    // as the reference curve. On the latest date, a second curve
    // appears only when the user explicitly selects a range.
    if (data.trade_date !== data.latest_date) {
      return data.latest_date;
    }

    if (!comparisonRange) {
      return null;
    }

    return findComparisonDate(
      data.trade_date,
      data.available_dates,
      comparisonRange,
    );
  }, [
    data,
    comparisonRange,
  ]);

  const {
    data: comparisonData,
  } = useTesCurve(
    comparisonDate ?? undefined,
    Boolean(comparisonDate),
  );

  const latestTwoYearPoint = latestData
    ? findClosestTenorPoint(
        latestData.trade_date,
        latestData.points,
        2,
      )
    : undefined;

  const latestTenYearPoint = latestData
    ? findClosestTenorPoint(
        latestData.trade_date,
        latestData.points,
        10,
      )
    : undefined;

  const selectedTwoYearPoint = data
    ? findClosestTenorPoint(
        data.trade_date,
        data.points,
        2,
      )
    : undefined;

  const selectedTenYearPoint = data
    ? findClosestTenorPoint(
        data.trade_date,
        data.points,
        10,
      )
    : undefined;

  const twoYearMove = tenorMoveBp(
    latestTwoYearPoint,
    selectedTwoYearPoint,
    isHistoricalDate,
  );

  const tenYearMove = tenorMoveBp(
    latestTenYearPoint,
    selectedTenYearPoint,
    isHistoricalDate,
  );

  const totalVolume =
    data?.points.reduce(
      (sum, point) =>
        sum + point.nominal_volume_cop_mn,
      0,
    ) ?? 0;

  const mostActivePoint = data?.points.reduce<
    TesCurvePoint | undefined
  >(
    (current, point) =>
      !current ||
      point.nominal_volume_cop_mn >
        current.nominal_volume_cop_mn
        ? point
        : current,
    undefined,
  );

  const comparisonAvailability = useMemo(() => {
    if (!data) {
      return {
        "1W": null,
        "1M": null,
        "3M": null,
      };
    }

    return {
      "1W": findComparisonDate(
        data.trade_date,
        data.available_dates,
        "1W",
      ),
      "1M": findComparisonDate(
        data.trade_date,
        data.available_dates,
        "1M",
      ),
      "3M": findComparisonDate(
        data.trade_date,
        data.available_dates,
        "3M",
      ),
    };
  }, [data]);

  const handlePreviousDate = () => {
    if (data?.previous_date) {
      setSelectedDate(
        data.previous_date,
      );
      setComparisonRange(null);
      setSelectedSecurityId(null);
    }
  };

  const handleNextDate = () => {
    if (data?.next_date) {
      setSelectedDate(
        data.next_date,
      );
      setComparisonRange(null);
      setSelectedSecurityId(null);
    }
  };

  const handleLatestDate = () => {
    if (!data) {
      return;
    }

    setSelectedDate(undefined);
    setComparisonRange(null);
    setSelectedSecurityId(null);
  };

  return (
    <>
        <header className="topbar">
          <div>
            <p className="eyebrow">
              COLOMBIA LOCAL MARKETS
            </p>
            <h1>Market Dashboard</h1>
          </div>

          <div className="market-status">
            <span className="status-dot" />
            <span>SEN CLOSE</span>
            <strong>
              {data
                ? formatDateDisplay(
                    data.trade_date,
                  )
                : "—"}
            </strong>
          </div>
        </header>

        <section className="content">
          {isLoading && (
            <div className="loading">
              Loading TES market data…
            </div>
          )}

          {isError && (
            <div className="error-card">
              Unable to retrieve TES market data.
            </div>
          )}

          {data && (
            <>
              <div className="metric-grid">
                <div className="metric-card">
                  <span className="metric-label">
                    2Y TES
                  </span>

                  <div className="metric-value-row">
                    <strong>
                      {latestTwoYearPoint?.close_yield !== null &&
                      latestTwoYearPoint?.close_yield !== undefined
                        ? `${latestTwoYearPoint.close_yield.toFixed(3)}%`
                        : "—"}
                    </strong>

                    <MetricMove
                      value={twoYearMove}
                    />
                  </div>

                  <span className="metric-note">
                    {latestTwoYearPoint
                      ? `${formatMaturity(
                          latestTwoYearPoint.maturity_date,
                        )}${
                          isHistoricalDate && data
                            ? ` · vs ${formatDateDisplay(data.trade_date)}`
                            : " · 1D"
                        }`
                      : "—"}
                  </span>
                </div>

                <div className="metric-card">
                  <span className="metric-label">
                    10Y TES
                  </span>

                  <div className="metric-value-row">
                    <strong>
                      {latestTenYearPoint?.close_yield !== null &&
                      latestTenYearPoint?.close_yield !== undefined
                        ? `${latestTenYearPoint.close_yield.toFixed(3)}%`
                        : "—"}
                    </strong>

                    <MetricMove
                      value={tenYearMove}
                    />
                  </div>

                  <span className="metric-note">
                    {latestTenYearPoint
                      ? `${formatMaturity(
                          latestTenYearPoint.maturity_date,
                        )}${
                          isHistoricalDate && data
                            ? ` · vs ${formatDateDisplay(data.trade_date)}`
                            : " · 1D"
                        }`
                      : "—"}
                  </span>
                </div>

                <div className="metric-card">
                  <span className="metric-label">
                    SEN Nominal Volume
                  </span>

                  <strong>
                    {formatCopMillions(
                      totalVolume,
                    )}
                  </strong>

                  <span className="metric-note">
                    CONH · TES fixed-rate
                  </span>
                </div>

                <div className="metric-card">
                  <span className="metric-label">
                    Most Active Bond
                  </span>

                  <strong className="market-name">
                    {mostActivePoint
                      ? `${formatMaturity(
                          mostActivePoint.maturity_date,
                        )} TES`
                      : "—"}
                  </strong>

                  <span className="metric-note">
                    {mostActivePoint
                      ? `${formatCopMillions(
                          mostActivePoint.nominal_volume_cop_mn,
                        )} · ${mostActivePoint.trade_count} trades`
                      : "—"}
                  </span>
                </div>
              </div>

              <section className="panel rates-panel">
                <div className="panel-header">
                  <div>
                    <div className="panel-title-row">
                      <LineChart size={18} />
                      <h2>TES Nominal Curve</h2>
                    </div>

                    <p>
                      COP fixed-rate government bonds · SEN cash market
                    </p>
                  </div>

                  <div className="curve-controls">
                    <div className="comparison-controls">
                      <button
                        type="button"
                        className={
                          comparisonRange === null
                            ? "range-button active"
                            : "range-button"
                        }
                        onClick={() =>
                          setComparisonRange(null)
                        }
                      >
                        None
                      </button>

                      {(["1W", "1M", "3M"] as const).map(
                        (range) => (
                          <button
                            type="button"
                            key={range}
                            className={
                              comparisonRange === range
                                ? "range-button active"
                                : "range-button"
                            }
                            disabled={
                              isHistoricalDate ||
                              !comparisonAvailability[range]
                            }
                            title={
                              isHistoricalDate
                                ? "Range comparisons are anchored to the latest SEN close. Return to Latest to use them."
                                : comparisonAvailability[range]
                                  ? `Compare with ${comparisonAvailability[range]}`
                                  : `Not enough history for ${range}`
                            }
                            onClick={() =>
                              setComparisonRange(range)
                            }
                          >
                            {range}
                          </button>
                        ),
                      )}
                    </div>

                    <div className="date-control">
                      <button
                        type="button"
                        className="date-arrow"
                        disabled={!data.previous_date}
                        onClick={handlePreviousDate}
                        aria-label="Previous trading day"
                      >
                        <ChevronLeft size={16} />
                      </button>

                      <label className="date-input-wrap">
                        <CalendarDays size={14} />
                        <input
                          type="date"
                          value={data.trade_date}
                          min={data.available_dates[0]}
                          max={data.latest_date}
                          onChange={(event: ChangeEvent<HTMLInputElement>) => {
                            setSelectedDate(
                              event.target.value || undefined,
                            );
                            setComparisonRange(null);
                            setSelectedSecurityId(null);
                          }}
                        />
                      </label>

                      <button
                        type="button"
                        className="date-arrow"
                        disabled={!data.next_date}
                        onClick={handleNextDate}
                        aria-label="Next trading day"
                      >
                        <ChevronRight size={16} />
                      </button>
                    </div>

                    <button
                      type="button"
                      className="latest-button"
                      disabled={
                        data.trade_date === data.latest_date
                      }
                      onClick={handleLatestDate}
                      title="Jump to latest available SEN close"
                    >
                      Latest
                    </button>
                  </div>
                </div>

                <div className="curve-chart">
                  <TesYieldCurve
                    points={data.points}
                    currentLabel={
                      formatDateDisplay(
                        data.trade_date,
                      )
                    }
                    comparisonPoints={
                      comparisonDate &&
                      comparisonDate !== data.trade_date &&
                      comparisonData?.trade_date === comparisonDate
                        ? comparisonData.points
                        : undefined
                    }
                    comparisonLabel={
                      comparisonDate &&
                      comparisonDate !== data.trade_date &&
                      comparisonData?.trade_date === comparisonDate
                        ? formatDateDisplay(
                            comparisonData.trade_date,
                          )
                        : undefined
                    }
                    selectedSecurityId={
                      selectedSecurityId
                    }
                    onSelectSecurity={
                      setSelectedSecurityId
                    }
                  />
                </div>

                <div className="table-section-header">
                  <div>
                    <h3>Cash Bond Monitor</h3>
                    <span>
                      Click a row to highlight the bond on the curve
                    </span>
                  </div>

                  <span className="table-count">
                    {data.points.length} securities
                  </span>
                </div>

                <BondTable
                  points={data.points}
                  selectedSecurityId={
                    selectedSecurityId
                  }
                  onSelectSecurity={
                    setSelectedSecurityId
                  }
                />
              </section>
            </>
          )}
        </section>
    </>
  );
}

function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">LM</div>
        <div>
          <div className="brand-title">Local Markets</div>
          <div className="brand-subtitle">Colombia</div>
        </div>
      </div>

      <nav className="nav" aria-label="Main navigation">
        <NavLink to="/" end className={({isActive}) => `nav-item${isActive ? " active" : ""}`}>
          <BarChart3 size={17}/> Dashboard
        </NavLink>
        <NavLink to="/rates" className={({isActive}) => `nav-item${isActive ? " active" : ""}`}>
          <Landmark size={17}/> TES Rates
        </NavLink>
        <NavLink to="/fx" className={({isActive}) => `nav-item${isActive ? " active" : ""}`}>
          <CircleDollarSign size={17}/> FX
        </NavLink>
        <NavLink to="/macro" className={({isActive}) => `nav-item${isActive ? " active" : ""}`}>
          <Activity size={17}/> Macro
        </NavLink>
      </nav>

      <div className="sidebar-footer">
        <Database size={14}/>
        <div>
          <div>Market data</div>
          <span>BanRep SEN · Yahoo Finance</span>
        </div>
      </div>
    </aside>
  );
}

function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <Sidebar/>
        <main className="workspace">
          <Routes>
            <Route path="/" element={<RatesPage/>}/>
            <Route path="/rates" element={<RatesPage/>}/>
            <Route path="/fx" element={<FxPage/>}/>
            <Route path="/macro" element={<MacroPage/>}/>
            <Route path="*" element={<Navigate to="/" replace/>}/>
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
