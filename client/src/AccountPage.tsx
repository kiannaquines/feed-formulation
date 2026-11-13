import { useState } from 'react';
import { Alert, Box, Button, Chip, Dialog, DialogActions, DialogContent, DialogTitle, Divider, MenuItem, Paper, Stack, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TextField, Typography } from '@mui/material';
import { date, request, useResource } from './data';
import { LoadState, PageTitle } from './Page';
import type { License } from './AdminLicenses';

type Device = { id: number; name: string; device_type: string; is_active: boolean; last_seen_at: string };
export type LicenseStatus = { status: string; device: Device; license: License | null; ingredients: { used: number; limit: number | null }; requirements: { used: number; limit: number | null } };
type Credit = { id: number; bonus_days: number; claimed_at: string | null; claimed_license_id: number | null };
type Referrals = { referral_code: string; pending_referrals: number; qualified_referrals: number; credits: Credit[] };
export default function AccountPage({ token }: { token: string }) {
  const status = useResource<LicenseStatus>('/api/v1/licensing/status', token);
  const devices = useResource<Device[]>('/api/v1/licensing/devices', token);
  const referrals = useResource<Referrals>('/api/v1/referrals/me', token);
  const [claim, setClaim] = useState<Credit | null>(null);
  const [licenseId, setLicenseId] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const current = status.data;
  async function submit() {
    if (!claim) return;
    if (!Number.isInteger(Number(licenseId)) || Number(licenseId) <= 0) { setError('Enter a valid paid license ID.'); return; }
    setBusy(true); setError('');
    try {
      await request('POST', `/api/v1/referrals/credits/${claim.id}/claim`, token, { license_id: Number(licenseId) });
      setClaim(null); setNotice('Referral credit claimed. Your license expiry has been extended.'); status.refresh(); referrals.refresh();
    } catch (cause) { setError((cause as Error).message); } finally { setBusy(false); }
  }
  return <>
    <PageTitle title="My account" description="Your device access, saved-data allowances, and referral rewards." />
    {notice && <Alert severity="success" sx={{ mb: 2 }}>{notice}</Alert>}
    <Stack spacing={3}>
      <Paper variant="outlined" sx={{ p: 3 }}><Typography variant="h6">License & usage</Typography><LoadState {...status} retry={status.refresh} />{current && <Stack spacing={2} sx={{ mt: 2 }}>
        <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}><Chip label={current.status} color={current.status === 'active' ? 'success' : 'warning'} /><Typography>{current.license ? `${current.license.plan_code} · ${current.license.license_type} · License #${current.license.id}` : 'No license assigned'}</Typography></Stack>
        <Typography>Current device: {current.device.name} (#{current.device.id})</Typography><Typography>Expires: {date(current.license?.expires_at)}</Typography>
        {current.status !== 'active' && <Alert severity="warning">Contact your administrator to activate or renew access. Your saved data is retained.</Alert>}
        <Divider />{(['ingredients', 'requirements'] as const).map((key) => <Typography key={key}>{key === 'ingredients' ? 'Saved ingredients' : 'Saved requirements'}: <strong>{current[key].used} / {current[key].limit === null ? 'Unlimited' : current[key].limit}</strong></Typography>)}
      </Stack>}</Paper>
      <Box><Typography variant="h6" sx={{ mb: 1.5 }}>Registered devices</Typography><LoadState {...devices} retry={devices.refresh} /><TableContainer component={Paper} variant="outlined"><Table sx={{ minWidth: 540 }}><TableHead><TableRow><TableCell>Device</TableCell><TableCell>Type</TableCell><TableCell>Status</TableCell><TableCell>Last seen</TableCell></TableRow></TableHead><TableBody>{devices.data?.map((device) => <TableRow key={device.id}><TableCell>{device.name} · #{device.id}</TableCell><TableCell>{device.device_type}</TableCell><TableCell>{device.is_active ? 'Active' : 'Inactive'}{device.id === current?.device.id ? ' · Current' : ''}</TableCell><TableCell>{date(device.last_seen_at)}</TableCell></TableRow>)}{devices.data?.length === 0 && <TableRow><TableCell colSpan={4}>No registered devices.</TableCell></TableRow>}</TableBody></Table></TableContainer></Box>
      <Paper variant="outlined" sx={{ p: 3 }}><Typography variant="h6">Referrals</Typography><LoadState {...referrals} retry={referrals.refresh} />{referrals.data && <Stack spacing={2} sx={{ mt: 2 }}><Typography>Your referral code: <strong>{referrals.data.referral_code}</strong></Typography><Typography>{referrals.data.pending_referrals} pending · {referrals.data.qualified_referrals} qualified</Typography><Divider />{referrals.data.credits.map((credit) => <Stack key={credit.id} direction="row" spacing={2} sx={{ alignItems: 'center', justifyContent: 'space-between' }}><Box><Typography>{credit.bonus_days} bonus days</Typography><Typography variant="body2" color="text.secondary">{credit.claimed_at ? `Claimed ${date(credit.claimed_at)} · License #${credit.claimed_license_id}` : 'Available for an active paid license'}</Typography></Box><Button disabled={!!credit.claimed_at} onClick={() => { setClaim(credit); setError(''); setLicenseId(current?.status === 'active' && current.license?.license_type === 'paid' ? String(current.license.id) : ''); }}>{credit.claimed_at ? 'Claimed' : 'Claim credit'}</Button></Stack>)}{!referrals.data.credits.length && <Typography color="text.secondary">No referral credits earned yet.</Typography>}</Stack>}</Paper>
    </Stack>
    <Dialog open={!!claim} fullWidth maxWidth="sm" onClose={busy ? undefined : () => setClaim(null)}><DialogTitle>Claim {claim?.bonus_days} bonus days</DialogTitle><Box component="form" onSubmit={(event) => { event.preventDefault(); void submit(); }}><DialogContent dividers><Stack spacing={2}>{error && <Alert severity="error">{error}</Alert>}<Typography>Apply this credit to an active paid license you own.</Typography>{current?.status === 'active' && current.license?.license_type === 'paid' && <TextField select label="Current device license" value={licenseId === String(current.license.id) ? licenseId : ''} onChange={(event) => setLicenseId(event.target.value)}><MenuItem value="">Choose another license below</MenuItem><MenuItem value={String(current.license.id)}>#{current.license.id} · {current.license.plan_code}</MenuItem></TextField>}<TextField label="Paid license ID" type="number" value={licenseId} onChange={(event) => setLicenseId(event.target.value)} required helperText="For another device, enter its license ID. Ownership and eligibility are checked before claiming." /></Stack></DialogContent><DialogActions><Button disabled={busy} onClick={() => setClaim(null)}>Cancel</Button><Button type="submit" disabled={busy} variant="contained">{busy ? 'Claiming…' : 'Claim credit'}</Button></DialogActions></Box></Dialog>
  </>;
}
