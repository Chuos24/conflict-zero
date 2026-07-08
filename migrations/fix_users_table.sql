-- Migración: Agregar columna hashed_password a tabla users
-- Y crear tabla de registrations pendientes

-- Verificar si la columna existe antes de agregarla
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='users' AND column_name='hashed_password') THEN
        ALTER TABLE users ADD COLUMN hashed_password VARCHAR(255);
        -- Actualizar registros existentes con contraseña temporal
        UPDATE users SET hashed_password = 'temp:pending' WHERE hashed_password IS NULL;
        -- Hacer la columna NOT NULL después de actualizar
        ALTER TABLE users ALTER COLUMN hashed_password SET NOT NULL;
    END IF;
END $$;

-- Tabla para registros pendientes (aprobación manual)
CREATE TABLE IF NOT EXISTS registrations_pending (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    company_name VARCHAR(255),
    ruc VARCHAR(11),
    phone VARCHAR(50),
    plan_requested VARCHAR(50) DEFAULT 'professional',
    status VARCHAR(20) DEFAULT 'pending', -- pending, approved, rejected
    admin_notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP,
    processed_by VARCHAR(255)
);

CREATE INDEX IF NOT EXISTS idx_registrations_pending_status ON registrations_pending(status);
CREATE INDEX IF NOT EXISTS idx_registrations_pending_email ON registrations_pending(email);

-- Insertar algunos registros de prueba si la tabla está vacía
INSERT INTO registrations_pending (id, email, full_name, company_name, ruc, phone, plan_requested, status)
SELECT 
    'test-' || gen_random_uuid()::text,
    'test@example.com',
    'Usuario de Prueba',
    'Empresa Test',
    '20100070970',
    '+51 999 999 999',
    'professional',
    'pending'
WHERE NOT EXISTS (SELECT 1 FROM registrations_pending LIMIT 1);
