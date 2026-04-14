-- Crear tabla para almacenar datos de RUCs
CREATE TABLE IF NOT EXISTS ruc_cache (
    ruc VARCHAR(11) PRIMARY KEY,
    razon_social VARCHAR(255) NOT NULL,
    nombre_comercial VARCHAR(255),
    estado VARCHAR(50) DEFAULT 'ACTIVO',
    condicion VARCHAR(50) DEFAULT 'HABIDO',
    direccion TEXT,
    departamento VARCHAR(100),
    provincia VARCHAR(100),
    distrito VARCHAR(100),
    ubigeo VARCHAR(10),
    fuente VARCHAR(50) DEFAULT 'manual',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Crear índice para búsqueda rápida
CREATE INDEX IF NOT EXISTS idx_ruc_cache_razon_social ON ruc_cache(razon_social);

-- Insertar algunos RUCs importantes que no están en Factiliza
INSERT INTO ruc_cache (ruc, razon_social, estado, fuente) VALUES
('20100049581', 'DROGUERIA FARVET SA', 'ACTIVO', 'manual'),
('20502126297', 'GRUAS Y SERVICIOS INDUSTRIALES DEL PERU S.A.C.', 'ACTIVO', 'manual'),
('20521657021', 'CORPORACION INMOBILIARIA VISTA ALEGRE S.A.C.', 'ACTIVO', 'manual')
ON CONFLICT (ruc) DO NOTHING;
