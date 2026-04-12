import { Request, Response } from 'express';
import { v4 as uuidv4 } from 'uuid';
import { 
  CreateConflictRequest, 
  UpdateConflictRequest, 
  ConflictStatus,
  Conflict 
} from '../types';
import * as db from '../database';

export function getAllConflicts(req: Request, res: Response): void {
  try {
    const limit = parseInt(req.query.limit as string) || 100;
    const offset = parseInt(req.query.offset as string) || 0;
    
    const conflicts = db.getAllConflicts(limit, offset);
    res.json({ success: true, data: conflicts });
  } catch (error) {
    res.status(500).json({ success: false, error: 'Failed to fetch conflicts' });
  }
}

export function getConflictById(req: Request, res: Response): void {
  try {
    const { id } = req.params;
    const conflict = db.getConflictById(id);
    
    if (!conflict) {
      res.status(404).json({ success: false, error: 'Conflict not found' });
      return;
    }
    
    res.json({ success: true, data: conflict });
  } catch (error) {
    res.status(500).json({ success: false, error: 'Failed to fetch conflict' });
  }
}

export function createConflict(req: Request, res: Response): void {
  try {
    const data = req.body as CreateConflictRequest;
    const now = new Date().toISOString();
    
    const conflict: Conflict = {
      id: uuidv4(),
      title: data.title,
      description: data.description,
      type: data.type,
      severity: data.severity,
      status: ConflictStatus.ACTIVE,
      parties: data.parties.map(p => ({ ...p, id: uuidv4() })),
      createdAt: now,
      updatedAt: now
    };
    
    db.createConflict(conflict);
    res.status(201).json({ success: true, data: conflict });
  } catch (error) {
    res.status(500).json({ success: false, error: 'Failed to create conflict' });
  }
}

export function updateConflict(req: Request, res: Response): void {
  try {
    const { id } = req.params;
    const data = req.body as UpdateConflictRequest;
    const existing = db.getConflictById(id);
    
    if (!existing) {
      res.status(404).json({ success: false, error: 'Conflict not found' });
      return;
    }
    
    const updates: Partial<Conflict> = {
      ...data,
      updatedAt: new Date().toISOString()
    };
    
    if (data.status === ConflictStatus.RESOLVED && !existing.resolvedAt) {
      updates.resolvedAt = new Date().toISOString();
    }
    
    db.updateConflict(id, updates);
    const updated = db.getConflictById(id);
    
    res.json({ success: true, data: updated });
  } catch (error) {
    res.status(500).json({ success: false, error: 'Failed to update conflict' });
  }
}

export function deleteConflict(req: Request, res: Response): void {
  try {
    const { id } = req.params;
    const existing = db.getConflictById(id);
    
    if (!existing) {
      res.status(404).json({ success: false, error: 'Conflict not found' });
      return;
    }
    
    db.deleteConflict(id);
    res.json({ success: true, message: 'Conflict deleted' });
  } catch (error) {
    res.status(500).json({ success: false, error: 'Failed to delete conflict' });
  }
}

export function getStats(req: Request, res: Response): void {
  try {
    const stats = db.getConflictStats();
    res.json({ success: true, data: stats });
  } catch (error) {
    res.status(500).json({ success: false, error: 'Failed to fetch stats' });
  }
}
