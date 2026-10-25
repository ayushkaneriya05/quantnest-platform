import { LoaderMark } from '@/shared/components/ui/global-loader';
import { formatDate } from "@/shared/utils/formatters";
import { useEffect, useRef, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { CheckCircle2, ImagePlus, X } from 'lucide-react';
import api from '@/shared/services/api';
import { useNotifications } from '@/shared/hooks/useNotifications';
import { updateUser } from '@/shared/store/authSlice';
import { getApiErrorDetails, getApiErrorMessage } from '@/shared/utils/apiErrors';
import { Button } from '@/shared/components/ui/button';
import { Input } from '@/shared/components/ui/input';
import { Label } from '@/shared/components/ui/label';
import { Textarea } from '@/shared/components/ui/textarea';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/shared/components/ui/card';
import UserAvatar from '@/shared/components/UserAvatar';
import ThemeSwitch from '@/shared/components/ThemeSwitch';

const fields = user => ({ first_name: user?.first_name || '', last_name: user?.last_name || '', username: user?.username || '', bio: user?.bio || '' });
export default function ProfileTab() {
  const user = useSelector(state => state.auth.user);
  const dispatch = useDispatch();
  const { notify } = useNotifications();
  const [form, setForm] = useState(() => fields(user));
  const [file, setFile] = useState(null);
  const [remove, setRemove] = useState(false);
  const [preview, setPreview] = useState(null);
  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState(false);
  const busy = useRef(false);
  const identity = useRef(user?.id);
  useEffect(() => {
    if (identity.current !== user?.id) { setForm(fields(user)); setFile(null); setRemove(false); identity.current = user?.id; }
  }, [user]);
  useEffect(() => {
    const url = file ? URL.createObjectURL(file) : null;
    setPreview(url);
    return () => { if (url) URL.revokeObjectURL(url); };
  }, [file]);
  const fieldError = name => Array.isArray(errors[name]) ? errors[name][0] : errors[name];
  const change = event => {
    const { name, value } = event.target;
    setForm(current => ({ ...current, [name]: value }));
    setErrors(current => ({ ...current, [name]: null }));
  };
  const chooseImage = event => {
    const selected = event.target.files[0]; event.target.value = '';
    if (!selected) return;
    if (!['image/png', 'image/jpeg', 'image/webp'].includes(selected.type) || selected.size > 2 * 1024 * 1024) {
      setErrors(current => ({ ...current, avatar: 'Choose a PNG, JPEG or WebP image no larger than 2 MiB.' })); return;
    }
    setFile(selected); setRemove(false); setErrors(current => ({ ...current, avatar: null }));
  };
  async function save(event) {
    event.preventDefault(); if (busy.current) return;
    busy.current = true; setSaving(true); setErrors({});
    try {
      const data = new FormData();
      Object.entries(form).forEach(([key, value]) => data.append(key, value.trim()));
      if (file) data.append('avatar', file); else if (remove) data.append('avatar', '');
      const response = await api.patch('/users/profile/', data);
      dispatch(updateUser(response.data)); setForm(fields(response.data)); setFile(null); setRemove(false); notify.success('Your profile has been saved.');
    } catch (failure) { setErrors(getApiErrorDetails(failure)); notify.error(getApiErrorMessage(failure, 'Your profile could not be saved.')); }
    finally { busy.current = false; setSaving(false); }
  }
  return <form onSubmit={save} className="grid items-start gap-5 lg:grid-cols-[280px_1fr]">
    <aside className="space-y-4">
      <Card><CardContent className="p-5"><div className="flex items-center gap-4 lg:flex-col lg:gap-0 lg:text-center"><UserAvatar src={preview || (remove ? null : user?.avatar)} className="h-16 w-16 text-xl lg:h-24 lg:w-24 lg:text-2xl" refreshOnError={!file && !remove} /><div className="min-w-0 lg:mt-4"><p className="max-w-full break-words font-semibold">{[user?.first_name, user?.last_name].filter(Boolean).join(' ') || user?.username || 'Your profile'}</p><p className="mt-1 max-w-full break-all text-xs text-muted-foreground">{user?.email}</p></div></div><div className="mt-4 flex flex-wrap gap-2 lg:justify-center"><Label htmlFor="avatar-upload" className="inline-flex min-h-10 cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-xs hover:bg-accent"><ImagePlus className="h-4 w-4" />Choose photo</Label><input id="avatar-upload" className="sr-only" type="file" accept="image/png,image/jpeg,image/webp" disabled={saving} onChange={chooseImage} />{(file || (!remove && user?.avatar)) && <Button type="button" variant="ghost" size="sm" disabled={saving} onClick={() => { setFile(null); setRemove(true); }}><X className="h-3.5 w-3.5" />Remove</Button>}</div><p className="mt-3 text-xs leading-5 text-muted-foreground lg:text-center">PNG, JPEG or WebP · up to 2 MiB.<br />Save changes to update your photo.</p>{fieldError('avatar') && <p role="alert" className="mt-3 text-xs text-destructive-text">{fieldError('avatar')}</p>}
        <dl className="mt-5 space-y-3 border-t pt-4 text-sm"><div className="flex justify-between gap-3"><dt className="text-muted-foreground">Workspace plan</dt><dd className="font-medium">{user?.workspace_plan?.name || 'Loading…'}</dd></div><div className="flex justify-between gap-3"><dt className="text-muted-foreground">Member since</dt><dd>{user?.date_joined ? formatDate(user.date_joined, { month: 'short', year: 'numeric' }) : 'Unavailable'}</dd></div><div className="flex justify-between gap-3"><dt className="text-muted-foreground">Email</dt><dd className="flex items-center gap-1.5">{user?.is_email_verified && <CheckCircle2 className="h-4 w-4 text-success" />}{user?.is_email_verified ? 'Verified' : 'Not verified'}</dd></div></dl>
      </CardContent></Card>
      <Card><CardContent className="flex items-center justify-between gap-3 p-5 lg:block"><div><h2 className="font-medium">Appearance</h2><p className="mt-1 text-xs leading-5 text-muted-foreground lg:mb-4">Theme for this device.</p></div><ThemeSwitch showLabel /></CardContent></Card>
    </aside>
    <Card><CardHeader className="p-5 pb-4"><CardTitle className="text-lg">Profile information</CardTitle><CardDescription>Your name and personal profile details.</CardDescription></CardHeader><CardContent className="space-y-5 px-5 pb-5">
      <div className="grid gap-4 sm:grid-cols-2">{[['first_name', 'First name', 'given-name', 30], ['last_name', 'Last name', 'family-name', 30], ['username', 'Username', 'username', 150]].map(([name, label, autocomplete, limit]) => <div className="space-y-2" key={name}><Label htmlFor={name}>{label}</Label><Input id={name} name={name} autoComplete={autocomplete} maxLength={limit} value={form[name]} onChange={change} disabled={saving} aria-invalid={Boolean(fieldError(name))} />{fieldError(name) && <p className="text-xs text-destructive-text">{fieldError(name)}</p>}</div>)}<div className="space-y-2"><Label htmlFor="profile-email">Email address</Label><Input id="profile-email" value={user?.email || ''} disabled /><p className="text-xs leading-5 text-muted-foreground">Contact support if your verified email needs changing.</p></div></div>
      <div className="space-y-2"><Label htmlFor="bio">About you</Label><Textarea id="bio" name="bio" value={form.bio} onChange={change} disabled={saving} maxLength={500} rows={4} placeholder="A short introduction for your personal profile" /><div className="flex justify-between gap-3 text-xs text-muted-foreground"><span>Optional. Use at least 10 characters when filled.</span><span>{form.bio.length}/500</span></div>{fieldError('bio') && <p className="text-xs text-destructive-text">{fieldError('bio')}</p>}</div><div className="flex justify-end border-t pt-4"><Button type="submit" disabled={saving}>{saving && <LoaderMark className="h-4 w-4" />}{saving ? 'Saving…' : 'Save changes'}</Button></div>
    </CardContent></Card>
  </form>;
}
