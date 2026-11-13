import { Alert, Box, Chip, Stack, Typography } from '@mui/material';
import { label, money } from './data';

export type Calculation = {
  status?: string; message?: string; detail?: string;
  summary?: { cost_per_kg?: number; total_ingredient_percentage?: number };
  ingredient_composition?: { name: string; percentage: number; cost_contribution: number }[];
  nutrient_achievement?: Record<string, { required: number; achieved: number }>;
  constraint_diagnostics?: Record<string, { required: number; achieved: number; difference: number; status: string }>;
  failed_constraints?: string[];
  error_details?: { possible_causes?: string[]; suggestions?: string[] };
};
export default function FormulationResult({ result }: { result: Calculation }) {
  return <Stack spacing={2.5}>
    <Stack direction="row" spacing={2} sx={{ alignItems: 'center' }}><Typography variant="h6">Calculation result</Typography><Chip size="small" label={result.status === 'success' ? 'Feasible' : result.status === 'failure' ? 'Infeasible' : 'Saved result'} color={result.status === 'success' ? 'success' : 'default'} /></Stack>
    {result.status === 'failure' && <Alert severity="warning">This candidate does not satisfy all constraints. Review the diagnostics before using it.</Alert>}
    {(result.message || result.detail) && <Typography>{result.message || result.detail}</Typography>}
    {result.summary && <Stack direction={{ xs: 'column', sm: 'row' }} spacing={4}><Box><Typography color="text.secondary">Cost per kg</Typography><Typography variant="h5">{result.summary.cost_per_kg === undefined ? '—' : money(result.summary.cost_per_kg)}</Typography></Box><Box><Typography color="text.secondary">Total mixture</Typography><Typography variant="h5">{result.summary.total_ingredient_percentage?.toFixed(2) ?? '—'}%</Typography></Box></Stack>}
    {!!result.ingredient_composition?.length && <Box className="result-table"><table><thead><tr><th>Ingredient</th><th>Inclusion</th><th>Cost contribution / kg</th></tr></thead><tbody>{result.ingredient_composition.map((item, index) => <tr key={index}><td>{item.name}</td><td>{item.percentage.toFixed(2)}%</td><td>{money(item.cost_contribution)}</td></tr>)}</tbody></table></Box>}
    {result.nutrient_achievement && <Box className="result-table"><table><thead><tr><th>Nutrient</th><th>Target</th><th>Achieved</th></tr></thead><tbody>{Object.entries(result.nutrient_achievement).map(([key, item]) => <tr key={key}><td>{label(key)}</td><td>{item.required}</td><td>{item.achieved.toFixed(4)}</td></tr>)}</tbody></table></Box>}
    {result.constraint_diagnostics && <Box className="result-table"><table><thead><tr><th>Constraint</th><th>Required</th><th>Achieved</th><th>Difference</th><th>Status</th></tr></thead><tbody>{Object.entries(result.constraint_diagnostics).map(([key, item]) => <tr key={key}><td>{label(key)}</td><td>{item.required}</td><td>{item.achieved.toFixed(4)}</td><td>{item.difference.toFixed(4)}</td><td>{item.status}</td></tr>)}</tbody></table></Box>}
    {!!result.failed_constraints?.length && <Alert severity="warning">Unmet constraints: {result.failed_constraints.map(label).join(', ')}</Alert>}
    {result.error_details?.possible_causes?.map((cause) => <Typography key={cause} variant="body2">{cause}</Typography>)}
    {result.error_details?.suggestions?.map((suggestion) => <Typography key={suggestion} variant="body2">{suggestion}</Typography>)}
  </Stack>;
}
