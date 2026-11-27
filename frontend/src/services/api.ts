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
  software?: SoftwareItem[];
  risk_score?: number | null;
  risk_level?: string | null;
  risk_calculated_at?: string | null;
}

export interface SoftwareItem {
  product: string;
  version?: string | null;
  source?: string;
  confidence?: number;
  evidence?: string;
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

export interface VulnerabilityDetails {
  cve_id: string;
  description?: string | null;
  severity?: string | null;
  cvss_score?: number | null;
  cvss_version?: string | null;
  cvss_vector?: string | null;
  published_at?: string | null;
  last_modified_at?: string | null;
  source: string;
  references: string[];
  last_fetched_at?: string | null;
  rejected: boolean;
}

export interface AssetVulnerability {
  cve_id: string;
  vulnerability: VulnerabilityDetails;
  match_type: 'confirmed' | 'potential' | 'manual' | 'rejected' | 'resolved';
  confidence: number;
  status: string;
  matched_product?: string | null;
  matched_version?: string | null;
  evidence?: string | null;
  added_at?: string | null;
}

export interface ExposureAssessment {
  exposure_level: 'public' | 'internal' | 'restricted' | 'unknown';
  evidence: string[];
  uncertainty: string[];
}

export interface RiskResult {
  asset_id: string;
  overall_score: number;
  risk_level: 'low' | 'medium' | 'high';
  vulnerability_contribution: number;
  exposure_contribution: number;
  connectivity_contribution: number;
  criticality_contribution: number;
  factor_scores: Record<string, number>;
  explanation: string;
  evidence: string[];
  uncertainty: string[];
  formula_version: string;
  calculated_at: string;
}

export interface RiskSummary {
  total_assets: number;
  confirmed_vulnerability_assets: number;
  distinct_associated_cves: number;
  high_risk_assets: number;
  medium_risk_assets: number;
  low_risk_assets: number;
  unknown_risk_assets: number;
  overall_infrastructure_risk: 'low' | 'medium' | 'high' | 'unknown';
  aggregation_method: string;
}

export function searchVulnerabilities(keyword: string) {
  return request<{ total_results: number; items: VulnerabilityDetails[] }>(
    `/vulnerabilities/search?keyword=${encodeURIComponent(keyword)}&results_per_page=20`,
  );
}

export function getAssetVulnerabilities(assetId: string) {
  return request<AssetVulnerability[]>(`/assets/${encodeURIComponent(assetId)}/vulnerabilities`);
}

export function attachAssetVulnerability(assetId: string, payload: {
  cve_id: string;
  evidence?: string;
  match_type: 'confirmed' | 'potential' | 'manual';
  status: 'accepted' | 'potential' | 'resolved' | 'rejected';
  matched_product?: string;
  matched_version?: string;
}) {
  return request<AssetVulnerability>(`/assets/${encodeURIComponent(assetId)}/vulnerabilities`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updateAssetVulnerability(assetId: string, cveId: string, payload: {
  status: 'accepted' | 'potential' | 'resolved' | 'rejected';
  evidence?: string;
  match_type?: 'confirmed' | 'potential' | 'manual' | 'rejected' | 'resolved';
}) {
  return request<AssetVulnerability>(
    `/assets/${encodeURIComponent(assetId)}/vulnerabilities/${encodeURIComponent(cveId)}`,
    { method: 'PATCH', body: JSON.stringify(payload) },
  );
}

export function removeAssetVulnerability(assetId: string, cveId: string) {
  return request<void>(
    `/assets/${encodeURIComponent(assetId)}/vulnerabilities/${encodeURIComponent(cveId)}`,
    { method: 'DELETE' },
  );
}

export function refreshAssetVulnerabilities(assetId: string) {
  return request<AssetVulnerability[]>(`/assets/${encodeURIComponent(assetId)}/vulnerabilities/refresh`, { method: 'POST' });
}

export function getAssetExposure(assetId: string) {
  return request<ExposureAssessment>(`/assets/${encodeURIComponent(assetId)}/exposure`);
}

export function getAssetRisk(assetId: string) {
  return request<RiskResult>(`/assets/${encodeURIComponent(assetId)}/risk`);
}

export function recalculateAssetRisk(assetId: string) {
  return request<RiskResult>(`/assets/${encodeURIComponent(assetId)}/risk/recalculate`, { method: 'POST' });
}

export function getRiskSummary() {
  return request<RiskSummary>('/risk/summary');
}
