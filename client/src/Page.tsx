import type { ReactNode } from 'react';
import { Alert, Box, Button, LinearProgress, Stack, Typography } from '@mui/material';

export function PageTitle({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ justifyContent: 'space-between', alignItems: { sm: 'center' }, mb: 3 }}>
    <Box><Typography component="h1" variant="h4" sx={{ fontWeight: 750 }}>{title}</Typography><Typography color="text.secondary" sx={{ mt: 1 }}>{description}</Typography></Box>{action}
  </Stack>;
}
export function LoadState({ loading, error, retry }: { loading: boolean; error: string; retry: () => void }) {
  return <>{loading && <LinearProgress aria-label="Loading data" sx={{ my: 2 }} />}{error && <Alert severity="error" sx={{ my: 2 }} action={<Button onClick={retry}>Retry</Button>}>{error}</Alert>}</>;
}
