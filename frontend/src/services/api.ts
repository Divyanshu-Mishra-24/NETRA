export interface Asset {
  [key: string]: unknown;
  id: string;
  name: string;
  type: string;
  ip: string | null;
  os?: string | null;
  ports: number[];
  exposure: string | null;
  criticality: string | null;
  source?: string | null;
}

export interface AssetCreateInput {
  [key: string]: unknown;
  id: string;
  name: string;
  type: string;
  ip?: string | null;
  os?: string | null;
  ports: number[];
  exposure?: string | null;
  criticality?: string | null;
}

export interface ConnectionData {
  [key: string]: unknown;
  source: string;
  target: string;
  destination?: string | null;
  protocol?: string | null;
  port?: number | null;
  allowed?: boolean | null;
  evidence?: string | null;
}

export interface GraphNode {
  id: string;
  type?: string;
  position: { x: number; y: number };
  data: Asset;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type?: string;
  label?: string | null;
  data: ConnectionData;
}

export interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface GraphStats {
  asset_count: number;
  connection_count: number;
}

export interface CreateConnectionInput {
  target: string;
  protocol?: string | null;
  port?: number | null;
  allowed?: boolean | null;
  evidence?: string | null;
}

const RAW_API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim()
  || 'http://localhost:8080/netra/api';
export const API_BASE_URL = RAW_API_BASE_URL.replace(/\/$/, '');

export class ApiError extends Error {
  status: number;
  detail?: unknown;

  constructor(message: string, status: number, detail?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

async function parseErrorDetail(response: Response): Promise<unknown> {
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    try {
      return await response.json();
    } catch {
      return undefined;
    }
  }
  try {
    const text = await response.text();
    return text || undefined;
  } catch {
    return undefined;
  }
}

function errorMessage(detail: unknown, fallback: string): string {
  if (!detail) return fallback;
  if (typeof detail === 'string') return detail;
  if (typeof detail === 'object' && detail !== null && 'detail' in detail) {
    const value = (detail as { detail?: unknown }).detail;
    if (typeof value === 'string') return value;
    if (Array.isArray(value)) {
      return value
        .map((item) => {
          if (typeof item === 'string') return item;
          if (item && typeof item === 'object' && 'msg' in item) return String((item as { msg?: unknown }).msg);
          return JSON.stringify(item);
        })
        .join('; ');
    }
  }
  return fallback;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      headers: {
        'Content-Type': 'application/json',
        ...(init?.headers || {}),
      },
      ...init,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Network request failed';
    throw new ApiError(`Unable to reach NETRA backend: ${message}`, 0);
  }

  if (!response.ok) {
    const detail = await parseErrorDetail(response);
    throw new ApiError(errorMessage(detail, `Request failed with status ${response.status}`), response.status, detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export function getHealth() {
  return request<{ status: string; service: string; neo4j: string }>('/health');
}

export function getGraph() {
  return request<GraphResponse>('/graph');
}

export function getGraphStats() {
  return request<GraphStats>('/graph/stats');
}

export function getAssets() {
  return request<Asset[]>('/assets');
}

export function getAsset(id: string) {
  return request<Asset>(`/assets/${encodeURIComponent(id)}`);
}

export function createAsset(payload: AssetCreateInput) {
  return request<Asset>('/assets', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function createConnection(sourceId: string, payload: CreateConnectionInput) {
  return request<GraphEdge>(`/assets/${encodeURIComponent(sourceId)}/connect`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function deleteAsset(id: string) {
  return request<void>(`/assets/${encodeURIComponent(id)}`, { method: 'DELETE' });
}
