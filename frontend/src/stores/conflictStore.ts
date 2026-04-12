import { create } from 'zustand';
import { Conflict, ConflictStats, CreateConflictData, UpdateConflictData } from '../types';

const API_URL = '/api';

interface ConflictState {
  conflicts: Conflict[];
  currentConflict: Conflict | null;
  stats: ConflictStats | null;
  loading: boolean;
  error: string | null;
  
  // Actions
  fetchConflicts: () => Promise<void>;
  fetchConflict: (id: string) => Promise<void>;
  fetchStats: () => Promise<void>;
  createConflict: (data: CreateConflictData) => Promise<void>;
  updateConflict: (id: string, data: UpdateConflictData) => Promise<void>;
  deleteConflict: (id: string) => Promise<void>;
  setCurrentConflict: (conflict: Conflict | null) => void;
  clearError: () => void;
}

export const useConflictStore = create<ConflictState>((set, get) => ({
  conflicts: [],
  currentConflict: null,
  stats: null,
  loading: false,
  error: null,

  fetchConflicts: async () => {
    set({ loading: true, error: null });
    try {
      const response = await fetch(`${API_URL}/conflicts`);
      const result = await response.json();
      if (result.success) {
        set({ conflicts: result.data, loading: false });
      } else {
        set({ error: result.error, loading: false });
      }
    } catch (error) {
      set({ error: 'Failed to fetch conflicts', loading: false });
    }
  },

  fetchConflict: async (id: string) => {
    set({ loading: true, error: null });
    try {
      const response = await fetch(`${API_URL}/conflicts/${id}`);
      const result = await response.json();
      if (result.success) {
        set({ currentConflict: result.data, loading: false });
      } else {
        set({ error: result.error, loading: false });
      }
    } catch (error) {
      set({ error: 'Failed to fetch conflict', loading: false });
    }
  },

  fetchStats: async () => {
    try {
      const response = await fetch(`${API_URL}/conflicts/stats`);
      const result = await response.json();
      if (result.success) {
        set({ stats: result.data });
      }
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  },

  createConflict: async (data: CreateConflictData) => {
    set({ loading: true, error: null });
    try {
      const response = await fetch(`${API_URL}/conflicts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      const result = await response.json();
      if (result.success) {
        set(state => ({ 
          conflicts: [result.data, ...state.conflicts],
          loading: false 
        }));
      } else {
        set({ error: result.error, loading: false });
      }
    } catch (error) {
      set({ error: 'Failed to create conflict', loading: false });
    }
  },

  updateConflict: async (id: string, data: UpdateConflictData) => {
    set({ loading: true, error: null });
    try {
      const response = await fetch(`${API_URL}/conflicts/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      const result = await response.json();
      if (result.success) {
        set(state => ({
          conflicts: state.conflicts.map(c => c.id === id ? result.data : c),
          currentConflict: state.currentConflict?.id === id ? result.data : state.currentConflict,
          loading: false,
        }));
      } else {
        set({ error: result.error, loading: false });
      }
    } catch (error) {
      set({ error: 'Failed to update conflict', loading: false });
    }
  },

  deleteConflict: async (id: string) => {
    set({ loading: true, error: null });
    try {
      const response = await fetch(`${API_URL}/conflicts/${id}`, {
        method: 'DELETE',
      });
      const result = await response.json();
      if (result.success) {
        set(state => ({
          conflicts: state.conflicts.filter(c => c.id !== id),
          currentConflict: state.currentConflict?.id === id ? null : state.currentConflict,
          loading: false,
        }));
      } else {
        set({ error: result.error, loading: false });
      }
    } catch (error) {
      set({ error: 'Failed to delete conflict', loading: false });
    }
  },

  setCurrentConflict: (conflict: Conflict | null) => {
    set({ currentConflict: conflict });
  },

  clearError: () => {
    set({ error: null });
  },
}));
