import { useMemo, useState } from "react";
import {
  Activity,
  BarChart3,
  Landmark,
  LineChart,
  ShieldCheck,
  TrendingUp,
} from "lucide-react";

import type {
  MacroDerivedMetric,
  MacroObservationPoint,
  MacroSeriesSummary,
  MacroSnapshotMetric,
} from "../../types/macro";
import { MacroChart } from "./MacroChart";
import {
  type MacroRange,
  deriveGdpYoy,
  filterMacroPoints,
  formatMacroDate,
  formatQuarter,
  reservesToUsdBn,
  shiftMacroDate,
  signed,
} from "./macroAnalytics";
import {
  useMacroCatalog,
  useMacroSeriesHistory,
  useMacroSnapshot,
} from "./useMacroData";

function formatPercent(value: number, decimals = 2, signedValue = false): string {
  return `${signedValue ? signed(value, decimals) : value.toFixed(decimals)}%`;
}

function formatMetricDate(metric: MacroSnapshotMetric | MacroDerivedMetric, frequency: string): string {
  if (frequency === "quarterly") {
    return formatQuarter(metric.observation_date);
  }
  if (frequency === "monthly") {
    return formatMacroDate(metric.observation_date, true);
  }
  return formatMacroDate(metric.observation_date);
}

function findSummary(series: MacroSeriesSummary[], key: string): MacroSeriesSummary | undefined {
  return series.find((item) => item.series_key === key);
}

function formatChange(
  summary: MacroSeriesSummary | undefined,
  mode: "bp" | "pp" | "usd_bn",
): string {
  if (!summary || summary.change_abs === null) {
    return "—";
  }

  if (mode === "bp") {
    return `${signed(summary.change_abs * 100, 1)}bp`;
  }

  if (mode === "usd_bn") {
    return `${signed(summary.change_abs / 1000, 2)}bn`;
  }

  return `${signed(summary.change_abs, 2)}pp`;
}

function latestDerivedChange(points: MacroObservationPoint[]): string {
  if (points.length < 2) {
    return "—";
  }
  const latest = points[points.length - 1];
  const previous = points[points.length - 2];
  return `${signed(latest.value - previous.value, 2)}pp`;
}

interface MonitorRow {
  label: string;
  detail: string;
  value: string;
  date: string;
  change: string;
  source: string;
}

export function MacroPage() {
  const [range, setRange] = useState<MacroRange>("3Y");

  const snapshotQuery = useMacroSnapshot();
  const catalogQuery = useMacroCatalog();
  const policyQuery = useMacroSeriesHistory("policy_rate");
  const ibrQuery = useMacroSeriesHistory("ibr_overnight");
  const headlineQuery = useMacroSeriesHistory("headline_inflation");
  const coreQuery = useMacroSeriesHistory("core_inflation");
  const gdpQuery = useMacroSeriesHistory("real_gdp");
  const unemploymentQuery = useMacroSeriesHistory("unemployment");
  const currentAccountQuery = useMacroSeriesHistory("current_account_gdp");
  const reservesQuery = useMacroSeriesHistory("net_reserves");

  const historyQueries = [
    policyQuery,
    ibrQuery,
    headlineQuery,
    coreQuery,
    gdpQuery,
    unemploymentQuery,
    currentAccountQuery,
    reservesQuery,
  ];

  const isLoading = snapshotQuery.isLoading || catalogQuery.isLoading || historyQueries.some((query) => query.isLoading);
  const isError = snapshotQuery.isError || catalogQuery.isError || historyQueries.some((query) => query.isError);

  const snapshot = snapshotQuery.data;
  const catalog = catalogQuery.data?.series ?? [];

  const gdpYoyFull = useMemo(
    () => deriveGdpYoy(gdpQuery.data?.points ?? []),
    [gdpQuery.data],
  );

  const reservesBnFull = useMemo(
    () => reservesToUsdBn(reservesQuery.data?.points ?? []),
    [reservesQuery.data],
  );

  const latestDate = snapshot?.as_of_date ?? "";
  const rangeStart = useMemo(() => {
    if (!latestDate || range === "ALL") {
      return "2015-01-01";
    }
    return shiftMacroDate(latestDate, range);
  }, [latestDate, range]);

  const inRange = (points: MacroObservationPoint[]) =>
    latestDate ? filterMacroPoints(points, rangeStart, latestDate) : [];

  const policySummary = findSummary(catalog, "policy_rate");
  const ibrSummary = findSummary(catalog, "ibr_overnight");
  const headlineSummary = findSummary(catalog, "headline_inflation");
  const coreSummary = findSummary(catalog, "core_inflation");
  const unemploymentSummary = findSummary(catalog, "unemployment");
  const currentAccountSummary = findSummary(catalog, "current_account_gdp");
  const reservesSummary = findSummary(catalog, "net_reserves");

  const monitorRows: MonitorRow[] = snapshot
    ? [
        {
          label: "Policy rate",
          detail: "BanRep policy rate",
          value: formatPercent(snapshot.policy_rate.value, 2),
          date: formatMetricDate(snapshot.policy_rate, "daily"),
          change: formatChange(policySummary, "bp"),
          source: snapshot.policy_rate.source,
        },
        {
          label: "IBR overnight",
          detail: "Effective annual, base 365",
          value: formatPercent(snapshot.ibr_overnight.value, 3),
          date: formatMetricDate(snapshot.ibr_overnight, "daily"),
          change: formatChange(ibrSummary, "bp"),
          source: snapshot.ibr_overnight.source,
        },
        {
          label: "Headline CPI",
          detail: "Annual inflation",
          value: formatPercent(snapshot.headline_inflation.value, 2),
          date: formatMetricDate(snapshot.headline_inflation, "monthly"),
          change: formatChange(headlineSummary, "pp"),
          source: snapshot.headline_inflation.source,
        },
        {
          label: "Core CPI",
          detail: "Ex-food & regulated",
          value: formatPercent(snapshot.core_inflation.value, 2),
          date: formatMetricDate(snapshot.core_inflation, "monthly"),
          change: formatChange(coreSummary, "pp"),
          source: snapshot.core_inflation.source,
        },
        {
          label: "Real GDP",
          detail: "Year-over-year growth",
          value: formatPercent(snapshot.real_gdp_yoy.value, 2, true),
          date: formatMetricDate(snapshot.real_gdp_yoy, "quarterly"),
          change: latestDerivedChange(gdpYoyFull),
          source: "Calculated from DANE real GDP",
        },
        {
          label: "Unemployment",
          detail: "Total national",
          value: formatPercent(snapshot.unemployment.value, 2),
          date: formatMetricDate(snapshot.unemployment, "monthly"),
          change: formatChange(unemploymentSummary, "pp"),
          source: snapshot.unemployment.source,
        },
        {
          label: "Current account",
          detail: "Share of GDP",
          value: formatPercent(snapshot.current_account_gdp.value, 2, true),
          date: formatMetricDate(snapshot.current_account_gdp, "quarterly"),
          change: formatChange(currentAccountSummary, "pp"),
          source: snapshot.current_account_gdp.source,
        },
        {
          label: "Net reserves",
          detail: "International reserves",
          value: `$${snapshot.net_reserves_usd_bn.value.toFixed(2)}bn`,
          date: formatMetricDate(snapshot.net_reserves, "monthly"),
          change: formatChange(reservesSummary, "usd_bn"),
          source: snapshot.net_reserves.source,
        },
      ]
    : [];

  return (
    <>
      <header className="topbar">
        <div>
          <p className="eyebrow">COLOMBIA LOCAL MARKETS</p>
          <h1>Macro · Colombia</h1>
        </div>
        <div className="market-status">
          <span className="status-dot" />
          <span>BANREP / DANE</span>
          <strong>{snapshot ? formatMacroDate(snapshot.as_of_date).toUpperCase() : "—"}</strong>
        </div>
      </header>

      <section className="content macro-content">
        {isLoading && <div className="loading">Loading Colombia macro data…</div>}
        {isError && (
          <div className="error-card">
            Unable to retrieve macro data. Check that FastAPI is running and the BanRep macro backfill is loaded.
          </div>
        )}

        {snapshot && !isLoading && !isError && (
          <>
            <div className="macro-page-intro">
              <div>
                <span className="macro-kicker">MONETARY POLICY · INFLATION · ACTIVITY · EXTERNAL</span>
                <span className="macro-source-note">
                  Official observations stored from <strong>Banco de la República / DANE</strong>
                </span>
              </div>
              <div className="comparison-controls macro-range-controls" aria-label="Macro chart range">
                {(["1Y", "3Y", "5Y", "ALL"] as const).map((period) => (
                  <button
                    type="button"
                    key={period}
                    className={`range-button${range === period ? " active" : ""}`}
                    onClick={() => setRange(period)}
                    aria-pressed={range === period}
                  >
                    {period === "ALL" ? "All" : period}
                  </button>
                ))}
              </div>
            </div>

            <div className="metric-grid macro-metric-grid">
              <div className="metric-card">
                <span className="metric-label">BanRep Policy Rate</span>
                <div className="metric-value-row">
                  <strong>{formatPercent(snapshot.policy_rate.value, 2)}</strong>
                  <span className="macro-card-change">{formatChange(policySummary, "bp")}</span>
                </div>
                <span className="metric-note">
                  {formatMetricDate(snapshot.policy_rate, "daily")} · effective annual
                </span>
              </div>

              <div className="metric-card">
                <span className="metric-label">IBR Overnight</span>
                <div className="metric-value-row">
                  <strong>{formatPercent(snapshot.ibr_overnight.value, 3)}</strong>
                  <span className="macro-card-change">
                    {signed(snapshot.ibr_policy_spread_bp.value, 1)}bp vs policy
                  </span>
                </div>
                <span className="metric-note">
                  {formatMetricDate(snapshot.ibr_overnight, "daily")} · effective annual
                </span>
              </div>

              <div className="metric-card">
                <span className="metric-label">Headline / Core CPI</span>
                <div className="metric-value-row macro-dual-value">
                  <strong>{formatPercent(snapshot.headline_inflation.value, 2)}</strong>
                  <span>Core {formatPercent(snapshot.core_inflation.value, 2)}</span>
                </div>
                <span className="metric-note">
                  {formatMetricDate(snapshot.headline_inflation, "monthly")} · YoY inflation
                </span>
              </div>

              <div className="metric-card">
                <span className="metric-label">Real GDP Growth</span>
                <div className="metric-value-row">
                  <strong>{formatPercent(snapshot.real_gdp_yoy.value, 2, true)}</strong>
                  <span className="macro-card-change">YoY</span>
                </div>
                <span className="metric-note">
                  {formatMetricDate(snapshot.real_gdp_yoy, "quarterly")} · real GDP, 2015 prices
                </span>
              </div>
            </div>

            <div className="macro-secondary-strip">
              <div className="macro-secondary-stat">
                <Activity size={15} />
                <div>
                  <span>Unemployment</span>
                  <strong>{formatPercent(snapshot.unemployment.value, 2)}</strong>
                  <small>{formatMetricDate(snapshot.unemployment, "monthly")}</small>
                </div>
              </div>
              <div className="macro-secondary-stat">
                <LineChart size={15} />
                <div>
                  <span>Current Account</span>
                  <strong>{formatPercent(snapshot.current_account_gdp.value, 2, true)}</strong>
                  <small>% GDP · {formatMetricDate(snapshot.current_account_gdp, "quarterly")}</small>
                </div>
              </div>
              <div className="macro-secondary-stat">
                <Landmark size={15} />
                <div>
                  <span>Net International Reserves</span>
                  <strong>${snapshot.net_reserves_usd_bn.value.toFixed(2)}bn</strong>
                  <small>{formatMetricDate(snapshot.net_reserves, "monthly")}</small>
                </div>
              </div>
            </div>

            <div className="macro-panel-grid">
              <section className="panel macro-panel">
                <div className="panel-header macro-panel-header">
                  <div>
                    <div className="panel-title-row">
                      <Landmark size={18} />
                      <h2>Monetary Policy</h2>
                    </div>
                    <p>BanRep policy rate versus IBR overnight effective</p>
                  </div>
                  <span className="macro-panel-badge">{range === "ALL" ? "2015–latest" : range}</span>
                </div>
                <div className="macro-chart-wrap">
                  <MacroChart
                    leftUnit="%"
                    series={[
                      {
                        name: "Policy rate",
                        points: inRange(policyQuery.data?.points ?? []),
                        color: "#002B51",
                        step: true,
                        valueFormatter: (value) => `${value.toFixed(2)}%`,
                      },
                      {
                        name: "IBR O/N",
                        points: inRange(ibrQuery.data?.points ?? []),
                        color: "#187ABA",
                        valueFormatter: (value) => `${value.toFixed(3)}%`,
                      },
                    ]}
                  />
                </div>
              </section>

              <section className="panel macro-panel">
                <div className="panel-header macro-panel-header">
                  <div>
                    <div className="panel-title-row">
                      <TrendingUp size={18} />
                      <h2>Inflation</h2>
                    </div>
                    <p>Headline and ex-food / regulated consumer inflation</p>
                  </div>
                  <span className="macro-panel-badge">Monthly</span>
                </div>
                <div className="macro-chart-wrap">
                  <MacroChart
                    leftUnit="% YoY"
                    referenceLine={{ value: 3, label: "3% target" }}
                    series={[
                      {
                        name: "Headline CPI",
                        points: inRange(headlineQuery.data?.points ?? []),
                        color: "#187ABA",
                        valueFormatter: (value) => `${value.toFixed(2)}%`,
                      },
                      {
                        name: "Core CPI",
                        points: inRange(coreQuery.data?.points ?? []),
                        color: "#4695C8",
                        dashed: true,
                        valueFormatter: (value) => `${value.toFixed(2)}%`,
                      },
                    ]}
                  />
                </div>
              </section>

              <section className="panel macro-panel">
                <div className="panel-header macro-panel-header">
                  <div>
                    <div className="panel-title-row">
                      <BarChart3 size={18} />
                      <h2>Activity & Labor</h2>
                    </div>
                    <p>Real GDP growth and national unemployment</p>
                  </div>
                  <span className="macro-panel-badge">Quarterly / monthly</span>
                </div>
                <div className="macro-chart-wrap">
                  <MacroChart
                    leftUnit="%"
                    series={[
                      {
                        name: "Real GDP YoY",
                        points: inRange(gdpYoyFull),
                        color: "#002B51",
                        valueFormatter: (value) => `${signed(value, 2)}%`,
                      },
                      {
                        name: "Unemployment",
                        points: inRange(unemploymentQuery.data?.points ?? []),
                        color: "#187ABA",
                        dashed: true,
                        valueFormatter: (value) => `${value.toFixed(2)}%`,
                      },
                    ]}
                  />
                </div>
              </section>

              <section className="panel macro-panel">
                <div className="panel-header macro-panel-header">
                  <div>
                    <div className="panel-title-row">
                      <LineChart size={18} />
                      <h2>External Balance</h2>
                    </div>
                    <p>Current account balance and net international reserves</p>
                  </div>
                  <span className="macro-panel-badge">% GDP / USD bn</span>
                </div>
                <div className="macro-chart-wrap">
                  <MacroChart
                    leftUnit="% GDP"
                    rightUnit="USD bn"
                    series={[
                      {
                        name: "Current account",
                        points: inRange(currentAccountQuery.data?.points ?? []),
                        color: "#187ABA",
                        valueFormatter: (value) => `${signed(value, 2)}%`,
                      },
                      {
                        name: "Net reserves",
                        points: inRange(reservesBnFull),
                        color: "#002B51",
                        axis: 1,
                        valueFormatter: (value) => `$${value.toFixed(1)}bn`,
                      },
                    ]}
                  />
                </div>
              </section>
            </div>

            <section className="panel macro-monitor-panel">
              <div className="table-section-header">
                <div>
                  <h3>Macro Monitor</h3>
                  <span>Latest official observations · Δ uses economically relevant units</span>
                </div>
                <span className="table-count">{monitorRows.length} indicators</span>
              </div>
              <div className="macro-table-wrap">
                <table className="macro-table">
                  <thead>
                    <tr>
                      <th>Indicator</th>
                      <th>Latest</th>
                      <th>Observation</th>
                      <th>Δ vs prior</th>
                      <th>Source</th>
                    </tr>
                  </thead>
                  <tbody>
                    {monitorRows.map((row) => (
                      <tr key={row.label}>
                        <td>
                          <strong>{row.label}</strong>
                          <span>{row.detail}</span>
                        </td>
                        <td className="macro-table-value">{row.value}</td>
                        <td>{row.date}</td>
                        <td className="macro-table-change">{row.change}</td>
                        <td>{row.source}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <div className="macro-disclaimer">
              <ShieldCheck size={14} />
              <span>
                Official raw observations are stored from BanRep SUAMECA / DANE. GDP YoY, IBR-policy spread and reserve USD-bn display values are calculated from the stored raw series; the Dashboard page is unchanged.
              </span>
            </div>
          </>
        )}
      </section>
    </>
  );
}
