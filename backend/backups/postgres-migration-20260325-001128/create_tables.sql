-- PostgreSQL Schema for Conflict Zero
-- Compatible con SQLAlchemy models

-- Extensión para UUID (si se desea migrar a UUID nativo en el futuro)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tabla users
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    company_name VARCHAR(255),
    ruc VARCHAR(11),
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    plan_type VARCHAR(50) DEFAULT 'essential',
    api_key VARCHAR(255) UNIQUE,
    monthly_requests INTEGER DEFAULT 0,
    monthly_limit INTEGER DEFAULT 1000,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_api_key ON users(api_key);

-- Tabla verification_requests
CREATE TABLE IF NOT EXISTS verification_requests (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ruc VARCHAR(11) NOT NULL,
    company_name VARCHAR(255),
    score INTEGER NOT NULL,
    risk_level VARCHAR(20) NOT NULL,
    sunat_debt FLOAT DEFAULT 0.0,
    sunat_score_contribution FLOAT DEFAULT 0.0,
    osce_sanctions_count INTEGER DEFAULT 0,
    osce_score_contribution FLOAT DEFAULT 0.0,
    osce_sanctions_details JSONB DEFAULT '[]'::jsonb,
    tce_sanctions_count INTEGER DEFAULT 0,
    tce_score_contribution FLOAT DEFAULT 0.0,
    tce_sanctions_details JSONB DEFAULT '[]'::jsonb,
    ml_anomaly_score FLOAT DEFAULT 0.0,
    ml_score_contribution FLOAT DEFAULT 0.0,
    raw_data JSONB DEFAULT '{}'::jsonb,
    pdf_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_verification_requests_user_id ON verification_requests(user_id);
CREATE INDEX idx_verification_requests_ruc ON verification_requests(ruc);
CREATE INDEX idx_verification_requests_created_at ON verification_requests(created_at);

-- Tabla api_keys
CREATE TABLE IF NOT EXISTS api_keys (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    last_used_at TIMESTAMP,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);

CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX idx_api_keys_key_hash ON api_keys(key_hash);

-- Tabla system_logs
CREATE TABLE IF NOT EXISTS system_logs (
    id VARCHAR(36) PRIMARY KEY,
    level VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    source VARCHAR(100),
    meta_data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_system_logs_created_at ON system_logs(created_at);
CREATE INDEX idx_system_logs_level ON system_logs(level);

-- Trigger para actualizar updated_at en users
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Comentarios para documentación
COMMENT ON TABLE users IS 'Usuarios registrados en la plataforma';
COMMENT ON TABLE verification_requests IS 'Historial de verificaciones de RUC';
COMMENT ON TABLE api_keys IS 'API keys para integraciones';
COMMENT ON TABLE system_logs IS 'Logs del sistema';
