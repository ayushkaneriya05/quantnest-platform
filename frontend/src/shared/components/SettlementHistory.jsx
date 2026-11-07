import Pagination from "@/shared/components/Pagination";
import WorkspaceState from "@/shared/components/WorkspaceState";
import { usePagination } from "@/shared/hooks/usePagination";
import { useEffect, useState } from 'react';
import PropTypes from 'prop-types';

import api from '@/shared/services/api';
import { getApiErrorMessage } from '@/shared/utils/apiErrors';
import { settlementColumns } from '@/shared/utils/settlements';
import { GlobalLoader } from '@/shared/components/ui/global-loader';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/shared/components/ui/table';

export default function SettlementHistory({ accountId, refreshKey }) {
  const [data, setData] = useState({ results: [], count: 0 });
  const { page, pageSize, setPage, setPageSize, accept } = usePagination(String(accountId), 'settlements');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError('');
    api.get('/paper/settlements/', { signal: controller.signal, params: { account_id: accountId, page, page_size: pageSize } })
      .then(({ data: result }) => { if (!controller.signal.aborted) { setData(result); accept(result); } })
      .catch((error) => { if (!controller.signal.aborted) setError(getApiErrorMessage(error, 'Could not load settlements.')); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [accountId, page, pageSize, accept, refreshKey, revision]);
  return <section className="overflow-hidden rounded-xl border bg-card">
    <div className="flex items-center justify-between gap-3 border-b px-3 py-2">
      <div><h2 className="text-sm font-semibold">Settlements</h2><p className="text-xs text-muted-foreground">Sourced cash payments. Closed-trade P&amp;L includes these amounts; do not add them again.</p></div>
    </div>
    {error ? <WorkspaceState error={error} onRetry={() => setRevision(value => value + 1)} /> : <Table className="whitespace-nowrap text-xs [&_td]:py-2 [&_th]:h-9">
      <TableHeader><TableRow><TableHead>Instrument</TableHead>{settlementColumns.map(([label]) => <TableHead key={label}>{label}</TableHead>)}</TableRow></TableHeader>
      <TableBody>{data.results.map((row) => <TableRow key={row.id}><TableCell className="font-medium">{row.instrument.name}</TableCell>{settlementColumns.map(([label, render]) => <TableCell className="max-w-56 truncate tabular-nums" title={label === 'Source' ? row.source : undefined} key={label}>{render(row)}</TableCell>)}</TableRow>)}
        {!data.results.length && <TableRow><TableCell colSpan={settlementColumns.length + 1} className="h-20 text-center text-muted-foreground">{loading ? <GlobalLoader inline text="Loading settlements…" /> : 'No settlement payments recorded.'}</TableCell></TableRow>}
      </TableBody>
    </Table>}
    <Pagination {...data} page={page} pageSize={pageSize} loading={loading} onPageChange={setPage} onPageSizeChange={setPageSize} label="Paper settlement pages" />
  </section>;
}

SettlementHistory.propTypes = {
  accountId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
  refreshKey: PropTypes.object,
};
