import { useQuery } from "@tanstack/react-query";

import { api } from "../../lib/api";
import type {
  TesCurveResponse,
} from "../../types/rates";


export function useTesCurve(
  tradeDate?: string,
  enabled = true,
) {
  return useQuery({
    queryKey: [
      "tes-curve",
      enabled
        ? tradeDate ?? "latest"
        : "disabled",
    ],
    enabled,

    queryFn: async () => {
      const response =
        await api.get<TesCurveResponse>(
          "/rates/curve",
          {
            params: tradeDate
              ? { trade_date: tradeDate }
              : undefined,
          },
        );

      return response.data;
    },
  });
}
