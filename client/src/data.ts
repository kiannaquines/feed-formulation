import { useCallback, useEffect, useState } from 'react';
import { apiRequest, resultMessage } from './api';

export async function request<T>(method: string, path: string, token?: string, body?: unknown): Promise<T> {
  const result = await apiRequest(method, path, token, body);
  if (!result.ok) throw new Error(resultMessage(result));
  return result.data as T;
}

export function useResource<T>(path: string, token?: string) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [revision, setRevision] = useState(0);
  const refresh = useCallback(() => setRevision((value) => value + 1), []);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    void request<T>('GET', path, token).then((value) => {
      if (active) setData(value);
    }).catch((cause: Error) => {
      if (active) setError(cause.message || 'Connection failed. Please retry.');
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [path, token, revision]);
  return { data, error, loading, refresh };
}

export const fourNutrients = ['protein_percent', 'energy_me', 'calcium_percent', 'phosphorus_percent'];
export const tenNutrients = ['protein_percent', 'fat_percent', 'fiber_percent', 'energy_me', 'calcium_percent', 'phosphorus_percent', 'available_phosphorus_percent', 'lysine_percent', 'methionine_percent', 'methionine_cystine_percent'];
export function label(value: string): string {
  const labels: Record<string, string> = { protein_percent: 'Protein (%)', fat_percent: 'Fat (%)', fiber_percent: 'Fiber (%)', energy_me: 'Energy (kcal/kg)', calcium_percent: 'Calcium (%)', phosphorus_percent: 'Total phosphorus (%)', available_phosphorus_percent: 'Available phosphorus (%)', lysine_percent: 'Lysine (%)', methionine_percent: 'Methionine (%)', methionine_cystine_percent: 'Methionine + cystine (%)', total_ingredient_percentage: 'Total mixture (%)' };
  return labels[value] || value.replaceAll('_', ' ');
}
export function date(value?: string | null): string {
  if (!value) return '—';
  return new Date(/(?:Z|[+-]\d{2}:\d{2})$/.test(value) ? value : `${value}Z`).toLocaleString();
}
export const money = (value: number) => new Intl.NumberFormat(undefined, { style: 'currency', currency: 'PHP' }).format(value);
export function accountId(token: string): number | null {
  try {
    const segment = token.split('.')[1].replaceAll('-', '+').replaceAll('_', '/');
    const data = JSON.parse(atob(segment));
    return typeof data.user_id === 'number' ? data.user_id : null;
  } catch { return null; }
}
