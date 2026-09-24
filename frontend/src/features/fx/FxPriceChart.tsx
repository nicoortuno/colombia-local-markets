import ReactECharts from "echarts-for-react";

import type { FxDailyPoint } from "../../types/fx";
import { displayCandle, formatCopPrice, formatFxDate, formatSigned } from "./fxAnalytics";

export type FxChartMode = "line" | "candles";

interface FxPriceChartProps {
  points: FxDailyPoint[];
  mode: FxChartMode;
}

export function FxPriceChart({ points, mode }: FxPriceChartProps) {
  if (points.length === 0) {
    return <div className="fx-chart-empty">No USD/COP observations in this range.</div>;
  }

  const lows = points.map((p) => Math.min(p.low_price, p.open_price, p.close_price));
  const highs = points.map((p) => Math.max(p.high_price, p.open_price, p.close_price));
  const minPrice = Math.floor((Math.min(...lows) - 8) / 25) * 25;
  const maxPrice = Math.ceil((Math.max(...highs) + 8) / 25) * 25;
  const seriesName = mode === "line" ? "USD/COP Close" : "USD/COP OHLC";
  const badCandles = points.filter((point) => displayCandle(point) === null).length;

  const option = {
    animationDuration: 260,
    grid: { top: 37, right: 24, bottom: 53, left: 75 },
    legend: {
      show: true,
      right: 16,
      top: 1,
      selectedMode: false,
      itemWidth: 17,
      itemHeight: 8,
      textStyle: { color: "#60758A", fontSize: 11 },
    },
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "cross", crossStyle: { color: "#9DADBD" } },
      backgroundColor: "#002B51",
      borderColor: "#335574",
      borderWidth: 1,
      padding: 12,
      textStyle: { color: "#FFFFFF", fontSize: 11 },
      formatter: (items: { dataIndex?: number } | { dataIndex?: number }[]) => {
        const index = (Array.isArray(items) ? items[0] : items)?.dataIndex;
        const point = index === undefined ? undefined : points[index];
        if (!point) return "";
        return [
          `<strong>${formatFxDate(point.trade_date, true)}</strong>`,
          `Open: <strong>${formatCopPrice(point.open_price)}</strong>`,
          `High: <strong>${formatCopPrice(point.high_price)}</strong>`,
          `Low: <strong>${formatCopPrice(point.low_price)}</strong>`,
          `Close: <strong>${formatCopPrice(point.close_price)}</strong>`,
          `1D: <strong>${point.change_1d_cop === null ? "—" : `${formatSigned(point.change_1d_cop)} COP`} (${point.change_1d_pct === null ? "—" : `${formatSigned(point.change_1d_pct, 3)}%`})</strong>`,
        ].join("<br/>");
      },
    },
    xAxis: {
      type: "category",
      data: points.map((point) => point.trade_date),
      boundaryGap: mode === "candles",
      axisLabel: {
        color: "#60758A",
        fontSize: 10,
        hideOverlap: true,
        formatter: (value: string) => formatFxDate(value),
      },
      axisLine: { lineStyle: { color: "#C9D3DC" } },
      axisTick: { show: false },
      splitLine: { show: false },
      name: "Trading session",
      nameLocation: "middle",
      nameGap: 34,
      nameTextStyle: { color: "#7B8B99", fontSize: 10 },
    },
    yAxis: {
      type: "value",
      scale: true,
      min: minPrice,
      max: maxPrice <= minPrice ? minPrice + 25 : maxPrice,
      axisLabel: {
        color: "#60758A",
        fontSize: 10,
        formatter: (value: number) => value.toLocaleString("en-US", { maximumFractionDigits: 0 }),
      },
      axisLine: { show: false },
      splitLine: { lineStyle: { color: "#E7EBEF", width: 1 } },
    },
    series: mode === "line"
      ? [{
          name: seriesName,
          type: "line",
          data: points.map((point) => point.close_price),
          showSymbol: points.length <= 15,
          symbol: "circle",
          symbolSize: 5,
          lineStyle: { color: "#187ABA", width: 2 },
          itemStyle: { color: "#187ABA" },
          smooth: false,
        }]
      : [{
          name: seriesName,
          type: "candlestick",
          data: points.map((point) => displayCandle(point) ?? "-"),
          barMaxWidth: 15,
          itemStyle: {
            // A higher USD/COP close signals COP depreciation: shown in red.
            color: "#B14D4D",
            color0: "#337C63",
            borderColor: "#B14D4D",
            borderColor0: "#337C63",
          },
        }],
  };

  return (
    <>
      <ReactECharts
        option={option}
        notMerge={true}
        style={{ height: "360px", width: "100%" }}
      />
      {mode === "candles" && (
        <p className="fx-chart-footnote">
          Small (≤ COP 0.05) vendor OHLC discrepancies are corrected for candle display only.
          {badCandles > 0 ? ` ${badCandles} session(s) with larger inconsistencies are omitted from candles.` : ""}
        </p>
      )}
    </>
  );
}
