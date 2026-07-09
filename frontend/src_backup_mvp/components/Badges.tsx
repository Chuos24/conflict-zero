import { ConflictStatus, SeverityLevel } from '../types';

interface StatusBadgeProps {
  status: ConflictStatus;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const styles = {
    [ConflictStatus.ACTIVE]: 'bg-blue-100 text-blue-800',
    [ConflictStatus.PENDING]: 'bg-yellow-100 text-yellow-800',
    [ConflictStatus.RESOLVED]: 'bg-green-100 text-green-800',
    [ConflictStatus.ESCALATED]: 'bg-red-100 text-red-800',
  };

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${styles[status]}`}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}

interface SeverityBadgeProps {
  severity: SeverityLevel;
}

export function SeverityBadge({ severity }: SeverityBadgeProps) {
  const styles = {
    [SeverityLevel.LOW]: 'bg-green-100 text-green-800',
    [SeverityLevel.MEDIUM]: 'bg-yellow-100 text-yellow-800',
    [SeverityLevel.HIGH]: 'bg-orange-100 text-orange-800',
    [SeverityLevel.CRITICAL]: 'bg-red-100 text-red-800',
  };

  const labels = {
    [SeverityLevel.LOW]: 'Low',
    [SeverityLevel.MEDIUM]: 'Medium',
    [SeverityLevel.HIGH]: 'High',
    [SeverityLevel.CRITICAL]: 'Critical',
  };

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${styles[severity]}`}>
      {labels[severity]}
    </span>
  );
}
