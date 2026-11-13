import { useState } from 'react';
import { Alert, Box, Button, Chip, Dialog, DialogActions, DialogContent, DialogTitle, Divider, Paper, Stack, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TextField, Typography } from '@mui/material';
import { date, request, useResource } from './data';
import { LoadState, PageTitle } from './Page';
import FormulationResult, { type Calculation } from './FormulationResult';
import type { BuilderInput, BuilderSeed } from './FormulationBuilder';

type Saved = { id: number; formulation_name: string; formulation_description: string; version_number: number; created_at: string; payload: Calculation & Record<string, unknown> };
const base = '/api/v1/feed/formulation';
export default function FormulationsPage({ token, onCreate, onRevise }: { token: string; onCreate: () => void; onRevise: (seed: BuilderSeed) => void }) {
  const resource = useResource<Saved[]>(`${base}/all`, token);
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState<Saved | null>(null);
  const [history, setHistory] = useState<Saved[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState('');
  const [editor, setEditor] = useState<'edit' | 'version' | null>(null);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [deleting, setDeleting] = useState<Saved | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  async function view(item: Saved) {
    setSelected(item); setHistory([]); setHistoryError(''); setHistoryLoading(true);
    try { setHistory(await request<Saved[]>('GET', `${base}/${item.id}/versions`, token)); }
    catch (cause) { setHistoryError((cause as Error).message); }
    finally { setHistoryLoading(false); }
  }
  function edit(mode: 'edit' | 'version') {
    if (!selected) return;
    setName(selected.formulation_name || ''); setDescription(selected.formulation_description || ''); setError(''); setEditor(mode);
  }
  async function save() {
    if (!selected || !name.trim()) return;
    setBusy(true); setError('');
    try {
      const payload = { formulation_name: name.trim(), formulation_description: description.trim(), payload: selected.payload };
      const response = await request<{ formulation: Saved }>(editor === 'edit' ? 'PUT' : 'POST', editor === 'edit' ? `${base}/edit/${selected.id}` : `${base}/${selected.id}/versions`, token, payload);
      setEditor(null); setNotice(editor === 'edit' ? 'Formulation updated.' : 'New version created.'); resource.refresh(); await view(response.formulation);
    } catch (cause) { setError((cause as Error).message); } finally { setBusy(false); }
  }
  async function remove() {
    if (!deleting) return;
    setBusy(true); setError('');
    try {
      await request('DELETE', `${base}/remove/${deleting.id}`, token); setDeleting(null); setSelected(null); setNotice('Selected version deleted. Other versions are preserved.'); resource.refresh();
    } catch (cause) { setError((cause as Error).message); } finally { setBusy(false); }
  }
  return <>
    <PageTitle title="Formulations" description="Manage your saved formulas and their version history." action={<Button variant="contained" onClick={onCreate}>Create formulation</Button>} />
    {notice && <Alert severity="success" sx={{ mb: 2 }} onClose={() => setNotice('')}>{notice}</Alert>}
    <LoadState {...resource} retry={resource.refresh} />
    {selected ? <Stack spacing={3}>
      <Box><Button onClick={() => setSelected(null)}>Back to formulations</Button><Typography variant="h5" sx={{ mt: 1 }}>{selected.formulation_name || 'Untitled'}</Typography><Typography color="text.secondary">Version {selected.version_number} · {date(selected.created_at)}</Typography><Typography sx={{ my: 2 }}>{selected.formulation_description}</Typography><Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: 'wrap' }}><Button variant="outlined" onClick={() => edit('edit')}>Edit details</Button>{!!selected.payload.portal_input && <Button variant="outlined" onClick={() => onRevise({ id: selected.id, name: selected.formulation_name, description: selected.formulation_description, mode: String(selected.payload.portal_mode || 'v4'), input: selected.payload.portal_input as BuilderInput })}>Revise calculation</Button>}<Button variant="outlined" disabled={historyLoading || !!historyError || !history.length || selected.id !== history[0]?.id} onClick={() => edit('version')}>Create new version</Button><Button color="error" onClick={() => { setError(''); setDeleting(selected); }}>Delete this version</Button></Stack></Box>
      {!selected.payload.portal_input && <Alert severity="info">This older result has no saved ingredient inputs. Its details and version history remain editable; create a formulation to run a new calculation.</Alert>}
      <Paper variant="outlined" sx={{ p: { xs: 2, md: 3 } }}><FormulationResult result={selected.payload} /></Paper>
      <Box><Typography variant="h6" sx={{ mb: 1 }}>Version history</Typography><LoadState loading={historyLoading} error={historyError} retry={() => void view(selected)} /><Stack divider={<Divider />}>{history.map((item) => <Stack key={item.id} direction="row" sx={{ py: 1.5, justifyContent: 'space-between', alignItems: 'center' }}><Box><Typography sx={{ fontWeight: 650 }}>{item.formulation_name} · v{item.version_number}</Typography><Typography variant="body2" color="text.secondary">{date(item.created_at)}</Typography></Box><Button disabled={selected.id === item.id} onClick={() => setSelected(item)}>View</Button></Stack>)}</Stack></Box>
    </Stack> : <>
      <TextField fullWidth size="small" label="Search formulations" value={search} onChange={(event) => setSearch(event.target.value)} sx={{ mb: 2 }} />
      <TableContainer component={Paper} variant="outlined"><Table sx={{ minWidth: 560 }}><TableHead><TableRow><TableCell>Name</TableCell><TableCell>Version</TableCell><TableCell>Saved</TableCell><TableCell align="right">Actions</TableCell></TableRow></TableHead><TableBody>{(resource.data || []).filter((item) => `${item.formulation_name} ${item.formulation_description}`.toLowerCase().includes(search.toLowerCase())).map((item) => <TableRow key={item.id} hover><TableCell><Typography sx={{ fontWeight: 650 }}>{item.formulation_name || 'Untitled'}</Typography><Typography variant="body2" color="text.secondary">{item.formulation_description}</Typography></TableCell><TableCell><Chip size="small" label={`v${item.version_number}`} /></TableCell><TableCell>{date(item.created_at)}</TableCell><TableCell align="right"><Button onClick={() => void view(item)}>View formulation</Button></TableCell></TableRow>)}{!resource.loading && !resource.error && !(resource.data || []).some((item) => `${item.formulation_name} ${item.formulation_description}`.toLowerCase().includes(search.toLowerCase())) && <TableRow><TableCell colSpan={4} sx={{ textAlign: 'center', py: 6 }}>{search ? 'No formulations match your search.' : 'No saved formulations yet. Create and save your first calculation.'}</TableCell></TableRow>}</TableBody></Table></TableContainer>
    </>}
    <Dialog open={!!editor} fullWidth maxWidth="sm" onClose={busy ? undefined : () => setEditor(null)}><DialogTitle>{editor === 'edit' ? 'Edit formulation details' : 'Create a formulation version'}</DialogTitle><Box component="form" onSubmit={(event) => { event.preventDefault(); void save(); }}><DialogContent dividers><Stack spacing={2}>{error && <Alert severity="error">{error}</Alert>}<Alert severity="info">{editor === 'edit' ? 'Updates this version in place. Calculation results are preserved.' : 'Creates a snapshot of the latest result with these details.'}</Alert><TextField label="Name" value={name} onChange={(event) => setName(event.target.value)} required /><TextField label="Description" value={description} onChange={(event) => setDescription(event.target.value)} multiline /></Stack></DialogContent><DialogActions><Button disabled={busy} onClick={() => setEditor(null)}>Cancel</Button><Button disabled={busy || !name.trim()} type="submit" variant="contained">{busy ? 'Saving…' : 'Save'}</Button></DialogActions></Box></Dialog>
    <Dialog open={!!deleting} onClose={busy ? undefined : () => setDeleting(null)}><DialogTitle>Delete version {deleting?.version_number}?</DialogTitle><DialogContent>{error && <Alert severity="error">{error}</Alert>}Only this version will be removed. This cannot be undone.</DialogContent><DialogActions><Button disabled={busy} onClick={() => setDeleting(null)}>Cancel</Button><Button disabled={busy} color="error" variant="contained" onClick={() => void remove()}>Delete version</Button></DialogActions></Dialog>
  </>;
}
