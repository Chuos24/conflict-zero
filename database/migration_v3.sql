-- Conflict Zero V3.0 - Migration Score/Plan Desacoplado
-- Fecha: 2026-03-28
-- Objetivo: Separar Score (calculado) de Plan (comprado)

-- 1. Extender tabla companies existente
ALTER TABLE companies
ADD COLUMN IF NOT EXISTS score_calculated INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS plan_type VARCHAR(20) DEFAULT 'starter',
ADD COLUMN IF NOT EXISTS status_validation VARCHAR(50) DEFAULT 'PENDING',
ADD COLUMN IF NOT EXISTS tier_visual VARCHAR(20) GENERATED ALWAYS AS (
    CASE
        WHEN score_calculated >= 90 THEN 'GOLD'
        WHEN score_calculated >= 70 THEN 'SILVER'
        WHEN score_calculated >= 30 THEN 'BRONZE'
        ELSE 'RECHAZADO'
    END
) STORED;

-- 2. Tabla de auditoría de decisiones
CREATE TABLE IF NOT EXISTS validation_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ruc VARCHAR(11) NOT NULL,
    score_detected INTEGER NOT NULL,
    tier_detected VARCHAR(20),
    plan_requested VARCHAR(20),
    plan_allowed VARCHAR(20),
    plan_selected VARCHAR(20),
    validated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address INET
);

-- 3. Tabla de certificados V3 (el producto final)
CREATE TABLE IF NOT EXISTS certificates_v3 (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ruc VARCHAR(11) NOT NULL,
    company_name VARCHAR(200),
    score INTEGER NOT NULL,
    tier_name VARCHAR(20) CHECK (tier_name IN ('GOLD','SILVER','BRONZE','RECHAZADO')),
    plan_type VARCHAR(20) CHECK (plan_type IN ('starter','professional','enterprise')),
    plan_price_paid DECIMAL(10,2),
    cert_slug VARCHAR(50) UNIQUE,
    pdf_url VARCHAR(500),
    issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL '1 year')
);

CREATE INDEX IF NOT EXISTS idx_cert_slug ON certificates_v3(cert_slug);
CREATE INDEX IF NOT EXISTS idx_cert_ruc ON certificates_v3(ruc, issued_at DESC);
CREATE INDEX IF NOT EXISTS idx_validation_logs_ruc ON validation_logs(ruc, validated_at DESC);

-- 4. Pre-cargar Zamora Jara (Demo obligatorio)
INSERT INTO companies (ruc, razon_social, score_calculated, plan_type, status_validation)
VALUES ('20529400790', 'CONSTRUCTORA ZAMORA JARA SAC', 41, 'enterprise', 'ACTIVE')
ON CONFLICT (ruc) DO UPDATE SET
    score_calculated = 41,
    plan_type = 'enterprise',
    status_validation = 'ACTIVE';

-- 5. Pre-cargar otros RUCs de demo
INSERT INTO companies (ruc, razon_social, score_calculated, plan_type, status_validation)
VALUES 
    ('20100123091', 'EMPRESA DEMO GOLD SAC', 95, 'professional', 'ACTIVE'),
    ('20100047218', 'RIMAC SEGUROS', 98, 'enterprise', 'ACTIVE'),
    ('20111111111', 'EMPRESA RECHAZADA SAC', 15, 'starter', 'REJECTED')
ON CONFLICT (ruc) DO UPDATE SET
    score_calculated = EXCLUDED.score_calculated,
    plan_type = EXCLUDED.plan_type,
    status_validation = EXCLUDED.status_validation;

-- Verificación
SELECT ruc, razon_social, score_calculated, tier_visual, plan_type, status_validation 
FROM companies 
WHERE ruc IN ('20529400790', '20100123091', '20100047218')
ORDER BY score_calculated DESC;
