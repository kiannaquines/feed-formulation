import { Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow } from '@mui/material';
import AdminLicenses, { type License } from './AdminLicenses';
import AdminPricing, { type PricingVersion } from './AdminPricing';
import { money, useResource } from './data';
import { LoadState, PageTitle } from './Page';

export default function Administration({ page, token, isAdmin }: { page: 'Licenses' | 'Pricing'; token: string; isAdmin: boolean }) {
  const licenses = page === 'Licenses';
  const resource = useResource<License[] | PricingVersion[]>(licenses ? '/api/v1/admin/licenses' : isAdmin ? '/api/v1/admin/pricing/plans' : '/api/v1/pricing/plans', token);
  return <><PageTitle title={page} description={licenses ? 'Manage device access and verified offline payments across the platform.' : 'Review monthly plans, storage allowances, and pricing versions.'} /><LoadState {...resource} retry={resource.refresh} />{resource.data && (licenses ? <AdminLicenses token={token} licenses={resource.data as License[]} onChanged={async () => resource.refresh()} /> : isAdmin ? <AdminPricing token={token} plans={resource.data as PricingVersion[]} onChanged={async () => resource.refresh()} /> : <TableContainer component={Paper} variant="outlined"><Table><TableHead><TableRow><TableCell>Plan</TableCell><TableCell>Monthly price</TableCell><TableCell>Ingredients</TableCell><TableCell>Requirements</TableCell></TableRow></TableHead><TableBody>{(resource.data as PricingVersion[]).map((plan) => <TableRow key={plan.code}><TableCell>{plan.name}</TableCell><TableCell>{money(plan.monthly_price)}</TableCell><TableCell>{plan.ingredient_limit ?? 'Unlimited'}</TableCell><TableCell>{plan.requirement_limit ?? 'Unlimited'}</TableCell></TableRow>)}</TableBody></Table></TableContainer>)}</>;
}
