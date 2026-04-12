export interface Conflict {
  id: string;
  title: string;
  description: string;
  type: ConflictType;
  severity: SeverityLevel;
  status: ConflictStatus;
  parties: Party[];
  createdAt: string;
  updatedAt: string;
  resolvedAt?: string;
}

export enum ConflictType {
  INTERPERSONAL = 'interpersonal',
  ORGANIZATIONAL = 'organizational',
  RESOURCE = 'resource',
  POLICY = 'policy',
  OTHER = 'other'
}

export enum SeverityLevel {
  LOW = 1,
  MEDIUM = 2,
  HIGH = 3,
  CRITICAL = 4
}

export enum ConflictStatus {
  ACTIVE = 'active',
  PENDING = 'pending',
  RESOLVED = 'resolved',
  ESCALATED = 'escalated'
}

export interface Party {
  id: string;
  name: string;
  role: string;
  contact?: string;
}

export interface ConflictStats {
  total: number;
  byStatus: Record<string, number>;
  bySeverity: Record<string, number>;
  byType: Record<string, number>;
  recent: Conflict[];
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}
