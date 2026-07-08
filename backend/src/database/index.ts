import Database from 'better-sqlite3';
import { Conflict, ConflictType, SeverityLevel, ConflictStatus, Party } from '../types';

let db: Database.Database | null = null;

export function initDatabase(): Database.Database {
  if (db) return db;
  
  db = new Database('./data/conflicts.db');
  
  db.exec(`
    CREATE TABLE IF NOT EXISTS conflicts (
      id TEXT PRIMARY KEY,
      title TEXT NOT NULL,
      description TEXT NOT NULL,
      type TEXT NOT NULL,
      severity INTEGER NOT NULL,
      status TEXT NOT NULL DEFAULT 'active',
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      resolved_at TEXT
    );
    
    CREATE TABLE IF NOT EXISTS parties (
      id TEXT PRIMARY KEY,
      conflict_id TEXT NOT NULL,
      name TEXT NOT NULL,
      role TEXT NOT NULL,
      contact TEXT,
      FOREIGN KEY (conflict_id) REFERENCES conflicts(id) ON DELETE CASCADE
    );
    
    CREATE INDEX IF NOT EXISTS idx_conflicts_status ON conflicts(status);
    CREATE INDEX IF NOT EXISTS idx_conflicts_severity ON conflicts(severity);
    CREATE INDEX IF NOT EXISTS idx_conflicts_type ON conflicts(type);
    CREATE INDEX IF NOT EXISTS idx_parties_conflict ON parties(conflict_id);
  `);
  
  return db;
}

export function getDatabase(): Database.Database {
  if (!db) throw new Error('Database not initialized');
  return db;
}

export function closeDatabase(): void {
  if (db) {
    db.close();
    db = null;
  }
}

// Conflict operations
export function createConflict(conflict: Conflict): void {
  const database = getDatabase();
  
  const insertConflict = database.prepare(`
    INSERT INTO conflicts (id, title, description, type, severity, status, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
  `);
  
  insertConflict.run(
    conflict.id,
    conflict.title,
    conflict.description,
    conflict.type,
    conflict.severity,
    conflict.status,
    conflict.createdAt,
    conflict.updatedAt
  );
  
  // Insert parties
  const insertParty = database.prepare(`
    INSERT INTO parties (id, conflict_id, name, role, contact)
    VALUES (?, ?, ?, ?, ?)
  `);
  
  for (const party of conflict.parties) {
    insertParty.run(
      party.id,
      conflict.id,
      party.name,
      party.role,
      party.contact || null
    );
  }
}

export function getConflictById(id: string): Conflict | null {
  const database = getDatabase();
  
  const conflict = database.prepare('SELECT * FROM conflicts WHERE id = ?').get(id) as any;
  if (!conflict) return null;
  
  const parties = database.prepare('SELECT * FROM parties WHERE conflict_id = ?').all(id) as any[];
  
  return mapConflictFromDB(conflict, parties);
}

export function getAllConflicts(limit: number = 100, offset: number = 0): Conflict[] {
  const database = getDatabase();
  
  const conflicts = database.prepare(
    'SELECT * FROM conflicts ORDER BY created_at DESC LIMIT ? OFFSET ?'
  ).all(limit, offset) as any[];
  
  return conflicts.map(c => {
    const parties = database.prepare('SELECT * FROM parties WHERE conflict_id = ?').all(c.id) as any[];
    return mapConflictFromDB(c, parties);
  });
}

export function updateConflict(id: string, updates: Partial<Conflict>): void {
  const database = getDatabase();
  const fields: string[] = [];
  const values: any[] = [];
  
  if (updates.title !== undefined) { fields.push('title = ?'); values.push(updates.title); }
  if (updates.description !== undefined) { fields.push('description = ?'); values.push(updates.description); }
  if (updates.type !== undefined) { fields.push('type = ?'); values.push(updates.type); }
  if (updates.severity !== undefined) { fields.push('severity = ?'); values.push(updates.severity); }
  if (updates.status !== undefined) { fields.push('status = ?'); values.push(updates.status); }
  if (updates.updatedAt !== undefined) { fields.push('updated_at = ?'); values.push(updates.updatedAt); }
  if (updates.resolvedAt !== undefined) { fields.push('resolved_at = ?'); values.push(updates.resolvedAt); }
  
  if (fields.length === 0) return;
  
  values.push(id);
  database.prepare(`UPDATE conflicts SET ${fields.join(', ')} WHERE id = ?`).run(...values);
}

export function deleteConflict(id: string): void {
  const database = getDatabase();
  database.prepare('DELETE FROM conflicts WHERE id = ?').run(id);
}

export function getConflictStats(): { total: number; byStatus: Record<string, number>; bySeverity: Record<string, number>; byType: Record<string, number> } {
  const database = getDatabase();
  
  const total = (database.prepare('SELECT COUNT(*) as count FROM conflicts').get() as any).count;
  
  const byStatus = database.prepare('SELECT status, COUNT(*) as count FROM conflicts GROUP BY status').all() as any[];
  const bySeverity = database.prepare('SELECT severity, COUNT(*) as count FROM conflicts GROUP BY severity').all() as any[];
  const byType = database.prepare('SELECT type, COUNT(*) as count FROM conflicts GROUP BY type').all() as any[];
  
  return {
    total,
    byStatus: Object.fromEntries(byStatus.map(r => [r.status, r.count])),
    bySeverity: Object.fromEntries(bySeverity.map(r => [r.severity, r.count])),
    byType: Object.fromEntries(byType.map(r => [r.type, r.count]))
  };
}

function mapConflictFromDB(row: any, parties: any[]): Conflict {
  return {
    id: row.id,
    title: row.title,
    description: row.description,
    type: row.type as ConflictType,
    severity: row.severity as SeverityLevel,
    status: row.status as ConflictStatus,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    resolvedAt: row.resolved_at,
    parties: parties.map(p => ({
      id: p.id,
      name: p.name,
      role: p.role,
      contact: p.contact
    }))
  };
}
