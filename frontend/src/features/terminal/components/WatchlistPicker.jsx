import PropTypes from 'prop-types';
import { useState } from 'react';
import { Button } from '@/shared/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/shared/components/ui/select';
import { Plus, Pencil, Trash2 } from 'lucide-react';
import { Input } from '@/shared/components/ui/input';
import { Dialog, DialogContent, DialogTitle } from '@/shared/components/ui/dialog';
import { useNotifications } from '@/shared/hooks/useNotifications';
import { getApiErrorMessage } from '@/shared/utils/apiErrors';
import api from '@/shared/services/api';

export default function WatchlistPicker({ lists, activeId, onChange, onRefresh }) {
  const [action, setAction] = useState(''), [name, setName] = useState(''), [busy, setBusy] = useState(false);
  const { notify } = useNotifications();
  const open = (value) => { setAction(value); setName(value === 'create' ? '' : lists.find((row) => row.id === activeId)?.name || ''); };
  const save = async (event) => {
    event.preventDefault(); setBusy(true);
    try {
      if (action === 'create') { const response = await api.post('/trading/watchlists/', { name }); onChange(response.data.id); }
      else if (action === 'rename') { await api.patch('/trading/watchlists/' + activeId + '/', { name }); await onRefresh(); }
      else { await api.delete('/trading/watchlists/' + activeId + '/'); onChange(lists.find((row) => row.id !== activeId).id); }
      setAction(''); notify.success('Watchlists updated');
    } catch (error) { notify.error(getApiErrorMessage(error, 'Could not update watchlist.')); }
    finally { setBusy(false); }
  };
  return <><div className="flex items-center gap-1">
    <Select value={String(activeId)} onValueChange={(value) => onChange(Number(value))}><SelectTrigger aria-label="Active watchlist" className="h-9 min-w-0 flex-1"><SelectValue placeholder="Watchlist" /></SelectTrigger>
      <SelectContent>{lists.map((row) => <SelectItem value={String(row.id)} key={row.id}>{row.name}</SelectItem>)}</SelectContent></Select>
    <Button size="icon" variant="ghost" className="h-8 w-8 shrink-0" aria-label="Create watchlist" onClick={() => open('create')}><Plus className="h-3.5 w-3.5" /></Button><Button size="icon" variant="ghost" className="h-8 w-8 shrink-0" disabled={!activeId} onClick={() => open('rename')} aria-label="Rename watchlist"><Pencil className="h-3.5 w-3.5" /></Button>
    <Button size="icon" variant="ghost" className="h-8 w-8 shrink-0" aria-label="Remove watchlist" disabled={lists.length < 2} onClick={() => open('delete')}><Trash2 className="h-3.5 w-3.5" /></Button>
  </div><Dialog open={!!action} onOpenChange={(value) => { if (!value && !busy) setAction(''); }}><DialogContent aria-describedby={undefined}>
    <DialogTitle>{action === 'create' ? 'New watchlist' : action === 'rename' ? 'Rename watchlist' : 'Remove watchlist'}</DialogTitle>
    <form onSubmit={save} className="space-y-3">{action === 'delete' ? <p className="text-sm">Remove “{name}”? Instruments, positions and orders are retained.</p> : <Input aria-label="Watchlist name" required maxLength={60} value={name} onChange={(e) => setName(e.target.value)} />}
      <Button disabled={busy} className="w-full">{busy ? 'Saving…' : 'Confirm'}</Button></form>
  </DialogContent></Dialog></>;
}
WatchlistPicker.propTypes = { lists: PropTypes.array.isRequired, activeId: PropTypes.number.isRequired, onChange: PropTypes.func.isRequired, onRefresh: PropTypes.func.isRequired };
