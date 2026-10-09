import { apiRequest } from '../../services/http'

export type ScannerState =
  | 'PENDING'
  | 'LINKED'
  | 'REVOKED'
  | 'EXPIRED'
  | 'DISCONNECTED'

export type ScannerLink = {
  id: string
  state: ScannerState
  cash_id: string
  branch_id: string
  qr_expires_at: string
  expires_at: string
  linked_at: string | null
}

export type CreatedScannerLink = ScannerLink & {
  pairing_code: string
}

async function request<T>(
  path: string,
  method: 'GET' | 'POST',
): Promise<T> {
  const response = await apiRequest(
    path,
    { method },
    {},
    true,
  )

  return response.json() as Promise<T>
}

export const scannerApi = {
  create: () =>
    request<CreatedScannerLink>('/api/scanner/links', 'POST'),

  status: (id: string) =>
    request<ScannerLink>(
      `/api/scanner/links/${encodeURIComponent(id)}`,
      'GET',
    ),

  revoke: (id: string) =>
    request<ScannerLink>(
      `/api/scanner/links/${encodeURIComponent(id)}/revoke`,
      'POST',
    ),
}