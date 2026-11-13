import { Box, Button, IconButton, Stack, TextField } from '@mui/material';
import DeleteOutlineRoundedIcon from '@mui/icons-material/DeleteOutlineRounded';
import { label } from './data';

export type NutrientRow = { id: string; name: string; value: string };
export const nutrientRows = (values: Record<string, number>): NutrientRow[] => Object.entries(values).map(([name, value]) => ({ id: crypto.randomUUID(), name, value: String(value) }));
export function composition(rows: NutrientRow[]): Record<string, number> {
  if (!rows.length) throw new Error('Add at least one nutrient.');
  const result: Record<string, number> = {};
  for (const row of rows) {
    if (!row.name.trim() || row.name !== row.name.trim() || row.name.startsWith('_') || ['name', 'cost_per_kg', 'min_percentage', 'max_percentage', 'model_dump', 'total_ingredient_percentage'].includes(row.name)) throw new Error('Use a valid, trimmed nutrient name.');
    if (Object.hasOwn(result, row.name)) throw new Error('Nutrient names must be unique.');
    const value = Number(row.value);
    if (!row.value.trim() || !Number.isFinite(value) || value < 0) throw new Error(`Enter a nonnegative value for ${label(row.name)}.`);
    result[row.name] = value;
  }
  return result;
}
export default function NutrientEditor({ rows, onChange, fixed = false }: { rows: NutrientRow[]; onChange: (rows: NutrientRow[]) => void; fixed?: boolean }) {
  return <Stack spacing={1.5}>{rows.map((row) => <Stack key={row.id} direction="row" spacing={1} sx={{ alignItems: 'center' }}>
    <TextField fullWidth label={fixed ? label(row.name) : 'Nutrient name'} value={row.name} disabled={fixed} onChange={(event) => onChange(rows.map((item) => item.id === row.id ? { ...item, name: event.target.value } : item))} />
    <TextField fullWidth label={fixed ? `${label(row.name)} value` : 'Value'} type="number" slotProps={{ htmlInput: { min: 0, step: 'any' } }} value={row.value} onChange={(event) => onChange(rows.map((item) => item.id === row.id ? { ...item, value: event.target.value } : item))} required />
    {!fixed && <IconButton aria-label={`Remove ${row.name || 'nutrient'}`} onClick={() => onChange(rows.filter((item) => item.id !== row.id))}><DeleteOutlineRoundedIcon /></IconButton>}
  </Stack>)}{!fixed && <Box><Button onClick={() => onChange([...rows, { id: crypto.randomUUID(), name: '', value: '' }])}>Add nutrient</Button></Box>}</Stack>;
}
