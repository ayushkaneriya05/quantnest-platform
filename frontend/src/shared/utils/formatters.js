const formatters = new Map();
const TIME_ZONE = 'Asia/Kolkata';

function getFormatter(kind, options) {
  const key = kind + JSON.stringify(options);
  if (!formatters.has(key)) formatters.set(key, kind === 'number'
    ? new Intl.NumberFormat('en-IN', options)
    : new Intl.DateTimeFormat('en-IN', { timeZone: TIME_ZONE, ...options }));
  return formatters.get(key);
}

export function formatNumber(value, options = {}) {
  const maximumFractionDigits = options.maximumFractionDigits ?? 2;
  return getFormatter('number', { maximumFractionDigits,
    minimumFractionDigits: Math.min(2, maximumFractionDigits), ...options }).format(Number(value || 0));
}

export function formatCurrency(value, options = {}) {
  const amount = Number(value);
  return getFormatter('number', { style: 'currency', currency: 'INR',
    minimumFractionDigits: Math.min(2, options.maximumFractionDigits ?? 2),
    maximumFractionDigits: 2, ...options }).format(Number.isFinite(amount) ? amount : 0);
}

export function formatDateTime(value, options = {}) {
  if (!value) return 'Not started';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return '—';
  return getFormatter('date', Object.keys(options).length ? options
    : { dateStyle: 'medium', timeStyle: 'medium' }).format(parsed);
}

export function formatDate(value, options = {}) {
  if (!value) return '—';
  return formatDateTime(value, Object.keys(options).length ? options : { dateStyle: 'medium' });
}

export function formatTime(value, options = {}) {
  if (!value) return '—';
  return formatDateTime(value, { hour: '2-digit', minute: '2-digit', hourCycle: 'h23', ...options });
}

// Exchange dates identify daily/weekly/monthly chart bars.
export function formatDateKey(value) {
  const parts = getFormatter('date', { year: 'numeric', month: '2-digit', day: '2-digit' })
    .formatToParts(new Date(value));
  const part = (type) => parts.find((item) => item.type === type).value;
  return part('year') + '-' + part('month') + '-' + part('day');
}

// A date-picker value represents a calendar date in the user's browser.
export function formatDateInput(date) {
  return date ? [date.getFullYear(), String(date.getMonth() + 1).padStart(2, '0'),
    String(date.getDate()).padStart(2, '0')].join('-') : '';
}

export function formatCurrencyMinorUnits(value, currency = 'INR') {
  return formatCurrency(Number(value) / 100, { currency });
}

export function formatBrokerAccount(brokerName, accountLabel) {
  const broker = brokerName || 'Broker';
  return accountLabel ? `${broker} · ${accountLabel}` : broker;
}
