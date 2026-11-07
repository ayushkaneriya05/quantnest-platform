import { formatCurrency, formatDateTime, formatNumber } from './formatters';

export const settlementColumns = [
  ['Event', (row) => row.kind],
  ['Quantity', (row) => formatNumber(row.quantity, { maximumFractionDigits: 0 })],
  ['Gross payment', (row) => formatCurrency(row.gross)],
  ['Charges', (row) => formatCurrency(row.fees)],
  ['Cash change', (row) => formatCurrency(row.cash_change)],
  ['Effective (IST)', (row) => formatDateTime(row.effective_at)],
  ['Source', (row) => row.source],
];
