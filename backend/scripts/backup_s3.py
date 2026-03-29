#!/usr/bin/env python3
"""
Backup Automático S3 - Conflict Zero
Backup diario de PostgreSQL a AWS S3
"""
import os
import sys
import boto3
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

# Configuración
S3_BUCKET = os.environ.get('BACKUP_S3_BUCKET', 'conflict-zero-backups')
S3_REGION = os.environ.get('BACKUP_S3_REGION', 'us-east-1')
DATABASE_URL = os.environ.get('DATABASE_URL', '')
RETENTION_DAYS = int(os.environ.get('BACKUP_RETENTION_DAYS', '30'))

def create_backup():
    """Crear backup SQL de PostgreSQL"""
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    backup_file = f"/tmp/backup_{timestamp}.sql"
    
    print(f"[Backup] Creando backup: {backup_file}")
    
    if not DATABASE_URL:
        print("[Backup] ❌ DATABASE_URL no configurado")
        return None
    
    try:
        # Parse DATABASE_URL
        # Format: postgresql://user:pass@host:port/dbname
        url = DATABASE_URL.replace('postgresql://', '').replace('postgres://', '')
        
        if '@' in url:
            credentials, hostpart = url.split('@')
            user, password = credentials.split(':')
        else:
            print("[Backup] ❌ DATABASE_URL formato inválido")
            return None
        
        if ':' in hostpart:
            host_port, dbname = hostpart.split('/')
            host, port = host_port.split(':')
        else:
            host = hostpart.split('/')[0]
            port = '5432'
            dbname = hostpart.split('/')[-1]
        
        # Ejecutar pg_dump
        env = os.environ.copy()
        env['PGPASSWORD'] = password
        
        cmd = [
            'pg_dump',
            '-h', host,
            '-p', port,
            '-U', user,
            '-d', dbname,
            '-f', backup_file,
            '--verbose'
        ]
        
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"[Backup] ❌ pg_dump error: {result.stderr}")
            return None
        
        # Comprimir
        compressed_file = f"{backup_file}.gz"
        subprocess.run(['gzip', '-f', backup_file], check=True)
        
        print(f"[Backup] ✅ Backup creado: {compressed_file}")
        return compressed_file
        
    except Exception as e:
        print(f"[Backup] ❌ Error: {e}")
        return None

def upload_to_s3(local_file):
    """Subir backup a S3"""
    try:
        # Crear cliente S3
        s3 = boto3.client('s3', region_name=S3_REGION)
        
        # Generar key en S3
        date_folder = datetime.now().strftime('%Y/%m')
        filename = os.path.basename(local_file)
        s3_key = f"backups/{date_folder}/{filename}"
        
        print(f"[Backup] Subiendo a S3: {s3_key}")
        
        # Subir archivo
        s3.upload_file(
            local_file,
            S3_BUCKET,
            s3_key,
            ExtraArgs={
                'ServerSideEncryption': 'AES256',
                'StorageClass': 'STANDARD_IA'  # Infrequent Access (más barato)
            }
        )
        
        print(f"[Backup] ✅ Subido a s3://{S3_BUCKET}/{s3_key}")
        
        # Limpiar archivo local
        os.remove(local_file)
        
        return s3_key
        
    except Exception as e:
        print(f"[Backup] ❌ Error S3: {e}")
        return None

def cleanup_old_backups():
    """Eliminar backups antiguos (más de RETENTION_DAYS días)"""
    try:
        s3 = boto3.client('s3', region_name=S3_REGION)
        
        cutoff_date = datetime.now() - timedelta(days=RETENTION_DAYS)
        
        # Listar objetos
        response = s3.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix='backups/'
        )
        
        if 'Contents' not in response:
            return
        
        deleted = 0
        for obj in response['Contents']:
            if obj['LastModified'].replace(tzinfo=None) < cutoff_date:
                s3.delete_object(Bucket=S3_BUCKET, Key=obj['Key'])
                deleted += 1
        
        print(f"[Backup] 🗑️ Eliminados {deleted} backups antiguos")
        
    except Exception as e:
        print(f"[Backup] ⚠️ Error cleanup: {e}")

def main():
    """Función principal"""
    print("=" * 50)
    print("Conflict Zero - Backup Automático S3")
    print(f"Fecha: {datetime.now().isoformat()}")
    print("=" * 50)
    
    # 1. Crear backup
    backup_file = create_backup()
    if not backup_file:
        sys.exit(1)
    
    # 2. Subir a S3
    s3_key = upload_to_s3(backup_file)
    if not s3_key:
        sys.exit(1)
    
    # 3. Cleanup
    cleanup_old_backups()
    
    print("=" * 50)
    print("[Backup] ✅ Proceso completado exitosamente")
    print("=" * 50)

if __name__ == '__main__':
    main()
