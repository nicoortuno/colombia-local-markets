import { useQuery } from "@tanstack/react-query";

import { api } from "../../lib/api";
import type {
  MacroSeriesCatalogResponse,
  MacroSeriesHistoryResponse,
  MacroSeriesKey,
  MacroSnapshotResponse,
} from "../../types/macro";

const HISTORY_START = "2015-01-01";

export function useMacroSnapshot() {
  return useQuery({
    queryKey: ["macro", "snapshot"],
    queryFn: async () => {
      const response = await api.get<MacroSnapshotResponse>("/macro/snapshot");
      return response.data;
    },
    staleTime: 60_000,
  });
}

export function useMacroCatalog() {
  return useQuery({
    queryKey: ["macro", "series", "catalog"],
    queryFn: async () => {
      const response = await api.get<MacroSeriesCatalogResponse>("/macro/series");
      return response.data;
    },
    staleTime: 60_000,
  });
}

export function useMacroSeriesHistory(seriesKey: MacroSeriesKey) {
  return useQuery({
    queryKey: ["macro", "series", seriesKey, HISTORY_START],
    queryFn: async () => {
      const response = await api.get<MacroSeriesHistoryResponse>(
        `/macro/series/${seriesKey}`,
        {
          params: {
            start_date: HISTORY_START,
            limit: 5000,
          },
        },
      );
      return response.data;
    },
    staleTime: 60_000,
  });
}
