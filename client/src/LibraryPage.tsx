import { useState } from 'react';
import { Alert, Box, Button, Checkbox, Chip, Dialog, DialogActions, DialogContent, DialogTitle, FormControlLabel, MenuItem, Paper, Stack, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TextField, Typography } from '@mui/material';
import { accountId, label, money, request, tenNutrients, useResource } from './data';
import { LoadState, PageTitle } from './Page';
import NutrientEditor, { composition, nutrientRows, type NutrientRow } from './NutrientEditor';

export type LibraryItem = { id: number; user_id: number | null; name?: string; price?: number; is_available?: boolean; nutrient_requirement_name?: string; nutrient_requirement_description?: string; composition: Record<string, number> };
export default function LibraryPage({ kind, token }: { kind: 'ingredients' | 'requirements'; token: string }) {
  const ingredients = kind === 'ingredients';
  const base = ingredients ? '/v4/ingredients' : '/api/v1/nutrient-requirements';
  const resource = useResource<{ ingredients?: LibraryItem[]; nutrient_requirements?: LibraryItem[] }>(`${base}/all`, token);
  const [search, setSearch] = useState('');
  const [editor, setEditor] = useState<LibraryItem | 'new' | null>(null);
  const [deleting, setDeleting] = useState<LibraryItem | null>(null);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [price, setPrice] = useState('');
  const [available, setAvailable] = useState(true);
  const [mode, setMode] = useState('custom');
  const [rows, setRows] = useState<NutrientRow[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const items = (ingredients ? resource.data?.ingredients : resource.data?.nutrient_requirements) || [];
  const title = ingredients ? 'Ingredients' : 'Nutrient requirements';
  const itemName = (item: LibraryItem) => item.name || item.nutrient_requirement_name || 'Untitled';
  const shown = items.filter((item) => `${itemName(item)} ${item.nutrient_requirement_description || ''}`.toLowerCase().includes(search.toLowerCase()));
  function open(item: LibraryItem | 'new') {
    setEditor(item); setError(''); setMode('custom');
    setName(item === 'new' ? '' : itemName(item));
    setDescription(item === 'new' ? '' : item.nutrient_requirement_description || '');
    setPrice(item === 'new' ? '' : String(item.price ?? ''));
    setAvailable(item === 'new' ? true : item.is_available !== false);
    setRows(item === 'new' ? [{ id: crypto.randomUUID(), name: 'protein_percent', value: '' }] : nutrientRows(item.composition));
  }
  async function save() {
    setError(''); setBusy(true);
    try {
      if (!name.trim()) throw new Error('Enter a name.');
      if (ingredients && (!price.trim() || !Number.isFinite(Number(price)) || Number(price) < 0)) throw new Error('Enter a nonnegative price.');
      const values = composition(rows);
      const payload = ingredients ? { name: name.trim(), price: Number(price), is_available: available, composition: values } : { nutrient_requirement_name: name.trim(), nutrient_requirement_description: description.trim(), composition: values };
      const creating = editor === 'new';
      const path = creating ? (!ingredients && mode === 'ten' ? '/v2/nutrient-requirements/create' : `${base}/create`) : `${base}/update/${(editor as LibraryItem).id}`;
      await request(creating ? 'POST' : 'PUT', path, token, payload);
      setEditor(null); setNotice('Saved successfully.'); resource.refresh();
    } catch (cause) { setError((cause as Error).message); } finally { setBusy(false); }
  }
  async function remove() {
    if (!deleting) return;
    setBusy(true); setError('');
    try { await request('DELETE', `${base}/delete/${deleting.id}`, token); setDeleting(null); setNotice('Deleted successfully.'); resource.refresh(); }
    catch (cause) { setError((cause as Error).message); } finally { setBusy(false); }
  }
  return <>
    <PageTitle title={title} description={ingredients ? 'Manage ingredient prices, availability, and nutrient composition.' : 'Save named nutrient targets for your formulation workflows.'} action={<Button variant="contained" onClick={() => open('new')}>Add {ingredients ? 'ingredient' : 'requirement'}</Button>} />
    <LoadState {...resource} retry={resource.refresh} />
    {notice && <Alert severity="success" onClose={() => setNotice('')} sx={{ mb: 2 }}>{notice}</Alert>}
    <Paper variant="outlined" sx={{ p: 2, mb: 2 }}><TextField size="small" fullWidth label={`Search ${title.toLowerCase()}`} value={search} onChange={(event) => setSearch(event.target.value)} /></Paper>
    <TableContainer component={Paper} variant="outlined"><Table sx={{ minWidth: 640 }}><TableHead><TableRow><TableCell>Name</TableCell><TableCell>{ingredients ? 'Price / kg' : 'Description'}</TableCell><TableCell>Nutrients</TableCell><TableCell>Access</TableCell><TableCell align="right">Actions</TableCell></TableRow></TableHead><TableBody>
      {shown.map((item) => <TableRow key={item.id} hover><TableCell><Typography sx={{ fontWeight: 650 }}>{itemName(item)}</Typography>{ingredients && <Typography variant="caption" color="text.secondary">{item.is_available ? 'Available' : 'Unavailable'}</Typography>}</TableCell><TableCell>{ingredients ? money(item.price || 0) : item.nutrient_requirement_description || '—'}</TableCell><TableCell>{Object.entries(item.composition).map(([key, value]) => <Typography key={key} variant="body2">{label(key)}: {value}</Typography>)}</TableCell><TableCell><Chip size="small" variant="outlined" label={item.user_id === null ? 'Shared · read only' : 'Owned'} /></TableCell><TableCell align="right">{item.user_id === accountId(token) && <><Button onClick={() => open(item)}>Edit</Button><Button color="error" onClick={() => { setError(''); setDeleting(item); }}>Delete</Button></>}</TableCell></TableRow>)}
      {!resource.loading && !resource.error && !shown.length && <TableRow><TableCell colSpan={5} sx={{ py: 6, textAlign: 'center' }}>{search ? 'No records match your search.' : `No ${title.toLowerCase()} yet. Add your first record to get started.`}</TableCell></TableRow>}
    </TableBody></Table></TableContainer>
    <Dialog open={editor !== null} onClose={busy ? undefined : () => setEditor(null)} fullWidth maxWidth="md"><DialogTitle>{editor === 'new' ? 'Add' : 'Edit'} {ingredients ? 'ingredient' : 'nutrient requirement'}</DialogTitle><Box component="form" onSubmit={(event) => { event.preventDefault(); void save(); }}><DialogContent dividers><Stack spacing={2}>
      {error && <Alert severity="error">{error}</Alert>}<TextField label="Name" value={name} onChange={(event) => setName(event.target.value)} required />
      {ingredients ? <><TextField label="Price per kg (PHP)" type="number" slotProps={{ htmlInput: { min: 0, step: 'any' } }} value={price} onChange={(event) => setPrice(event.target.value)} required /><FormControlLabel control={<Checkbox checked={available} onChange={(event) => setAvailable(event.target.checked)} />} label="Available for formulation" /></> : <TextField label="Description" value={description} onChange={(event) => setDescription(event.target.value)} multiline />}
      {!ingredients && editor === 'new' && <TextField select label="Target format" value={mode} onChange={(event) => { setMode(event.target.value); if (event.target.value === 'ten') setRows(tenNutrients.map((key) => ({ id: crypto.randomUUID(), name: key, value: rows.find((row) => row.name === key)?.value || '' }))); }}><MenuItem value="custom">Custom nutrients</MenuItem><MenuItem value="ten">Standard ten nutrients (V3)</MenuItem></TextField>}
      <Typography variant="body2" color="text.secondary">Use consistent units for targets and ingredient values. Blank values are never treated as zero.</Typography><NutrientEditor rows={rows} onChange={setRows} fixed={!ingredients && mode === 'ten'} />
    </Stack></DialogContent><DialogActions><Button disabled={busy} onClick={() => setEditor(null)}>Cancel</Button><Button type="submit" variant="contained" disabled={busy}>{busy ? 'Saving…' : 'Save'}</Button></DialogActions></Box></Dialog>
    <Dialog open={!!deleting} onClose={busy ? undefined : () => setDeleting(null)}><DialogTitle>Delete {deleting && itemName(deleting)}?</DialogTitle><DialogContent>{error && <Alert severity="error">{error}</Alert>}This permanently removes this record.</DialogContent><DialogActions><Button disabled={busy} onClick={() => setDeleting(null)}>Cancel</Button><Button disabled={busy} color="error" variant="contained" onClick={() => void remove()}>{busy ? 'Deleting…' : 'Delete'}</Button></DialogActions></Dialog>
  </>;
}
