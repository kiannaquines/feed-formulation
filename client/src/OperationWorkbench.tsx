import { useState } from 'react';
import {
  Alert, Box, Button, Chip, CircularProgress, Divider, Grid, Paper, Stack,
  TextField, Typography,
} from '@mui/material';
import PlayArrowRoundedIcon from '@mui/icons-material/PlayArrowRounded';
import ContentCopyRoundedIcon from '@mui/icons-material/ContentCopyRounded';
import { apiRequest, resultMessage, type ApiResult } from './api';
import { bodyExample, type ApiOperation, type ApiSchema } from './openapi';

type Props = {
  operation: ApiOperation;
  schemas: Record<string, ApiSchema>;
  token: string;
  initialBody?: string;
  onAuthRequired: () => void;
  onSaveResult: (result: unknown) => void;
};

function formatResult(data: unknown): string {
  return typeof data === 'string' ? data : JSON.stringify(data, null, 2) ?? '';
}

export default function OperationWorkbench({
  operation, schemas, token, initialBody, onAuthRequired, onSaveResult,
}: Props) {
  const [parameters, setParameters] = useState<Record<string, string>>({});
  const [body, setBody] = useState(initialBody ?? bodyExample(operation, schemas));
  const [result, setResult] = useState<ApiResult | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function run() {
    if (operation.secured && !token) {
      onAuthRequired();
      return;
    }
    setError('');
    setResult(null);
    let path = operation.path;
    const query = new URLSearchParams();
    for (const parameter of operation.parameters) {
      const value = (parameters[parameter.name] || '').trim();
      if (parameter.required && !value) {
        setError(`${parameter.name} is required.`);
        return;
      }
      if (parameter.in === 'path') {
        path = path.replace(`{${parameter.name}}`, encodeURIComponent(value));
      } else if (parameter.in === 'query' && value) {
        query.set(parameter.name, value);
      }
    }
    if (query.size) path += `?${query.toString()}`;
    let payload: unknown;
    if (operation.requestSchema) {
      try {
        payload = JSON.parse(body);
      } catch {
        setError('Request body must be valid JSON.');
        return;
      }
    }
    setBusy(true);
    try {
      const response = await apiRequest(operation.method, path, token, payload);
      setResult(response);
      if (!response.ok) setError(resultMessage(response));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not reach the API.');
    } finally {
      setBusy(false);
    }
  }

  const isFormulation = operation.method === 'POST' && operation.path.endsWith('/feed/formulate');

  return (
    <Stack spacing={3}>
      <Box>
        <Stack direction="row" spacing={1} useFlexGap sx={{ alignItems: 'center', flexWrap: 'wrap', mb: 1.5 }}>
          <Chip label={operation.method} size="small" color={operation.method === 'GET' ? 'default' : 'primary'} />
          <Chip label={operation.tag} size="small" variant="outlined" />
          {operation.deprecated && <Chip label="Legacy" size="small" color="warning" variant="outlined" />}
          {operation.secured && <Chip label="Account required" size="small" variant="outlined" />}
        </Stack>
        <Typography variant="h4" sx={{ fontWeight: 700 }}>{operation.summary}</Typography>
        <Typography color="text.secondary" sx={{ mt: 0.5 }}>{operation.description}</Typography>
        <Typography className="endpoint-path" sx={{ mt: 1.5 }}>{operation.method} {operation.path}</Typography>
      </Box>

      <Paper variant="outlined" sx={{ p: { xs: 2, md: 3 }, borderRadius: 3 }}>
        <Stack spacing={2.5}>
          <Typography variant="h6" sx={{ fontWeight: 700 }}>Request</Typography>
          {operation.parameters.length > 0 && (
            <Grid container spacing={2}>
              {operation.parameters.map((parameter) => (
                <Grid size={{ xs: 12, sm: 6 }} key={`${parameter.in}-${parameter.name}`}>
                  <TextField
                    fullWidth
                    label={parameter.name}
                    value={parameters[parameter.name] || ''}
                    onChange={(event) => setParameters((current) => ({ ...current, [parameter.name]: event.target.value }))}
                    required={parameter.required}
                    helperText={parameter.description || `${parameter.in} parameter`}
                    type={parameter.schema?.type === 'integer' || parameter.schema?.type === 'number' ? 'number' : 'text'}
                  />
                </Grid>
              ))}
            </Grid>
          )}
          {operation.requestSchema && (
            <TextField
              label="JSON request body"
              value={body}
              onChange={(event) => setBody(event.target.value)}
              multiline
              minRows={Math.min(14, Math.max(7, body.split('\n').length))}
              maxRows={24}
              fullWidth
              className="json-editor"
              helperText="Edit the example to match your data before sending."
            />
          )}
          {!operation.requestSchema && operation.parameters.length === 0 && (
            <Typography color="text.secondary">This request has no inputs.</Typography>
          )}
          {error && <Alert severity="error">{error}</Alert>}
          <Box>
            <Button variant="contained" size="large" startIcon={busy ? <CircularProgress size={18} color="inherit" /> : <PlayArrowRoundedIcon />} disabled={busy} onClick={() => void run()}>
              {busy ? 'Sending…' : 'Send request'}
            </Button>
          </Box>
        </Stack>
      </Paper>

      {result && (
        <Paper variant="outlined" sx={{ borderRadius: 3, overflow: 'hidden' }}>
          <Stack direction="row" sx={{ justifyContent: 'space-between', alignItems: 'center', px: { xs: 2, md: 3 }, py: 1.5 }}>
            <Stack direction="row" spacing={1.5} sx={{ alignItems: 'center' }}>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>Response</Typography>
              <Chip size="small" label={`HTTP ${result.status}`} color={result.ok ? 'success' : 'error'} />
            </Stack>
            <Button size="small" startIcon={<ContentCopyRoundedIcon />} onClick={() => void navigator.clipboard.writeText(formatResult(result.data))}>Copy</Button>
          </Stack>
          <Divider />
          <Box component="pre" className="response-code">{formatResult(result.data)}</Box>
          {isFormulation && result.ok && Boolean(result.data) && typeof result.data === 'object' && (
            <Box sx={{ px: { xs: 2, md: 3 }, pb: 2 }}>
              <Button variant="outlined" onClick={() => onSaveResult(result.data)}>Save this formulation</Button>
            </Box>
          )}
        </Paper>
      )}
    </Stack>
  );
}
