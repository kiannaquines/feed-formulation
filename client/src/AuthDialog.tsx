import { useState } from 'react';
import {
  Alert, Button, Dialog, DialogActions, DialogContent, DialogTitle,
  MenuItem, Stack, Tab, Tabs, TextField, Typography,
} from '@mui/material';
import { apiRequest, resultMessage } from './api';

type Props = {
  open: boolean;
  onClose: () => void;
  onAuthenticated: (token: string, username: string) => void;
};

type Challenge = { session_token: string; current_otp?: string; note?: string };

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? value as Record<string, unknown> : {};
}

export default function AuthDialog({ open, onClose, onAuthenticated }: Props) {
  const [tab, setTab] = useState(0);
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [deviceName, setDeviceName] = useState('My computer');
  const [deviceType, setDeviceType] = useState('laptop');
  const [installationId] = useState<string>(() => {
    const saved = localStorage.getItem('feedprime_installation_id') || crypto.randomUUID();
    localStorage.setItem('feedprime_installation_id', saved);
    return saved;
  });
  const [referralCode, setReferralCode] = useState('');
  const [challenge, setChallenge] = useState<Challenge | null>(null);
  const [otpCode, setOtpCode] = useState('');
  const [registrationResult, setRegistrationResult] = useState<unknown>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(path: string, body: unknown) {
    setBusy(true);
    setError('');
    try {
      const result = await apiRequest('POST', path, undefined, body);
      if (!result.ok) {
        setError(resultMessage(result));
        return;
      }
      const data = asRecord(result.data);
      if (path.endsWith('/register')) {
        setRegistrationResult(result.data);
        setTab(0);
        return;
      }
      if (typeof data.access_token === 'string') {
        const user = asRecord(data.user);
        onAuthenticated(data.access_token, String(user.username || username));
        setChallenge(null);
        setPassword('');
        onClose();
      } else if (typeof data.session_token === 'string') {
        setChallenge({
          session_token: data.session_token,
          current_otp: typeof data.current_otp === 'string' ? data.current_otp : undefined,
          note: typeof data.note === 'string' ? data.note : undefined,
        });
      } else {
        setError('The server returned an unexpected authentication response.');
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not reach the API.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onClose={busy ? undefined : onClose} fullWidth maxWidth="sm">
      <DialogTitle sx={{ fontWeight: 700 }}>Account access</DialogTitle>
      {!challenge && (
        <Tabs value={tab} onChange={(_, value: number) => { setTab(value); setError(''); }} sx={{ px: 3 }}>
          <Tab label="Sign in" />
          <Tab label="Create account" />
        </Tabs>
      )}
      <DialogContent dividers>
        <Stack component="form" spacing={2} onSubmit={(event) => {
          event.preventDefault();
          if (challenge) {
            void submit('/api/v1/auth/verify-otp', {
              session_token: challenge.session_token, otp_code: otpCode,
            });
          } else if (tab === 0) {
            void submit('/api/v1/auth/login', { username, password });
          } else {
            void submit('/api/v1/auth/register', {
              username, email, password, installation_id: installationId,
              device_name: deviceName, device_type: deviceType,
              ...(referralCode ? { referral_code: referralCode } : {}),
            });
          }
        }}>
          {error && <Alert severity="error">{error}</Alert>}
          {registrationResult !== null && !challenge && (
            <Alert severity="success" onClose={() => setRegistrationResult(null)}>
              Account created. You can sign in now.
            </Alert>
          )}
          {challenge ? (
            <>
              <Typography color="text.secondary">Enter the one-time code for this account.</Typography>
              {challenge.note && <Alert severity="info">{challenge.note}</Alert>}
              {challenge.current_otp && <Alert severity="info">Current code: <strong>{challenge.current_otp}</strong></Alert>}
              <TextField label="One-time code" value={otpCode} onChange={(event) => setOtpCode(event.target.value)} required autoFocus />
            </>
          ) : (
            <>
              <TextField label="Username or email" value={username} onChange={(event) => setUsername(event.target.value)} required autoFocus />
              {tab === 1 && <TextField label="Email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />}
              <TextField label="Password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />
              {tab === 1 && (
                <>
                  <TextField label="Device name" value={deviceName} onChange={(event) => setDeviceName(event.target.value)} required />
                  <TextField select label="Device type" value={deviceType} onChange={(event) => setDeviceType(event.target.value)}>
                    <MenuItem value="laptop">Laptop</MenuItem>
                    <MenuItem value="desktop">Desktop</MenuItem>
                    <MenuItem value="phone">Phone</MenuItem>
                  </TextField>
                  <TextField label="Referral code (optional)" value={referralCode} onChange={(event) => setReferralCode(event.target.value)} />
                </>
              )}
            </>
          )}
          <Button type="submit" variant="contained" size="large" disabled={busy}>
            {busy ? 'Working…' : challenge ? 'Verify code' : tab === 0 ? 'Sign in' : 'Create account'}
          </Button>
        </Stack>
      </DialogContent>
      <DialogActions><Button onClick={onClose} disabled={busy}>Close</Button></DialogActions>
    </Dialog>
  );
}
