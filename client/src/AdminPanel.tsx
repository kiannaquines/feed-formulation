import { useCallback, useEffect, useState } from 'react';
import {
  Alert, Box, Button, Card, CardContent, CircularProgress, Paper, Stack,
  Tab, Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Tabs, Typography,
} from '@mui/material';
import AdminLicenses, { type License } from './AdminLicenses';
import AdminPricing, { type PricingVersion } from './AdminPricing';
import { apiRequest, resultMessage } from './api';

type Props = { token: string };

export default function AdminPanel({ token }: Props) {
  const [tab, setTab] = useState(0);
  const [licenses, setLicenses] = useState<License[]>([]);
  const [plans, setPlans] = useState<PricingVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    const [licenseResponse, pricingResponse] = await Promise.all([
      apiRequest('GET', '/api/v1/admin/licenses', token),
      apiRequest('GET', '/api/v1/admin/pricing/plans', token),
    ]);
    if (!licenseResponse.ok) throw new Error(resultMessage(licenseResponse));
    if (!pricingResponse.ok) throw new Error(resultMessage(pricingResponse));
    if (!Array.isArray(licenseResponse.data) || !Array.isArray(pricingResponse.data)) {
      throw new Error('The admin API returned an unexpected response.');
    }
    setLicenses(licenseResponse.data as License[]);
    setPlans(pricingResponse.data as PricingVersion[]);
    setError('');
  }, [token]);

  useEffect(() => {
    let active = true;
    void load().catch((cause) => {
      if (active) setError(cause instanceof Error ? cause.message : 'Could not load admin data.');
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [load]);

  async function refresh() {
    try { await load(); }
    catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not refresh admin data.');
    }
  }

  const now = Date.now();
  const active = licenses.filter((license) => license.status === 'active' && new Date(license.expires_at).getTime() > now);
  const paid = active.filter((license) => license.license_type === 'paid');
  const trials = active.filter((license) => license.license_type === 'trial');
  const expiring = active.filter((license) => new Date(license.expires_at).getTime() <= now + 7 * 24 * 60 * 60 * 1000);
  const recent = [...active].sort((a, b) => new Date(a.expires_at).getTime() - new Date(b.expires_at).getTime()).slice(0, 5);

  return (
    <Stack spacing={3}>
      <Box><Typography variant="overline" color="primary">ADMINISTRATION</Typography><Typography variant="h4" sx={{ fontWeight: 750 }}>Admin panel</Typography><Typography color="text.secondary" sx={{ mt: 1 }}>Manage paid device licenses and published pricing.</Typography></Box>
      {error && <Alert severity="error" action={<Button onClick={() => void refresh()}>Retry</Button>}>{error}</Alert>}
      {loading ? <Stack sx={{ alignItems: 'center', py: 8 }}><CircularProgress /></Stack> : <>
        <Tabs value={tab} onChange={(_, value: number) => setTab(value)} variant="scrollable" scrollButtons="auto" sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tab label="Dashboard" /><Tab label="Licenses" /><Tab label="Pricing" />
        </Tabs>
        {tab === 0 && <Stack spacing={3}>
          <Box className="admin-metric-grid">
            {[
              { label: 'Active paid', value: paid.length },
              { label: 'Active trials', value: trials.length },
              { label: 'Expiring in 7 days', value: expiring.length },
              { label: 'Pricing plans', value: plans.length },
            ].map((item) => <Card key={item.label} variant="outlined"><CardContent sx={{ p: 2.5 }}><Typography variant="body2" color="text.secondary">{item.label}</Typography><Typography variant="h4" sx={{ mt: 0.5, fontWeight: 750 }}>{item.value}</Typography></CardContent></Card>)}
          </Box>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5}>
            <Button variant="contained" onClick={() => setTab(1)}>Manage licenses</Button>
            <Button variant="outlined" onClick={() => setTab(2)}>Manage pricing</Button>
          </Stack>
          <Box><Typography variant="h6" sx={{ fontWeight: 700, mb: 1.5 }}>Upcoming license expirations</Typography>
            <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 3 }}><Table size="small" sx={{ minWidth: 540 }}>
              <TableHead><TableRow><TableCell>License</TableCell><TableCell>User</TableCell><TableCell>Plan</TableCell><TableCell>Type</TableCell><TableCell>Expires</TableCell></TableRow></TableHead>
              <TableBody>{recent.map((license) => <TableRow key={license.id} hover><TableCell>#{license.id}</TableCell><TableCell>#{license.user_id}</TableCell><TableCell sx={{ textTransform: 'capitalize' }}>{license.plan_code}</TableCell><TableCell sx={{ textTransform: 'capitalize' }}>{license.license_type}</TableCell><TableCell>{new Date(license.expires_at).toLocaleDateString()}</TableCell></TableRow>)}
                {!recent.length && <TableRow><TableCell colSpan={5}>No licenses yet.</TableCell></TableRow>}
              </TableBody>
            </Table></TableContainer>
          </Box>
        </Stack>}
        {tab === 1 && <AdminLicenses token={token} licenses={licenses} onChanged={refresh} />}
        {tab === 2 && <AdminPricing token={token} plans={plans} onChanged={refresh} />}
      </>}
    </Stack>
  );
}
