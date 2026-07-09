import { ConflictType, SeverityLevel, ConflictStatus, Party } from './index';

export interface CreateConflictData {
  title: string;
  description: string;
  type: ConflictType;
  severity: SeverityLevel;
  parties: Omit<Party, 'id'>[];
}

export interface UpdateConflictData {
  title?: string;
  description?: string;
  type?: ConflictType;
  severity?: SeverityLevel;
  status?: ConflictStatus;
  parties?: Party[];
}