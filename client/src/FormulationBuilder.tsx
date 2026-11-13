import { useEffect, useState } from 'react';
import {
  Alert, Box, Button, Card, CardContent, Divider, MenuItem, Paper,
  Stack, TextField, Typography,
} from '@mui/material';
import AddRoundedIcon from '@mui/icons-material/AddRounded';
import DeleteOutlineRoundedIcon from '@mui/icons-material/DeleteOutlineRounded';
import { apiRequest, resultMessage } from './api';
import { fourNutrients, tenNutrients, label, useResource } from './data';
import type { LibraryItem } from './LibraryPage';
import FormulationResult from './FormulationResult';

type Target = { id: string; name: string; value: string };
type Ingredient = {
  id: string;
  name: string;
  cost: string;
  min: string;
  max: string;
  nutrients: Record<string, string>;
};
type SavedIngredient = {
  id: number;
  name: string;
  price: number;
  composition: Record<string, number>;
};
export type BuilderInput = { ingredients: { name: string; cost_per_kg: number; min_percentage: number; max_percentage: number; nutrients?: Record<string, number>; [key: string]: unknown }[]; nutrient_requirements: Record<string, number> };
export type BuilderSeed = { id: number; name: string; description: string; mode: string; input: BuilderInput };
type Result = import('./FormulationResult').Calculation;
type Props = { token: string; onAuthRequired: () => void; seed?: BuilderSeed | null };

const reservedNames = new Set([
  'name', 'cost_per_kg', 'min_percentage', 'max_percentage',
  'total_ingredient_percentage', 'model_dump',
]);

function newIngredient(): Ingredient {
  return { id: crypto.randomUUID(), name: '', cost: '', min: '0', max: '100', nutrients: {} };
}

function nonnegative(value: string): number | null {
  if (value.trim() === '') return null;
  const number = Number(value);
  return Number.isFinite(number) && number >= 0 ? number : null;
}

export default function FormulationBuilder({ token, onAuthRequired, seed }: Props) {
  const [mode, setMode] = useState(seed?.mode || 'v4');
  const [targets, setTargets] = useState<Target[]>(() => seed ? Object.entries(seed.input.nutrient_requirements).map(([name, value]) => ({ id: name, name, value: String(value) })) : [{ id: crypto.randomUUID(), name: 'protein_percent', value: '' }]);
  const [ingredients, setIngredients] = useState<Ingredient[]>(() => seed ? seed.input.ingredients.map((item) => ({ id: crypto.randomUUID(), name: item.name, cost: String(item.cost_per_kg), min: String(item.min_percentage * 100), max: String(item.max_percentage * 100), nutrients: Object.fromEntries(Object.keys(seed.input.nutrient_requirements).map((key) => [key, String(item.nutrients?.[key] ?? item[key] ?? '')])) })) : [newIngredient()]);
  const [savedIngredients, setSavedIngredients] = useState<SavedIngredient[]>([]);
  const [savedError, setSavedError] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<Result | null>(null);
  const [rawResult, setRawResult] = useState<unknown>(null);
  const [formulationName, setFormulationName] = useState(seed?.name || '');
  const [formulationDescription, setFormulationDescription] = useState(seed?.description || '');
  const [saveMode, setSaveMode] = useState('version');
  const requirements = useResource<{ nutrient_requirements?: LibraryItem[] }>('/api/v1/nutrient-requirements/all', token);
  const [saveMessage, setSaveMessage] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!token) {
      setSavedIngredients([]);
      return;
    }
    let active = true;
    void apiRequest('GET', '/v4/ingredients/all', token).then((response) => {
      if (!active) return;
      if (response.ok && response.data && typeof response.data === 'object' && 'ingredients' in response.data) {
        const list = response.data.ingredients;
        if (Array.isArray(list)) setSavedIngredients((list as (SavedIngredient & { is_available?: boolean })[]).filter((item) => item.is_available !== false));
      } else if (!response.ok) {
        setSavedError(resultMessage(response));
      }
    }).catch(() => { if (active) setSavedError('Could not load saved ingredients.'); });
    return () => { active = false; };
  }, [token]);

  function updateTarget(id: string, patch: Partial<Target>) {
    setTargets((current) => current.map((item) => item.id === id ? { ...item, ...patch } : item));
    setResult(null);
  }

  function updateIngredient(id: string, patch: Partial<Ingredient>) {
    setIngredients((current) => current.map((item) => item.id === id ? { ...item, ...patch } : item));
    setResult(null);
  }

  function addSaved(id: number) {
    const saved = savedIngredients.find((item) => item.id === id);
    if (!saved) return;
    const nutrients = Object.fromEntries(targets.map((target) => [
      target.id,
      saved.composition[target.name] === undefined ? '' : String(saved.composition[target.name]),
    ]));
    const added: Ingredient = {
      id: crypto.randomUUID(), name: saved.name, cost: String(saved.price),
      min: '0', max: '100', nutrients,
    };
    setIngredients((current) => current.length === 1 && !current[0].name && !current[0].cost
      ? [added] : [...current, added]);
    setResult(null);
  }

  function buildRequest(): BuilderInput | null {
    if (!targets.length) { setError('Add at least one nutrient target.'); return null; }
    if (!ingredients.length) { setError('Add at least one ingredient.'); return null; }
    const names = targets.map((item) => item.name.trim());
    if (names.some((name, index) => !name || name !== targets[index].name || name.startsWith('_') || reservedNames.has(name))) {
      setError('Nutrient names must be filled, trimmed, and not reserved.');
      return null;
    }
    if (new Set(names).size !== names.length) { setError('Each nutrient target needs a unique name.'); return null; }
    const requirements: Record<string, number> = {};
    for (const target of targets) {
      const value = nonnegative(target.value);
      if (value === null) { setError(`Enter a nonnegative target for ${target.name}.`); return null; }
      requirements[target.name] = value;
    }
    let totalMin = 0;
    let totalMax = 0;
    const payloadIngredients = [];
    for (const ingredient of ingredients) {
      if (!ingredient.name.trim()) { setError('Give every ingredient a name.'); return null; }
      const cost = nonnegative(ingredient.cost);
      const min = nonnegative(ingredient.min);
      const max = nonnegative(ingredient.max);
      if (cost === null || min === null || max === null || min > max || max > 100) {
        setError(`Check cost and inclusion limits for ${ingredient.name}. Use 0–100 for limits.`);
        return null;
      }
      totalMin += min;
      totalMax += max;
      const nutrients: Record<string, number> = {};
      for (const target of targets) {
        const value = nonnegative(ingredient.nutrients[target.id] ?? '');
        if (value === null) {
          setError(`Enter ${target.name} for ${ingredient.name}. Use 0 for a known zero.`);
          return null;
        }
        nutrients[target.name] = value;
      }
      payloadIngredients.push({
        name: ingredient.name.trim(), cost_per_kg: cost,
        min_percentage: min / 100, max_percentage: max / 100, ...(mode === 'v4' ? { nutrients } : nutrients),
      });
    }
    if (totalMin > 100.000001 || totalMax < 99.999999) {
      setError('Ingredient inclusion limits must allow a 100% mixture.');
      return null;
    }
    return { ingredients: payloadIngredients, nutrient_requirements: requirements };
  }

  async function formulate() {
    if (!token) { onAuthRequired(); return; }
    setError('');
    setSaveMessage('');
    setResult(null); setRawResult(null);
    const request = buildRequest();
    if (!request) return;
    setBusy(true);
    setResult(null);
    setRawResult(null);
    try {
      const path = mode === 'v1' ? '/api/v1/feed/formulate' : `/${mode}/feed/formulate`;
      const response = await apiRequest('POST', path, token, request);
      if (!response.ok) { setError(resultMessage(response)); return; }
      setRawResult({ ...(response.data as object), portal_input: request, portal_mode: mode });
      setResult(response.data as Result);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not reach the API.');
    } finally {
      setBusy(false);
    }
  }

  async function save() {
    if (!rawResult || !formulationName.trim()) return;
    setSaving(true);
    setSaveMessage('');
    try {
      const path = seed ? saveMode === 'edit' ? `/api/v1/feed/formulation/edit/${seed.id}` : `/api/v1/feed/formulation/${seed.id}/versions` : '/api/v1/feed/formulation/save';
      const response = await apiRequest(seed && saveMode === 'edit' ? 'PUT' : 'POST', path, token, {
        formulation_name: formulationName.trim(),
        formulation_description: formulationDescription.trim(),
        payload: rawResult,
      });
      setSaveMessage(response.ok ? 'Formulation saved.' : resultMessage(response));
      if (response.ok) setRawResult(null);
    } catch (cause) {
      setSaveMessage(cause instanceof Error ? cause.message : 'Could not save the formulation.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <Stack spacing={3}>
      <Box>
        <Typography component="h1" variant="h4" sx={{ fontWeight: 750 }}>{seed ? 'Revise formulation' : 'Create a feed formulation'}</Typography>
        <Typography color="text.secondary" sx={{ mt: 1 }}>Choose nutrient targets, add ingredients, and calculate the least-cost 100% mixture.</Typography>
      </Box>
      {!token && <Alert severity="info" action={<Button onClick={onAuthRequired}>Sign in</Button>}>Sign in to calculate and save formulations.</Alert>}
      <TextField select label="Calculation mode" value={mode} onChange={(event) => {
        const next = event.target.value;
        setMode(next); setResult(null);
        if (next !== 'v4') {
          const keys = next === 'v3' ? tenNutrients : fourNutrients;
          const nextTargets = keys.map((name) => ({ id: crypto.randomUUID(), name, value: targets.find((item) => item.name === name)?.value || '' }));
          setIngredients((current) => current.map((ingredient) => ({ ...ingredient, nutrients: Object.fromEntries(nextTargets.map((target) => [target.id, ingredient.nutrients[targets.find((item) => item.name === target.name)?.id || ''] || ''])) })));
          setTargets(nextTargets);
        }
      }}><MenuItem value="v4">Dynamic nutrients (V4)</MenuItem><MenuItem value="v3">Ten standard nutrients (V3)</MenuItem><MenuItem value="v2">Four standard nutrients + diagnostics (V2)</MenuItem><MenuItem value="v1">Four standard nutrients (V1)</MenuItem></TextField>
      <Paper variant="outlined" sx={{ p: { xs: 2, md: 3 }, borderRadius: 3 }}>
        <Stack spacing={2}>
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 700 }}>1. Nutrient targets</Typography>
            <Typography variant="body2" color="text.secondary">Use the same nutrient names and units across all ingredients.</Typography>
          </Box>
          {requirements.error && <Alert severity="warning">{requirements.error}<Button onClick={requirements.refresh}>Retry targets</Button></Alert>}
          <TextField select label="Use saved nutrient targets" value="" disabled={!requirements.data?.nutrient_requirements?.length} onChange={(event) => {
            const saved = requirements.data?.nutrient_requirements?.find((item) => item.id === Number(event.target.value));
            if (!saved) return;
            const values = saved.composition;
            const keys = mode === 'v4' ? Object.keys(values) : mode === 'v3' ? tenNutrients : fourNutrients;
            if (keys.some((key) => values[key] === undefined)) { setError('These targets do not contain every nutrient required by this calculation mode.'); return; }
            const next = keys.map((name) => ({ id: crypto.randomUUID(), name, value: String(values[name]) }));
            setIngredients((current) => current.map((ingredient) => ({ ...ingredient, nutrients: Object.fromEntries(next.map((target) => [target.id, ingredient.nutrients[targets.find((item) => item.name === target.name)?.id || ''] || ''])) })));
            setTargets(next); setResult(null); setError('');
          }}>{requirements.data?.nutrient_requirements?.map((item) => <MenuItem key={item.id} value={item.id}>{item.nutrient_requirement_name}</MenuItem>)}</TextField>
          {targets.map((target) => (
            <Stack key={target.id} direction={{ xs: 'column', sm: 'row' }} spacing={1.5} sx={{ alignItems: { sm: 'center' } }}>
              <TextField label="Nutrient name" disabled={mode !== 'v4'} value={target.name} onChange={(event) => updateTarget(target.id, { name: event.target.value })} fullWidth required />
              <TextField label="Target value" value={target.value} onChange={(event) => updateTarget(target.id, { value: event.target.value })} type="number" fullWidth required />
              <Button disabled={mode !== 'v4'} color="error" onClick={() => { setTargets((current) => current.filter((item) => item.id !== target.id)); setResult(null); }} aria-label={`Remove ${target.name || 'nutrient'}`} sx={{ minWidth: 44, alignSelf: { xs: 'flex-end', sm: 'center' } }}><DeleteOutlineRoundedIcon /></Button>
            </Stack>
          ))}
          <Box><Button disabled={mode !== 'v4'} startIcon={<AddRoundedIcon />} onClick={() => { setTargets((current) => [...current, { id: crypto.randomUUID(), name: '', value: '' }]); setResult(null); }}>Add nutrient</Button></Box>
        </Stack>
      </Paper>
      <Paper variant="outlined" sx={{ p: { xs: 2, md: 3 }, borderRadius: 3 }}>
        <Stack spacing={2.5}>
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 700 }}>2. Ingredients</Typography>
            <Typography variant="body2" color="text.secondary">Inclusion limits are percentages. Every ingredient needs a value for each target nutrient.</Typography>
          </Box>
          {savedError && <Alert severity="warning">{savedError}</Alert>}
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5}>
            <Button variant="outlined" startIcon={<AddRoundedIcon />} onClick={() => { setIngredients((current) => [...current, newIngredient()]); setResult(null); }}>Add custom ingredient</Button>
            <TextField select size="small" label="Add saved ingredient" value="" onChange={(event) => addSaved(Number(event.target.value))} sx={{ minWidth: 220 }} disabled={!savedIngredients.length}>
              {savedIngredients.map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}
            </TextField>
          </Stack>
          {ingredients.map((ingredient, index) => (
            <Card key={ingredient.id} variant="outlined" sx={{ bgcolor: '#fbfcfb' }}>
              <CardContent sx={{ p: 2.5 }}>
                <Stack direction="row" sx={{ alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                  <Typography sx={{ fontWeight: 700 }}>Ingredient {index + 1}</Typography>
                  <Button color="error" size="small" startIcon={<DeleteOutlineRoundedIcon />} onClick={() => { setIngredients((current) => current.filter((item) => item.id !== ingredient.id)); setResult(null); }}>Remove</Button>
                </Stack>
                <Box className="formulation-fields">
                  <TextField label="Name" value={ingredient.name} onChange={(event) => updateIngredient(ingredient.id, { name: event.target.value })} required />
                  <TextField label="Cost per kg" type="number" value={ingredient.cost} onChange={(event) => updateIngredient(ingredient.id, { cost: event.target.value })} required />
                  <TextField label="Minimum %" type="number" value={ingredient.min} onChange={(event) => updateIngredient(ingredient.id, { min: event.target.value })} required />
                  <TextField label="Maximum %" type="number" value={ingredient.max} onChange={(event) => updateIngredient(ingredient.id, { max: event.target.value })} required />
                </Box>
                <Divider sx={{ my: 2 }} />
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>Nutrient composition</Typography>
                <Box className="formulation-fields">
                  {targets.map((target) => <TextField key={target.id} label={target.name ? label(target.name) : 'Unnamed nutrient'} type="number" value={ingredient.nutrients[target.id] ?? ''} onChange={(event) => updateIngredient(ingredient.id, { nutrients: { ...ingredient.nutrients, [target.id]: event.target.value } })} required />)}
                </Box>
              </CardContent>
            </Card>
          ))}
        </Stack>
      </Paper>
      <Box>
        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
        <Button variant="contained" size="large" onClick={() => void formulate()} disabled={busy}>
          {busy ? 'Calculating…' : 'Calculate formulation'}
        </Button>
      </Box>
      {result && (
        <Paper variant="outlined" sx={{ p: { xs: 2, md: 3 }, borderRadius: 3 }}>
          <Stack spacing={2.5}>
            <FormulationResult result={result} />
            {result.status === 'success' && <>
              <Divider />
              <Typography variant="h6" sx={{ fontWeight: 700 }}>Save this formulation</Typography>
              {seed && <TextField select label="Save behavior" value={saveMode} onChange={(event) => setSaveMode(event.target.value)}><MenuItem value="version">Create a new version</MenuItem><MenuItem value="edit">Replace this version in place</MenuItem></TextField>}
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5}>
                <TextField label="Formulation name" value={formulationName} onChange={(event) => setFormulationName(event.target.value)} required fullWidth />
                <TextField label="Description" value={formulationDescription} onChange={(event) => setFormulationDescription(event.target.value)} fullWidth />
              </Stack>
              <Box><Button variant="outlined" disabled={saving || !rawResult || !formulationName.trim()} onClick={() => void save()}>{saving ? 'Saving…' : 'Save formulation'}</Button></Box>
              {saveMessage && <Alert severity={saveMessage === 'Formulation saved.' ? 'success' : 'error'}>{saveMessage}</Alert>}
            </>}
          </Stack>
        </Paper>
      )}
    </Stack>
  );
}
