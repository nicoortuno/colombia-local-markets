import ReactECharts from "echarts-for-react";

import type { MacroObservationPoint } from "../../types/macro";
import { formatMacroDate } from "./macroAnalytics";

interface MacroChartSeries {
  name: string;
  points: MacroObservationPoint[];
  color: string;
  axis?: 0 | 1;
  dashed?: boolean;
  step?: boolean;
  valueFormatter?: (value: number) => string;
}

interface MacroReferenceLine {
  value: number;
  label: string;
}

interface MacroChartProps {
  series: MacroChartSeries[];
  leftUnit: string;
  rightUnit?: string;
  referenceLine?: MacroReferenceLine;
}

export function MacroChart({
  series,
  leftUnit,
  rightUnit,
  referenceLine,
}: MacroChartProps) {
  const activeSeries = series.filter((item) => item.points.length > 0);

  if (activeSeries.length === 0) {
    return <div className="macro-chart-empty">No observations in this range.</div>;
  }

  const option = {
    animationDuration: 220,
    grid: {
      top: 45,
      right: rightUnit ? 66 : 24,
      bottom: 48,
      left: 62,
    },
    legend: {
      show: true,
      top: 4,
      right: 12,
      selectedMode: false,
      itemWidth: 18,
      itemHeight: 8,
      textStyle: { color: "#60758A", fontSize: 10 },
    },
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "line", lineStyle: { color: "#9DADBD" } },
      backgroundColor: "#002B51",
      borderColor: "#335574",
      borderWidth: 1,
      padding: 11,
      textStyle: { color: "#FFFFFF", fontSize: 11 },
      formatter: (items: Array<{ seriesName: string; value: [string, number] }>) => {
        if (!Array.isArray(items) || items.length === 0) {
          return "";
        }

        const dateValue = items[0]?.value?.[0];
        const lines = [`<strong>${dateValue ? formatMacroDate(dateValue) : ""}</strong>`];

        items.forEach((item) => {
          const config = activeSeries.find((candidate) => candidate.name === item.seriesName);
          const value = item.value?.[1];
          if (value === undefined || value === null) {
            return;
          }
          const formatted = config?.valueFormatter ? config.valueFormatter(value) : value.toFixed(2);
          lines.push(`${item.seriesName}: <strong>${formatted}</strong>`);
        });

        return lines.join("<br/>");
      },
    },
    xAxis: {
      type: "time",
      axisLabel: {
        color: "#60758A",
        fontSize: 9,
        hideOverlap: true,
        formatter: (value: number) => {
          const date = new Date(value);
          return date.toLocaleDateString("en-US", {
            month: "short",
            year: "2-digit",
            timeZone: "UTC",
          });
        },
      },
      axisLine: { lineStyle: { color: "#C9D3DC" } },
      axisTick: { show: false },
      splitLine: { show: false },
    },
    yAxis: [
      {
        type: "value",
        scale: true,
        name: leftUnit,
        nameTextStyle: { color: "#7B8B99", fontSize: 9, padding: [0, 0, 0, 4] },
        axisLabel: {
          color: "#60758A",
          fontSize: 9,
          formatter: (value: number) => value.toFixed(Math.abs(value) < 10 ? 1 : 0),
        },
        axisLine: { show: false },
        splitLine: { lineStyle: { color: "#E7EBEF", width: 1 } },
      },
      ...(rightUnit
        ? [{
            type: "value",
            scale: true,
            name: rightUnit,
            nameTextStyle: { color: "#7B8B99", fontSize: 9 },
            axisLabel: {
              color: "#60758A",
              fontSize: 9,
              formatter: (value: number) => value.toFixed(0),
            },
            axisLine: { show: false },
            splitLine: { show: false },
          }]
        : []),
    ],
    series: activeSeries.map((item, index) => ({
      name: item.name,
      type: "line",
      yAxisIndex: item.axis ?? 0,
      data: item.points.map((point) => [point.observation_date, point.value]),
      showSymbol: item.points.length <= 20,
      symbol: "circle",
      symbolSize: 4,
      smooth: false,
      step: item.step ? "end" : false,
      lineStyle: {
        color: item.color,
        width: index === 0 ? 2.1 : 1.8,
        type: item.dashed ? "dashed" : "solid",
      },
      itemStyle: { color: item.color },
      connectNulls: false,
      markLine:
        index === 0 && referenceLine
          ? {
              silent: true,
              symbol: "none",
              lineStyle: { color: "#9AA9B6", width: 1, type: "dashed" },
              label: {
                show: true,
                formatter: referenceLine.label,
                color: "#7B8B99",
                fontSize: 9,
                position: "insideEndTop",
              },
              data: [{ yAxis: referenceLine.value }],
            }
          : undefined,
    })),
  };

  return (
    <ReactECharts
      option={option}
      notMerge={true}
      style={{ height: "310px", width: "100%" }}
    />
  );
}
