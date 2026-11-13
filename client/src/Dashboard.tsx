import { Alert, Box, Button, Chip, Divider, Paper, Stack, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography } from '@mui/material';
import { date, money, useResource } from './data';
import { LoadState, PageTitle } from './Page';
import type { License } from './AdminLicenses';
import type { PricingVersion } from './AdminPricing';
import type { LicenseStatus } from './AccountPage';

function AdminOverview({ token, navigate }: { token: string; navigate: (page: string) => void }) {
  const licenses = useResource<License[]>('/api/v1/admin/licenses', token);
  const plans = useResource<PricingVersion[]>('/api/v1/admin/pricing/plans', token);
  const now = Date.now();
  const active = (licenses.data || []).filter((item) => item.status === 'active' && new Date(item.expires_at.endsWith('Z') ? item.expires_at : `${item.expires_at}Z`).getTime() > now);
  const expiring = active.filter((item) => new Date(item.expires_at.endsWith('Z') ? item.expires_at : `${item.expires_at}Z`).getTime() <= now + 7 * 86400000).sort((a, b) => a.expires_at.localeCompare(b.expires_at));
  return <Stack spacing={3}>
    <LoadState {...licenses} retry={licenses.refresh} />
    <Paper variant="outlined" className="dashboard-counts">{[{ name: 'Active paid licenses', value: active.filter((item) => item.license_type === 'paid').length }, { name: 'Active trials', value: active.filter((item) => item.license_type === 'trial').length }, { name: 'Expiring within 7 days', value: expiring.length }].map((item) => <Box key={item.name}><Typography color="text.secondary" variant="body2">{item.name}</Typography><Typography variant="h4" sx={{ mt: 1, fontWeight: 750 }}>{licenses.data ? item.value : '—'}</Typography></Box>)}</Paper>
    <Box><Stack direction="row" sx={{ justifyContent: 'space-between', mb: 2 }}><Typography variant="h6">Upcoming expirations</Typography><Button onClick={() => navigate('Licenses')}>Manage licenses</Button></Stack><TableContainer component={Paper} variant="outlined"><Table sx={{ minWidth: 560 }}><TableHead><TableRow><TableCell>License</TableCell><TableCell>User / device</TableCell><TableCell>Plan</TableCell><TableCell>Expires</TableCell></TableRow></TableHead><TableBody>{expiring.slice(0, 8).map((item) => <TableRow key={item.id}><TableCell>#{item.id} · {item.license_type}</TableCell><TableCell>#{item.user_id} / #{item.device_id}</TableCell><TableCell sx={{ textTransform: 'capitalize' }}>{item.plan_code}</TableCell><TableCell>{date(item.expires_at)}</TableCell></TableRow>)}{licenses.data && !expiring.length && <TableRow><TableCell colSpan={4} sx={{ py: 4 }}>No active licenses expire in the next seven days.</TableCell></TableRow>}</TableBody></Table></TableContainer></Box>
    <Box><Stack direction="row" sx={{ justifyContent: 'space-between', mb: 1 }}><Typography variant="h6">Current pricing</Typography><Button onClick={() => navigate('Pricing')}>Manage pricing</Button></Stack><LoadState {...plans} retry={plans.refresh} /><Paper variant="outlined"><Stack divider={<Divider />}>{plans.data?.map((plan) => <Stack key={plan.code} direction="row" spacing={2} sx={{ alignItems: 'center', justifyContent: 'space-between', p: 2.5 }}><Box><Typography sx={{ fontWeight: 650 }}>{plan.name}</Typography><Typography variant="body2" color="text.secondary">{plan.ingredient_limit ?? 'Unlimited'} ingredients · {plan.requirement_limit ?? 'Unlimited'} requirements</Typography></Box><Typography sx={{ fontWeight: 650 }}>{money(plan.monthly_price)} / month</Typography></Stack>)}</Stack></Paper></Box>
  </Stack>;
}
function MemberOverview({ token, navigate }: { token: string; navigate: (page: string) => void }) {
  const status = useResource<LicenseStatus>('/api/v1/licensing/status', token);
  return <Paper variant="outlined" sx={{ p: 3 }}><LoadState {...status} retry={status.refresh} />{status.data && <Stack spacing={2}><Stack direction="row" spacing={2} sx={{ alignItems: 'center' }}><Typography variant="h6">Workspace access</Typography><Chip label={status.data.status} color={status.data.status === 'active' ? 'success' : 'warning'} /></Stack><Typography>{status.data.device.name} · {status.data.license?.plan_code || 'No plan'}</Typography><Typography color="text.secondary">License expires {date(status.data.license?.expires_at)}</Typography>{status.data.status !== 'active' && <Alert severity="warning">Ask your administrator to renew access to formulation tools.</Alert>}<Box><Button onClick={() => navigate('My account')}>View license, devices & usage</Button></Box></Stack>}</Paper>;
}
export default function Dashboard({ token, isAdmin, navigate }: { token: string; isAdmin: boolean; navigate: (page: string) => void }) {
  return <><PageTitle title="Dashboard" description={isAdmin ? 'Monitor device access and manage daily feed operations.' : 'Your formulation workspace and account access at a glance.'} action={<Button variant="contained" onClick={() => navigate('Create formulation')}>Create formulation</Button>} />
    <Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: 'wrap', mb: 3 }}><Button variant="outlined" onClick={() => navigate('Ingredients')}>Manage ingredients</Button><Button variant="outlined" onClick={() => navigate('Nutrient requirements')}>Nutrient targets</Button><Button variant="outlined" onClick={() => navigate('Formulations')}>Saved formulations</Button></Stack>
    {isAdmin ? <AdminOverview token={token} navigate={navigate} /> : <MemberOverview token={token} navigate={navigate} />}
  </>;
}
