import { useEffect, useRef, useState } from "react";
import PropTypes from "prop-types";
import { Pencil, Trash2 } from "lucide-react";
import { Input } from "@/shared/components/ui/input";
import { Button } from "@/shared/components/ui/button";
import { TooltipHint } from "@/shared/components/ui/tooltip";
import { customConfirm } from "@/shared/components/ui/custom-dialog";
import { researchApi } from "@/shared/services/researchApi";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";

const groupName = (date) => {
  const day = new Date(date).toDateString();
  const yesterday = new Date(); yesterday.setDate(yesterday.getDate() - 1);
  return day === new Date().toDateString() ? "Today" : day === yesterday.toDateString() ? "Yesterday" : "Earlier";
};

export default function ResearchConversations({ session, onSelect, onDelete, refreshKey }) {
  const [items, setItems] = useState([]);
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [more, setMore] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState(null);
  const [title, setTitle] = useState("");
  const version = useRef(0);
  useEffect(() => { setPage(1); }, [refreshKey]);
  useEffect(() => {
    const current = ++version.current;
    const timer = setTimeout(async () => {
      setLoading(true); setError("");
      try {
        const response = await researchApi.sessions({ kind: "CHAT", search: query, page });
        if (current !== version.current) return;
        setItems((previous) => page === 1 ? response.data.results : [...new Map([...previous, ...response.data.results].map((item) => [item.id, item])).values()]);
        setMore(Boolean(response.data.next));
      } catch (error) { if (current === version.current) setError(getApiErrorMessage(error, "Could not load conversations")); }
      finally { if (current === version.current) setLoading(false); }
    }, query ? 250 : 0);
    return () => { version.current += 1; clearTimeout(timer); };
  }, [query, page, refreshKey]);
  async function rename(item) {
    try {
      const response = await researchApi.updateSession(item.id, { title });
      setItems((previous) => previous.map((value) => value.id === item.id ? response.data : value)); setEditing(null);
    } catch (error) { setError(getApiErrorMessage(error, "Could not rename conversation")); }
  }
  async function remove(item) {
    if (!await customConfirm(`Delete “${item.title}” and its research evidence?`, "Delete conversation")) return;
    try { await researchApi.deleteSession(item.id); setItems((previous) => previous.filter((value) => value.id !== item.id)); onDelete(item.id); }
    catch (error) { setError(getApiErrorMessage(error, "Could not delete conversation")); }
  }
  return <div className="flex h-full min-h-0 flex-col gap-3">
    <Input className="h-9 text-xs" aria-label="Search conversations" placeholder="Search conversations" value={query} onChange={(event) => { setQuery(event.target.value); setPage(1); }} />
    <div className="scrollbar-thin-theme min-h-0 flex-1 space-y-4 overflow-y-auto pr-1">
      {["Today", "Yesterday", "Earlier"].map((group) => { const rows = items.filter((item) => groupName(item.updated_at) === group); return rows.length > 0 && <section key={group}><h3 className="mb-2 text-xs text-muted-foreground">{group}</h3><ul className="space-y-1">{rows.map((item) => <li key={item.id} className={`group rounded-lg p-2 ${String(item.id) === String(session) ? "bg-indigo-500/15" : "hover:bg-card"}`}>
        {editing === item.id ? <form className="space-y-2" onSubmit={(event) => { event.preventDefault(); rename(item); }}><Input aria-label="Conversation name" autoFocus required maxLength={160} value={title} onChange={(event) => setTitle(event.target.value)} onKeyDown={(event) => { if (event.key === "Escape") setEditing(null); }} /><div className="flex gap-2"><Button size="sm" type="submit">Save</Button><Button size="sm" variant="ghost" onClick={() => setEditing(null)}>Cancel</Button></div></form> : <>
          <div className="flex items-center gap-1"><TooltipHint content={item.title}><button className="min-w-0 flex-1 truncate py-1 text-left text-sm text-foreground" onClick={() => onSelect(item.id)}>{item.title}</button></TooltipHint>
          <div className="flex shrink-0 gap-0.5 lg:opacity-0 lg:group-hover:opacity-100 lg:group-focus-within:opacity-100"><button aria-label={`Rename ${item.title}`} className="rounded p-1.5 text-muted-foreground hover:text-indigo-800 dark:hover:text-indigo-300" onClick={() => { setTitle(item.title); setEditing(item.id); }}><Pencil size={13} /></button><button aria-label={`Delete ${item.title}`} className="rounded p-1.5 text-muted-foreground hover:text-rose-800 dark:hover:text-rose-300" onClick={() => remove(item)}><Trash2 size={13} /></button></div></div>
        </>}
      </li>)}</ul></section>; })}
      {!items.length && !loading && <p className="text-sm text-muted-foreground">{query ? "No conversations match." : "Your research conversations will appear here."}</p>}
      {error && <p role="alert" className="text-sm text-rose-700 dark:text-rose-300">{error}</p>}
      {loading && <p className="text-xs text-muted-foreground">Loading conversations…</p>}
      {more && <Button variant="outline" className="w-full" disabled={loading} onClick={() => setPage(page + 1)}>Load more conversations</Button>}
    </div>
  </div>;
}
ResearchConversations.propTypes = { session: PropTypes.string, onSelect: PropTypes.func.isRequired, onDelete: PropTypes.func.isRequired, refreshKey: PropTypes.string };
