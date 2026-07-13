-- Migración: Agregar columnas faltantes a users y crear tablas nuevas
-- Fecha: 2026-07-13

-- Agregar columnas faltantes en users (si no existen)
ALTER TABLE users ADD COLUMN is_approved BOOLEAN DEFAULT 0;
ALTER TABLE users ADD COLUMN status VARCHAR(20) DEFAULT 'active';
ALTER TABLE users ADD COLUMN plan_activated_at DATETIME;
ALTER TABLE users ADD COLUMN plan_expires_at DATETIME;

-- Crear tabla certificates
CREATE TABLE IF NOT EXISTS certificates (
    id VARCHAR(36) PRIMARY KEY,
    ruc VARCHAR(11) NOT NULL,
    company_name VARCHAR(255),
    score FLOAT DEFAULT 0.0,
    tier VARCHAR(20) NOT NULL DEFAULT 'BRONZE',
    plan_type VARCHAR(50) DEFAULT 'essential',
    cert_slug VARCHAR(50) UNIQUE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME
);
CREATE INDEX IF NOT EXISTS idx_certificates_ruc ON certificates(ruc);
CREATE INDEX IF NOT EXISTS idx_certificates_slug ON certificates(cert_slug);

-- Crear tabla invitations
CREATE TABLE IF NOT EXISTS invitations (
    id VARCHAR(36) PRIMARY KEY,
    invitador_ruc VARCHAR(11) NOT NULL,
    email VARCHAR(255) NOT NULL,
    token VARCHAR(255) UNIQUE NOT NULL,
    ruc_invitado VARCHAR(11),
    usada BOOLEAN DEFAULT 0,
    usada_por VARCHAR(36),
    expira DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_invitations_invitador ON invitations(invitador_ruc);
CREATE INDEX IF NOT EXISTS idx_invitations_token ON invitations(token);

-- Crear tabla payments_manual
CREATE TABLE IF NOT EXISTS payments_manual (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id),
    amount FLOAT NOT NULL,
    currency VARCHAR(10) DEFAULT 'PEN',
    method VARCHAR(50) NOT NULL,
    reference VARCHAR(255) NOT NULL,
    payment_date DATETIME NOT NULL,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Crear tabla user_suppliers (si no existe)
CREATE TABLE IF NOT EXISTS user_suppliers (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id),
    ruc VARCHAR(11) NOT NULL,
    supplier_name VARCHAR(255),
    notes TEXT,
    added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_checked_at DATETIME,
    last_score INTEGER,
    last_risk_level VARCHAR(20),
    last_osce_sanciones INTEGER,
    last_tce_sanciones INTEGER
);

-- Crear tabla ruc_cache (si no existe)
CREATE TABLE IF NOT EXISTS ruc_cache (
    id VARCHAR(36) PRIMARY KEY,
    ruc VARCHAR(11) UNIQUE NOT NULL,
    cached_data TEXT NOT NULL DEFAULT '{}',
    source VARCHAR(50) DEFAULT 'unknown',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL,
    hit_count INTEGER DEFAULT 0,
    last_hit_at DATETIME,
    is_valid BOOLEAN DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_ruc_cache_ruc ON ruc_cache(ruc);
