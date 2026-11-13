import { useState } from 'react';
import {
  Alert, Box, Button, Chip, Dialog, DialogActions, DialogContent, DialogTitle,
  MenuItem, Paper, Stack, Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow, TextField, Typography,
} from '@mui/material';
import { apiRequest, resultMessage } from './api';

export type License = {
  id: number;
  user_id: number;
  device_id: number | null;
  plan_code: 'starter' | 'premium' | 'ultra';
  license_type: 'trial' | 'paid';
  status: 'active' | 'revoked';
  expires_at: string;
  price_php: number;
  payment_reference: string | null;
};

type Action = 'activate' | 'renew' | 'revoke' | 'reassign';
type Props = { token: string; licenses: License[]; onChanged: () => Promise<void> };

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
}

export default function AdminLicenses({ token, licenses, onChanged }: Props) {
  const [userFilter, setUserFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [planFilter, setPlanFilter] = useState('');
  const [expiresBy, setExpiresBy] = useState('');
  const [action, setAction] = useState<Action | null>(null);
  const [selected, setSelected] = useState<License | null>(null);
  const [userId, setUserId] = useState('');
  const [deviceId, setDeviceId] = useState('');
  const [planCode, setPlanCode] = useState<License['plan_code']>('starter');
  const [paymentReference, setPaymentReference] = useState('');
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const shown = licenses.filter((license) => {
    if (userFilter && String(license.user_id) !== userFilter.trim()) return false;
    const expired = license.status === 'active' && new Date(license.expires_at) < new Date();
    if (statusFilter === 'active' && (license.status !== 'active' || expired)) return false;
    if (statusFilter === 'expired' && !expired) return false;
    if (statusFilter === 'revoked' && license.status !== 'revoked') return false;
    if (planFilter && license.plan_code !== planFilter) return false;
    if (expiresBy && new Date(license.expires_at) > new Date(`${expiresBy}T23:59:59`)) return false;
    return true;
  });

  function open(nextAction: Action, license: License | null = null) {
    setAction(nextAction);
    setSelected(license);
    setUserId(license ? String(license.user_id) : '');
    setDeviceId(license?.device_id ? String(license.device_id) : '');
    setPlanCode(license?.plan_code || 'starter');
    setPaymentReference('');
    setReason('');
    setError('');
    setNotice('');
  }

  async function submit() {
    if (!action) return;
    const userNumber = Number(userId);
    const deviceNumber = Number(deviceId);
    if (action === 'activate' && (!Number.isInteger(userNumber) || userNumber <= 0 || !Number.isInteger(deviceNumber) || deviceNumber <= 0)) {
      setError('Enter valid user and device IDs.');
      return;
    }
    if (action === 'reassign' && (!Number.isInteger(deviceNumber) || deviceNumber <= 0)) {
      setError('Enter a valid destination device ID.');
      return;
    }
    if ((action === 'activate' || action === 'renew') && !paymentReference.trim()) {
      setError('Enter the verified offline payment reference.');
      return;
    }
    if ((action === 'revoke' || action === 'reassign') && !reason.trim()) {
      setError('Enter a reason for this change.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      const path = action === 'activate'
        ? '/api/v1/admin/licenses/activate'
        : `/api/v1/admin/licenses/${selected?.id}/${action}`;
      const body = action === 'activate'
        ? { user_id: userNumber, device_id: deviceNumber, plan_code: planCode, payment_reference: paymentReference.trim() }
        : action === 'renew'
          ? { plan_code: planCode, payment_reference: paymentReference.trim() }
          : action === 'reassign'
            ? { device_id: deviceNumber, reason: reason.trim() }
            : { reason: reason.trim() };
      const response = await apiRequest('POST', path, token, body);
      if (!response.ok) { setError(resultMessage(response)); return; }
      await onChanged();
      setAction(null);
      setNotice(`License ${action === 'activate' ? 'activated' : action === 'renew' ? 'renewed' : action === 'revoke' ? 'revoked' : 'reassigned'}.`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not update the license.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <Stack spacing={2.5}>
      <Stack direction={{ xs: 'column', sm: 'row' }} sx={{ justifyContent: 'space-between', alignItems: { sm: 'center' } }} spacing={1.5}>
        <Box><Typography variant="h6" sx={{ fontWeight: 700 }}>Device licenses</Typography><Typography variant="body2" color="text.secondary">Review trial and paid licenses, then record verified offline payments.</Typography></Box>
        <Button variant="contained" onClick={() => open('activate')}>Activate paid license</Button>
      </Stack>
      {notice && <Alert severity="success" onClose={() => setNotice('')}>{notice}</Alert>}
      <Paper variant="outlined" sx={{ p: 2, borderRadius: 3 }}>
        <Box className="admin-filter-grid">
          <TextField label="User ID" size="small" value={userFilter} onChange={(event) => setUserFilter(event.target.value)} />
          <TextField select label="Status" size="small" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
            <MenuItem value="">All</MenuItem><MenuItem value="active">Active</MenuItem><MenuItem value="expired">Expired</MenuItem><MenuItem value="revoked">Revoked</MenuItem>
          </TextField>
          <TextField select label="Plan" size="small" value={planFilter} onChange={(event) => setPlanFilter(event.target.value)}>
            <MenuItem value="">All</MenuItem><MenuItem value="starter">Starter</MenuItem><MenuItem value="premium">Premium</MenuItem><MenuItem value="ultra">Ultra</MenuItem>
          </TextField>
          <TextField label="Expires by" type="date" size="small" value={expiresBy} onChange={(event) => setExpiresBy(event.target.value)} slotProps={{ inputLabel: { shrink: true } }} />
        </Box>
      </Paper>
      <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 3 }}>
        <Table size="small" sx={{ minWidth: 760 }}>
          <TableHead><TableRow><TableCell>License</TableCell><TableCell>User / device</TableCell><TableCell>Plan</TableCell><TableCell>Status</TableCell><TableCell>Expires</TableCell><TableCell>Price</TableCell><TableCell align="right">Actions</TableCell></TableRow></TableHead>
          <TableBody>
            {shown.map((license) => {
              const expired = license.status === 'active' && new Date(license.expires_at) < new Date();
              return <TableRow key={license.id} hover>
                <TableCell>#{license.id}<Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>{license.license_type}</Typography></TableCell>
                <TableCell>#{license.user_id} / {license.device_id ? `#${license.device_id}` : '—'}</TableCell>
                <TableCell sx={{ textTransform: 'capitalize' }}>{license.plan_code}</TableCell>
                <TableCell><Chip size="small" label={expired ? 'Expired' : license.status} color={license.status === 'revoked' ? 'error' : expired ? 'warning' : 'success'} variant="outlined" /></TableCell>
                <TableCell>{formatDate(license.expires_at)}</TableCell>
                <TableCell>₱{license.price_php.toLocaleString()}</TableCell>
                <TableCell align="right">
                  {license.license_type === 'trial' ? <Button size="small" onClick={() => open('activate', license)}>Activate</Button> : <Stack direction="row" spacing={0.5} sx={{ justifyContent: 'flex-end' }}>
                    {license.status !== 'revoked' && <><Button size="small" onClick={() => open('renew', license)}>Renew</Button><Button size="small" onClick={() => open('reassign', license)}>Reassign</Button><Button size="small" color="error" onClick={() => open('revoke', license)}>Revoke</Button></>}
                  </Stack>}
                </TableCell>
              </TableRow>;
            })}
            {shown.length === 0 && <TableRow><TableCell colSpan={7}><Typography color="text.secondary" sx={{ py: 3, textAlign: 'center' }}>No licenses match these filters.</Typography></TableCell></TableRow>}
          </TableBody>
        </Table>
      </TableContainer>
      <Dialog open={!!action} onClose={busy ? undefined : () => setAction(null)} fullWidth maxWidth="sm">
        <DialogTitle sx={{ textTransform: 'capitalize' }}>{action} {action === 'activate' ? 'paid license' : `license #${selected?.id}`}</DialogTitle>
        <Box component="form" onSubmit={(event) => { event.preventDefault(); void submit(); }}>
          <DialogContent dividers><Stack spacing={2}>
            {error && <Alert severity="error">{error}</Alert>}
            {action === 'activate' && <>
              <TextField label="User ID" type="number" value={userId} onChange={(event) => setUserId(event.target.value)} required />
              <TextField label="Device ID" type="number" value={deviceId} onChange={(event) => setDeviceId(event.target.value)} required helperText="The device must belong to this user." />
            </>}
            {action === 'reassign' && <TextField label="Destination device ID" type="number" value={deviceId} onChange={(event) => setDeviceId(event.target.value)} required helperText="The destination must belong to the same user." />}
            {(action === 'activate' || action === 'renew') && <>
              <TextField select label="Plan" value={planCode} onChange={(event) => setPlanCode(event.target.value as License['plan_code'])}>
                <MenuItem value="starter">Starter</MenuItem><MenuItem value="premium">Premium</MenuItem><MenuItem value="ultra">Ultra</MenuItem>
              </TextField>
              <TextField label="Verified payment reference" value={paymentReference} onChange={(event) => setPaymentReference(event.target.value)} required />
            </>}
            {(action === 'revoke' || action === 'reassign') && <TextField label="Reason" value={reason} onChange={(event) => setReason(event.target.value)} required multiline minRows={2} />}
            {action === 'revoke' && <Alert severity="warning">Revoking a paid license removes access for that device.</Alert>}
          </Stack></DialogContent>
          <DialogActions><Button onClick={() => setAction(null)} disabled={busy}>Cancel</Button><Button type="submit" variant="contained" color={action === 'revoke' ? 'error' : 'primary'} disabled={busy}>{busy ? 'Saving…' : 'Confirm'}</Button></DialogActions>
        </Box>
      </Dialog>
    </Stack>
  );
}
