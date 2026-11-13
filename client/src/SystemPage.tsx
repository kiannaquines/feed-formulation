import { Chip, Paper, Stack, Typography } from '@mui/material';
import { useResource } from './data';
import { LoadState, PageTitle } from './Page';

type Health = { status: string; details: { database_status: string; database_latency_ms: number | null; uptime_seconds: number; otp_enabled: boolean; cpu_usage_percent: number; memory_usage_percent: number; hostname: string } };
export default function SystemPage() {
  const resource = useResource<Health>('/api/v1/health');
  const health = resource.data;
  return <><PageTitle title="System" description="Current service availability and database connectivity." /><LoadState {...resource} retry={resource.refresh} />{health && <Paper variant="outlined" sx={{ p: 3 }}><Stack spacing={2}><Stack direction="row" spacing={2}><Typography variant="h6">Service status</Typography><Chip size="small" label={health.status} color={health.status === 'healthy' ? 'success' : 'warning'} /></Stack>{Object.entries({ Database: health.details.database_status, 'Database latency': health.details.database_latency_ms === null ? 'Unavailable' : `${health.details.database_latency_ms} ms`, Uptime: `${Math.floor(health.details.uptime_seconds / 60)} minutes`, 'OTP authentication': health.details.otp_enabled ? 'Enabled' : 'Disabled', 'CPU usage': `${health.details.cpu_usage_percent}%`, 'Memory usage': `${health.details.memory_usage_percent}%`, Host: health.details.hostname }).map(([key, value]) => <Stack key={key} direction="row" spacing={2} sx={{ justifyContent: 'space-between' }}><Typography color="text.secondary">{key}</Typography><Typography sx={{ overflowWrap: 'anywhere', minWidth: 0 }}>{value}</Typography></Stack>)}</Stack></Paper>}</>;
}
