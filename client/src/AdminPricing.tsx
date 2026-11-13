import { useEffect, useState } from 'react';
import {
  Alert, Box, Button, Card, CardContent, Chip, Dialog, DialogActions,
  DialogContent, DialogTitle, MenuItem, Paper, Stack, Table, TableBody,
  TableCell, TableContainer, TableHead, TableRow, TextField, Typography,
} from '@mui/material';
import { apiRequest, resultMessage } from './api';

export type PricingVersion = {
  id: number;
  code: 'starter' | 'premium' | 'ultra';
  name: string;
  monthly_price: number;
  ingredient_limit: number | null;
  requirement_limit: number | null;
  version_number: number;
  effective_at: string;
  created_by_user_id: number | null;
};

type LimitMode = 'keep' | 'unlimited' | 'set';
type Props = { token: string; plans: PricingVersion[]; onChanged: () => Promise<void> };

function quota(value: number | null): string {
  return value === null ? 'Unlimited' : value.toLocaleString();
}

export default function AdminPricing({ token, plans, onChanged }: Props) {
  const [selectedCode, setSelectedCode] = useState<PricingVersion['code']>('starter');
  const [history, setHistory] = useState<PricingVersion[]>([]);
  const [historyError, setHistoryError] = useState('');
  const [refreshNumber, setRefreshNumber] = useState(0);
  const [publishOpen, setPublishOpen] = useState(false);
  const [price, setPrice] = useState('');
  const [ingredientMode, setIngredientMode] = useState<LimitMode>('keep');
  const [ingredientLimit, setIngredientLimit] = useState('');
  const [requirementMode, setRequirementMode] = useState<LimitMode>('keep');
  const [requirementLimit, setRequirementLimit] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const selected = plans.find((plan) => plan.code === selectedCode);

  useEffect(() => {
    let active = true;
    setHistory([]);
    void apiRequest('GET', `/api/v1/admin/pricing/plans/${selectedCode}/versions`, token)
      .then((response) => {
        if (!active) return;
        if (response.ok && Array.isArray(response.data)) {
          setHistory(response.data as PricingVersion[]);
          setHistoryError('');
        } else {
          setHistoryError(resultMessage(response));
        }
      }).catch(() => { if (active) setHistoryError('Could not load pricing history.'); });
    return () => { active = false; };
  }, [token, selectedCode, refreshNumber]);

  function openPublish(plan: PricingVersion) {
    setSelectedCode(plan.code);
    setPrice(String(plan.monthly_price));
    setIngredientMode('keep');
    setRequirementMode('keep');
    setIngredientLimit('');
    setRequirementLimit('');
    setError('');
    setNotice('');
    setPublishOpen(true);
  }

  async function publish() {
    if (!selected) return;
    const monthlyPrice = Number(price);
    const ingredientNumber = Number(ingredientLimit);
    const requirementNumber = Number(requirementLimit);
    if (!Number.isInteger(monthlyPrice) || monthlyPrice <= 0) {
      setError('Monthly price must be a positive whole number.');
      return;
    }
    if (ingredientMode === 'set' && (!Number.isInteger(ingredientNumber) || ingredientNumber <= 0)) {
      setError('Ingredient limit must be a positive whole number.');
      return;
    }
    if (requirementMode === 'set' && (!Number.isInteger(requirementNumber) || requirementNumber <= 0)) {
      setError('Requirement limit must be a positive whole number.');
      return;
    }
    const payload: Record<string, number | null> = { monthly_price: monthlyPrice };
    if (ingredientMode === 'unlimited') payload.ingredient_limit = null;
    if (ingredientMode === 'set') payload.ingredient_limit = ingredientNumber;
    if (requirementMode === 'unlimited') payload.requirement_limit = null;
    if (requirementMode === 'set') payload.requirement_limit = requirementNumber;
    setBusy(true);
    setError('');
    try {
      const response = await apiRequest('POST', `/api/v1/admin/pricing/plans/${selected.code}/versions`, token, payload);
      if (!response.ok) { setError(resultMessage(response)); return; }
      await onChanged();
      setRefreshNumber((current) => current + 1);
      setPublishOpen(false);
      setNotice(`${selected.name} pricing version published.`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not publish pricing.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <Stack spacing={2.5}>
      <Box><Typography variant="h6" sx={{ fontWeight: 700 }}>Pricing plans</Typography><Typography variant="body2" color="text.secondary">New versions apply to future activations and renewals. Existing paid terms remain until renewal.</Typography></Box>
      {notice && <Alert severity="success" onClose={() => setNotice('')}>{notice}</Alert>}
      <Box className="admin-plan-grid">
        {plans.map((plan) => <Card key={plan.code} variant="outlined" sx={{ borderColor: selectedCode === plan.code ? 'primary.main' : undefined }}>
          <CardContent sx={{ p: 2.5 }}><Stack spacing={1.5}>
            <Stack direction="row" sx={{ justifyContent: 'space-between', alignItems: 'center' }}><Typography sx={{ fontWeight: 700 }}>{plan.name}</Typography><Chip label={`v${plan.version_number}`} size="small" /></Stack>
            <Typography variant="h5" sx={{ fontWeight: 750 }}>₱{plan.monthly_price.toLocaleString()}<Typography component="span" variant="body2" color="text.secondary"> / month</Typography></Typography>
            <Typography variant="body2">Ingredients: {quota(plan.ingredient_limit)}</Typography>
            <Typography variant="body2">Requirements: {quota(plan.requirement_limit)}</Typography>
            <Stack direction="row" spacing={1}><Button size="small" onClick={() => setSelectedCode(plan.code)}>History</Button><Button size="small" variant="outlined" onClick={() => openPublish(plan)}>Publish version</Button></Stack>
          </Stack></CardContent>
        </Card>)}
      </Box>
      <Box>
        <Typography variant="h6" sx={{ fontWeight: 700, mb: 1.5, textTransform: 'capitalize' }}>{selectedCode} history</Typography>
        {historyError && <Alert severity="error" sx={{ mb: 2 }}>{historyError}</Alert>}
        <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 3 }}><Table size="small" sx={{ minWidth: 660 }}>
          <TableHead><TableRow><TableCell>Version</TableCell><TableCell>Monthly price</TableCell><TableCell>Ingredients</TableCell><TableCell>Requirements</TableCell><TableCell>Effective</TableCell><TableCell>Published by</TableCell></TableRow></TableHead>
          <TableBody>{history.map((version) => <TableRow key={version.id} hover>
            <TableCell>v{version.version_number}</TableCell><TableCell>₱{version.monthly_price.toLocaleString()}</TableCell><TableCell>{quota(version.ingredient_limit)}</TableCell><TableCell>{quota(version.requirement_limit)}</TableCell><TableCell>{new Date(version.effective_at).toLocaleString()}</TableCell><TableCell>{version.created_by_user_id ? `User #${version.created_by_user_id}` : 'System'}</TableCell>
          </TableRow>)}
          {!history.length && !historyError && <TableRow><TableCell colSpan={6}><Typography color="text.secondary" sx={{ py: 2 }}>Loading history…</Typography></TableCell></TableRow>}
          </TableBody>
        </Table></TableContainer>
      </Box>
      <Dialog open={publishOpen} onClose={busy ? undefined : () => setPublishOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Publish {selected?.name} pricing</DialogTitle>
        <Box component="form" onSubmit={(event) => { event.preventDefault(); void publish(); }}>
          <DialogContent dividers><Stack spacing={2}>
            {error && <Alert severity="error">{error}</Alert>}
            <Alert severity="info">This creates a new immutable pricing version.</Alert>
            <TextField label="Monthly price (PHP)" type="number" value={price} onChange={(event) => setPrice(event.target.value)} required />
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5}>
              <TextField select label="Ingredient limit" value={ingredientMode} onChange={(event) => setIngredientMode(event.target.value as LimitMode)} fullWidth>
                <MenuItem value="keep">Keep current</MenuItem><MenuItem value="unlimited">Unlimited</MenuItem><MenuItem value="set">Set a limit</MenuItem>
              </TextField>
              {ingredientMode === 'set' && <TextField label="New limit" type="number" value={ingredientLimit} onChange={(event) => setIngredientLimit(event.target.value)} fullWidth required />}
            </Stack>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5}>
              <TextField select label="Requirement limit" value={requirementMode} onChange={(event) => setRequirementMode(event.target.value as LimitMode)} fullWidth>
                <MenuItem value="keep">Keep current</MenuItem><MenuItem value="unlimited">Unlimited</MenuItem><MenuItem value="set">Set a limit</MenuItem>
              </TextField>
              {requirementMode === 'set' && <TextField label="New limit" type="number" value={requirementLimit} onChange={(event) => setRequirementLimit(event.target.value)} fullWidth required />}
            </Stack>
          </Stack></DialogContent>
          <DialogActions><Button onClick={() => setPublishOpen(false)} disabled={busy}>Cancel</Button><Button type="submit" variant="contained" disabled={busy}>{busy ? 'Publishing…' : 'Publish version'}</Button></DialogActions>
        </Box>
      </Dialog>
    </Stack>
  );
}
