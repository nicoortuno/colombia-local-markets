import ReactECharts from "echarts-for-react";

import type {
  TesCurvePoint,
} from "../../types/rates";


interface TesYieldCurveProps {
  points: TesCurvePoint[];
  currentLabel?: string;
  comparisonPoints?: TesCurvePoint[];
  comparisonLabel?: string;
  selectedSecurityId?: string | null;
  onSelectSecurity?: (securityId: string) => void;
}


function formatMaturity(
  maturityDate: string,
): string {
  const date = new Date(
    `${maturityDate}T00:00:00Z`,
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


function maturityYearValue(
  maturityDate: string,
): number {
  const date = new Date(
    `${maturityDate}T00:00:00Z`,
  );
  const year = date.getUTCFullYear();
  const startOfYear = Date.UTC(
    year,
    0,
    1,
  );
  const startOfNextYear = Date.UTC(
    year + 1,
    0,
    1,
  );

  return (
    year +
    (date.getTime() - startOfYear) /
      (startOfNextYear - startOfYear)
  );
}


function formatVolume(
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


export function TesYieldCurve({
  points,
  currentLabel,
  comparisonPoints,
  comparisonLabel,
  selectedSecurityId,
  onSelectSecurity,
}: TesYieldCurveProps) {
  const currentData = points
    .filter(
      (point) =>
        point.close_yield !== null,
    )
    .map((point) => ({
      value: [
        maturityYearValue(
          point.maturity_date,
        ),
        point.close_yield,
      ],
      security: point.security_id,
      maturity: point.maturity_date,
      yield: point.close_yield,
      volume: point.nominal_volume_cop_mn,
      trades: point.trade_count,
      change1d: point.change_1d_bp,
      change5d: point.change_5d_bp,
      symbolSize:
        point.security_id === selectedSecurityId
          ? 10
          : 6,
      itemStyle: {
        color:
          point.security_id === selectedSecurityId
            ? "#187ABA"
            : "#002B51",
        borderColor: "#FFFFFF",
        borderWidth:
          point.security_id === selectedSecurityId
            ? 2.5
            : 1.5,
      },
    }));

  const comparisonData = (comparisonPoints ?? [])
    .filter(
      (point) =>
        point.close_yield !== null,
    )
    .map((point) => ({
      value: [
        maturityYearValue(
          point.maturity_date,
        ),
        point.close_yield,
      ],
      security: point.security_id,
      maturity: point.maturity_date,
      yield: point.close_yield,
    }));

  const allYields = [
    ...currentData.map((point) => point.yield),
    ...comparisonData.map((point) => point.yield),
  ].filter(
    (value): value is number => value !== null,
  );

  const allMaturityYears = [
    ...currentData.map(
      (point) => point.value[0] as number,
    ),
    ...comparisonData.map(
      (point) => point.value[0] as number,
    ),
  ];

  if (allYields.length === 0) {
    return null;
  }

  const minimumYield =
    Math.floor(
      (Math.min(...allYields) - 0.08) * 10,
    ) / 10;

  const maximumYield =
    Math.ceil(
      (Math.max(...allYields) + 0.08) * 10,
    ) / 10;

  const minimumMaturityYear =
    Math.floor(
      Math.min(...allMaturityYears) / 5,
    ) * 5;

  const maximumMaturityYear =
    Math.ceil(
      Math.max(...allMaturityYears) / 5,
    ) * 5;

  const option = {
    animationDuration: 300,

    grid: {
      top: 34,
      right: 24,
      bottom: 58,
      left: 58,
    },

    legend: {
      show: true,
      top: 0,
      right: 16,
      itemWidth: 18,
      itemHeight: 8,
      textStyle: {
        color: "#60758A",
        fontSize: 11,
      },
    },

    tooltip: {
      trigger: "item",
      backgroundColor: "#002B51",
      borderColor: "#335574",
      borderWidth: 1,
      padding: 12,
      textStyle: {
        color: "#FFFFFF",
        fontSize: 12,
      },
      formatter: (params: {
        seriesName: string;
        data: {
          security: string;
          maturity: string;
          yield: number | null;
          volume?: number;
          trades?: number;
          change1d?: number | null;
          change5d?: number | null;
        };
      }) => {
        const point = params.data;
        const change1d = point.change1d;
        const change5d = point.change5d;

        const moveText = (
          value: number | null | undefined,
        ) => {
          if (value === null || value === undefined) {
            return "—";
          }

          return `${value > 0 ? "+" : ""}${value.toFixed(1)}bp`;
        };

        const liquidity =
          point.volume !== undefined
            ? `<br/>Volume: <strong>${formatVolume(point.volume)}</strong><br/>Trades: ${point.trades ?? "—"}`
            : "";

        const changes =
          params.seriesName === (currentLabel ?? "Current")
            ? `<br/>1D: ${moveText(change1d)} &nbsp; 5D: ${moveText(change5d)}`
            : "";

        return `
          <strong>${point.security}</strong><br/>
          ${formatMaturity(point.maturity)}<br/><br/>
          Yield: <strong>${point.yield?.toFixed(3)}%</strong>
          ${changes}
          ${liquidity}
        `;
      },
    },

    xAxis: {
      type: "value",
      min: minimumMaturityYear,
      max: maximumMaturityYear,
      interval: 5,
      axisLine: {
        lineStyle: {
          color: "#C9D3DC",
        },
      },
      axisTick: {
        show: false,
      },
      axisLabel: {
        color: "#60758A",
        fontSize: 10,
        formatter: (value: number) =>
          String(Math.round(value)),
      },
      name: "Maturity",
      nameLocation: "middle",
      nameGap: 34,
      nameTextStyle: {
        color: "#7B8B99",
        fontSize: 10,
        fontWeight: 500,
      },
      splitLine: {
        show: false,
      },
    },

    yAxis: {
      type: "value",
      min: minimumYield,
      max: maximumYield,
      axisLabel: {
        color: "#60758A",
        fontSize: 10,
        formatter: (
          value: number,
        ) => `${value.toFixed(1)}%`,
      },
      splitLine: {
        lineStyle: {
          color: "#E7EBEF",
          width: 1,
        },
      },
    },

    series: [
      ...(comparisonData.length > 0
        ? [
            {
              name: comparisonLabel ?? "Comparison",
              type: "line",
              data: comparisonData,
              showSymbol: true,
              symbol: "circle",
              symbolSize: 4,
              smooth: false,
              silent: false,
              lineStyle: {
                width: 1.5,
                type: "dashed",
                color: "#91A4B4",
              },
              itemStyle: {
                color: "#91A4B4",
              },
              z: 1,
            },
          ]
        : []),
      {
        name: currentLabel ?? "Current",
        type: "line",
        data: currentData,
        showSymbol: true,
        symbol: "circle",
        smooth: false,
        lineStyle: {
          width: 2,
          color: "#187ABA",
        },
        z: 2,
      },
    ],
  };

  const onEvents = {
    click: (params: {
      seriesName?: string;
      data?: {
        security?: string;
      };
    }) => {
      if (
        params.seriesName === (currentLabel ?? "Current") &&
        params.data?.security &&
        onSelectSecurity
      ) {
        onSelectSecurity(params.data.security);
      }
    },
  };

  return (
    <ReactECharts
      option={option}
      notMerge={true}
      onEvents={onEvents}
      style={{
        height: "320px",
        width: "100%",
      }}
    />
  );
}
