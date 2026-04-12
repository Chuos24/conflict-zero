# Conflict Zero - Fase 1 Plan de Desarrollo

## Visión
Sistema de gestión y análisis de conflictos con visualización de datos.

## Stack Tecnológico Actual
- **Backend (Producción)**: Python + FastAPI + PostgreSQL
- **Backend (Fase 1 Plan)**: Node.js + Express + TypeScript + SQLite
- **Frontend (Producción)**: Next.js + React + TypeScript
- **Frontend (Fase 1 Plan)**: React + TypeScript + Vite
- **Estado**: Zustand
- **Estilos**: Tailwind CSS

## Nota Importante
El proyecto tiene dos backends:
1. **Python FastAPI** (`app/`, `backend/app/`) - Backend en producción en Render
2. **Node.js Express** (`backend/src/`) - Backend experimental Fase 1 (nuevo stack)

## Estructura del Proyecto Fase 1 (Node.js Stack)
```
conflict-zero/
├── backend/                    # Backend Node.js/TypeScript
│   ├── src/
│   │   ├── index.ts           ✅ Servidor Express
│   │   ├── routes/
│   │   │   └── conflicts.ts   ✅ Rutas CRUD
│   │   ├── controllers/
│   │   │   └── conflictController.ts  ✅ Controladores
│   │   ├── database/
│   │   │   └── index.ts       ✅ SQLite con better-sqlite3
│   │   └── types/
│   │       └── index.ts       ✅ Tipos TypeScript
│   ├── package.json           ✅ Configuración
│   └── data/                  📁 Directorio para SQLite
├── frontend/                  # Frontend React/Vite
│   ├── src/
│   │   ├── App.tsx            ✅ Router
│   │   ├── main.tsx           ✅ Entry point
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx  ✅ Listado de conflictos
│   │   │   ├── ConflictDetail.tsx  ✅ Detalle de conflicto
│   │   │   └── ConflictForm.tsx    ✅ Formulario crear/editar
│   │   ├── components/
│   │   │   ├── Layout.tsx     ✅ Layout base
│   │   │   ├── ConflictList.tsx    ✅ Lista de conflictos
│   │   │   └── Badges.tsx     ✅ Componente de badges
│   │   ├── stores/
│   │   │   └── conflictStore.ts    ✅ Zustand store
│   │   └── types/
│   │       └── index.ts       ✅ Tipos + form types
│   ├── package.json           ✅ Configuración
│   └── vite.config.ts         ✅ Config Vite
└── README.md
```

## Fase 1 - MVP - Estado de Completitud

### Backend Node.js
| Componente | Estado | Archivo |
|------------|--------|---------|
| Servidor Express | ✅ | `backend/src/index.ts` |
| Rutas CRUD | ✅ | `backend/src/routes/conflicts.ts` |
| Controladores | ✅ | `backend/src/controllers/conflictController.ts` |
| Base de datos SQLite | ✅ | `backend/src/database/index.ts` |
| Tipos TypeScript | ✅ | `backend/src/types/index.ts` |

### Frontend React
| Componente | Estado | Archivo |
|------------|--------|---------|
| Router | ✅ | `frontend/src/App.tsx` |
| Layout | ✅ | `frontend/src/components/Layout.tsx` |
| Dashboard | ✅ | `frontend/src/pages/Dashboard.tsx` |
| ConflictDetail | ✅ | `frontend/src/pages/ConflictDetail.tsx` |
| ConflictForm | ✅ | `frontend/src/pages/ConflictForm.tsx` |
| ConflictList | ✅ | `frontend/src/components/ConflictList.tsx` |
| Badges | ✅ | `frontend/src/components/Badges.tsx` |
| Zustand Store | ✅ | `frontend/src/stores/conflictStore.ts` |
| Tipos | ✅ | `frontend/src/types/index.ts` |

## Backend Python (Producción) - Estado

El backend Python FastAPI es el sistema en producción actual con:
- ✅ 10+ routers (auth, verification, dashboard, compare, payments, admin, etc.)
- ✅ 14 modelos SQLAlchemy
- ✅ Servicios de verificación RUC con SUNAT, OSCE, RNP/TCE
- ✅ Sistema de scoring predictivo multidimensional
- ✅ Integración con PostgreSQL
- ✅ Fórmula "cruda pero justa" con recuperación temporal
- ⚠️ Problema conocido: RUC 20529400790 cache en Render

## Estado Actual
**Actualizado**: 2026-04-12
**Fase 1 MVP**: ✅ 100% Completo (Node.js stack)
**Producción**: Activa con Python FastAPI

## Próximos Pasos
1. Evaluar migración de Python a Node.js para unificación de stack
2. Resolver problema de cache en Render para RUC 20529400790
3. Integrar frontend Fase 1 con backend Node.js para testing
4. Decidir stack definitivo para Fase 2
