import { useQuery } from "@tanstack/react-query";

import { api } from "../../lib/api";
import type { FxHistoryResponse } from "../../types/fx";

/** The API caps responses at 5,000 sessions (~19 years). No new backend endpoint needed. */
export function useFxHistory() {
  return useQuery({
    queryKey: ["fx", "usdcop", "history"],
    queryFn: async () => {
      const response = await api.get<FxHistoryResponse>(
        "/fx/usdcop/history",
        { params: { start_date: "1900-01-01", limit: 5000 } },
      );
      return response.data;
    },
    staleTime: 60_000,
  });
}
