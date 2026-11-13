import { useEffect, useState } from 'react';
import { Alert, AppBar, Box, Button, Chip, CircularProgress, CssBaseline, Divider, Drawer, IconButton, List, ListItemButton, ListItemIcon, ListItemText, Stack, ThemeProvider, Toolbar, Typography, createTheme } from '@mui/material';
import DashboardOutlinedIcon from '@mui/icons-material/DashboardOutlined';
import ScienceOutlinedIcon from '@mui/icons-material/ScienceOutlined';
import Inventory2OutlinedIcon from '@mui/icons-material/Inventory2Outlined';
import TuneOutlinedIcon from '@mui/icons-material/TuneOutlined';
import BadgeOutlinedIcon from '@mui/icons-material/BadgeOutlined';
import PaymentsOutlinedIcon from '@mui/icons-material/PaymentsOutlined';
import PersonOutlineIcon from '@mui/icons-material/PersonOutlined';
import MonitorHeartOutlinedIcon from '@mui/icons-material/MonitorHeartOutlined';
import MenuRoundedIcon from '@mui/icons-material/MenuRounded';
import LogoutRoundedIcon from '@mui/icons-material/LogoutRounded';
import AuthDialog from './AuthDialog';
import FormulationBuilder, { type BuilderSeed } from './FormulationBuilder';
import FormulationsPage from './FormulationsPage';
import LibraryPage from './LibraryPage';
import AccountPage from './AccountPage';
import SystemPage from './SystemPage';
import Dashboard from './Dashboard';
import Administration from './Administration';
import { apiRequest } from './api';

const width = 244;
const theme = createTheme({
  palette: { primary: { main: '#17635a', dark: '#10463f', light: '#e2f0ec' }, background: { default: '#f6f8f7', paper: '#ffffff' }, text: { primary: '#192925', secondary: '#53655e' } },
  shape: { borderRadius: 10 },
  typography: { fontFamily: 'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif', h4: { fontSize: '1.85rem', letterSpacing: '-0.025em' }, h6: { fontWeight: 700 } },
  components: {
    MuiButton: { styleOverrides: { root: { textTransform: 'none', fontWeight: 650 } } },
    MuiTableCell: { styleOverrides: { head: { background: '#f4f7f5', color: '#53655e', fontWeight: 650 }, root: { borderColor: '#e2e9e5' } } },
    MuiPaper: { defaultProps: { elevation: 0 } },
    MuiListItemButton: { styleOverrides: { root: { borderRadius: 7, margin: '3px 12px', '&.Mui-selected': { background: '#e2f0ec', color: '#10463f' } } } },
  },
});
const pages = [
  { name: 'Dashboard', icon: <DashboardOutlinedIcon /> },
  { name: 'Formulations', icon: <ScienceOutlinedIcon /> },
  { name: 'Ingredients', icon: <Inventory2OutlinedIcon /> },
  { name: 'Nutrient requirements', icon: <TuneOutlinedIcon /> },
  { name: 'Licenses', icon: <BadgeOutlinedIcon />, admin: true },
  { name: 'Pricing', icon: <PaymentsOutlinedIcon /> },
  { name: 'My account', icon: <PersonOutlineIcon /> },
  { name: 'System', icon: <MonitorHeartOutlinedIcon />, admin: true },
];
function currentPage() {
  const value = decodeURIComponent(location.hash.slice(1));
  return [...pages.map((page) => page.name), 'Create formulation'].includes(value) ? value : 'Dashboard';
}
function AppContent() {
  const [token, setToken] = useState(() => sessionStorage.getItem('feedprime_token') || '');
  const [username, setUsername] = useState(() => sessionStorage.getItem('feedprime_username') || '');
  const [page, setPage] = useState(currentPage);
  const [mobile, setMobile] = useState(false);
  const [auth, setAuth] = useState(false);
  const [role, setRole] = useState<'loading' | 'admin' | 'member' | 'error'>('loading');
  const [roleRevision, setRoleRevision] = useState(0);
  const [seed, setSeed] = useState<BuilderSeed | null>(null);
  const [expired, setExpired] = useState(false);
  useEffect(() => {
    const listener = () => setPage(currentPage());
    window.addEventListener('hashchange', listener);
    return () => window.removeEventListener('hashchange', listener);
  }, []);
  useEffect(() => {
    if (!token) return;
    let active = true;
    setRole('loading');
    void apiRequest('GET', '/api/v1/admin/pricing/plans', token).then((result) => {
      if (!active) return;
      if (result.status === 401) { sessionStorage.removeItem('feedprime_token'); setToken(''); setExpired(true); }
      else setRole(result.ok ? 'admin' : result.status === 403 ? 'member' : 'error');
    }).catch(() => { if (active) setRole('error'); });
    return () => { active = false; };
  }, [token, roleRevision]);
  function navigate(next: string) { if (next !== 'Create formulation') setSeed(null); location.hash = encodeURIComponent(next); setPage(next); setMobile(false); }
  function signOut() { sessionStorage.removeItem('feedprime_token'); sessionStorage.removeItem('feedprime_username'); setToken(''); setUsername(''); navigate('Dashboard'); }
  useEffect(() => {
    const expire = () => { sessionStorage.removeItem('feedprime_token'); setToken(''); setExpired(true); };
    window.addEventListener('feedprime-session-expired', expire);
    return () => window.removeEventListener('feedprime-session-expired', expire);
  }, []);
  const isAdmin = role === 'admin';
  const navigation = <Stack sx={{ height: '100%', width }}>
    <Box sx={{ p: 3 }}><Typography variant="h5" color="primary.dark" sx={{ fontWeight: 800 }}>FeedPrime</Typography><Typography variant="body2" color="text.secondary">Management portal</Typography></Box><Divider />
    <List sx={{ flex: 1, pt: 2 }}>{pages.filter((item) => !item.admin || isAdmin).map((item) => <ListItemButton key={item.name} selected={page === item.name || (item.name === 'Formulations' && page === 'Create formulation')} onClick={() => navigate(item.name)}><ListItemIcon sx={{ minWidth: 36, color: 'inherit' }}>{item.icon}</ListItemIcon><ListItemText primary={item.name} slotProps={{ primary: { sx: { fontSize: 14, fontWeight: 550 } } }} /></ListItemButton>)}</List>
    <Box sx={{ p: 3 }}><Typography variant="body2" sx={{ fontWeight: 650 }}>{username}</Typography><Typography variant="caption" color="text.secondary">{isAdmin ? 'Administrator' : 'Member workspace'}</Typography></Box>
  </Stack>;
  if (!token) return <><CssBaseline /><Box className="access-page"><Box sx={{ maxWidth: 440 }}><Typography variant="h5" color="primary.dark" sx={{ fontWeight: 800, mb: 6 }}>FeedPrime</Typography><Typography component="h1" variant="h3" sx={{ fontSize: '2.5rem', fontWeight: 750, letterSpacing: '-0.03em' }}>Your feed operations, in one workspace.</Typography><Typography color="text.secondary" sx={{ mt: 2, mb: 4 }}>Build least-cost formulations, manage ingredient data, and keep device access and pricing under control.</Typography>{expired && <Alert severity="warning" sx={{ mb: 2 }}>Your session expired. Sign in again to continue.</Alert>}<Button size="large" variant="contained" onClick={() => setAuth(true)}>Sign in to your workspace</Button></Box></Box><AuthDialog open={auth} onClose={() => setAuth(false)} onAuthenticated={(value, user) => { sessionStorage.setItem('feedprime_token', value); sessionStorage.setItem('feedprime_username', user); setToken(value); setUsername(user); setRole('loading'); setExpired(false); }} /></>;
  return <Box sx={{ display: 'flex', minHeight: '100vh' }}><CssBaseline />
    <AppBar position="fixed" color="inherit" elevation={0} sx={{ borderBottom: '1px solid #e2e9e5', width: { md: `calc(100% - ${width}px)` }, ml: { md: `${width}px` } }}><Toolbar sx={{ gap: 2 }}><IconButton aria-label="Open navigation" onClick={() => setMobile(true)} sx={{ display: { md: 'none' } }}><MenuRoundedIcon /></IconButton><Typography sx={{ fontWeight: 650, flex: 1 }}>{page}</Typography><Chip size="small" variant="outlined" label={isAdmin ? 'Admin' : 'Workspace'} /><IconButton aria-label="Sign out" onClick={signOut}><LogoutRoundedIcon /></IconButton></Toolbar></AppBar>
    <Drawer variant="permanent" open sx={{ display: { xs: 'none', md: 'block' }, width, flexShrink: 0, '& .MuiDrawer-paper': { width, borderColor: '#e2e9e5' } }}>{navigation}</Drawer><Drawer open={mobile} onClose={() => setMobile(false)} sx={{ display: { md: 'none' } }}>{navigation}</Drawer>
    <Box component="main" sx={{ flexGrow: 1, minWidth: 0, pt: 12, pb: 6, px: { xs: 2, sm: 4, lg: 5 } }}><Box sx={{ maxWidth: 1280, mx: 'auto' }}>
      {role === 'loading' ? <Stack spacing={2} sx={{ alignItems: 'center', py: 8 }}><CircularProgress /><Typography>Opening your workspace…</Typography></Stack> : role === 'error' ? <Alert severity="error" action={<Button onClick={() => setRoleRevision((value) => value + 1)}>Retry</Button>}>Could not verify your account access. Check the connection and retry.</Alert> : <>
        {page === 'Dashboard' && <Dashboard token={token} isAdmin={isAdmin} navigate={navigate} />}
        {page === 'Formulations' && <FormulationsPage token={token} onCreate={() => { setSeed(null); navigate('Create formulation'); }} onRevise={(value) => { setSeed(value); navigate('Create formulation'); }} />}
        {page === 'Create formulation' && <FormulationBuilder key={seed?.id || 'new'} seed={seed} token={token} onAuthRequired={() => { signOut(); setAuth(true); }} />}
        {page === 'Ingredients' && <LibraryPage key="ingredients" kind="ingredients" token={token} />}
        {page === 'Nutrient requirements' && <LibraryPage key="requirements" kind="requirements" token={token} />}
        {page === 'My account' && <AccountPage token={token} />}
        {(page === 'Licenses' || page === 'Pricing') && (page === 'Pricing' || isAdmin ? <Administration key={page} page={page} token={token} isAdmin={isAdmin} /> : <Alert severity="warning">Administrator access is required.</Alert>)}
        {page === 'System' && (isAdmin ? <SystemPage /> : <Alert severity="warning">Administrator access is required.</Alert>)}
      </>}
    </Box></Box>
  </Box>;
}
export default function App() { return <ThemeProvider theme={theme}><AppContent /></ThemeProvider>; }
