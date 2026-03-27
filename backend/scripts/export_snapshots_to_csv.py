#!/usr/bin/env python3
"""
Exportador de Snapshots a CSV para Data Lake ML.

Se ejecuta semanalmente (cron) para exportar los snapshots a CSV
y construir el dataset histórico para entrenamiento ML.

Uso:
    python export_snapshots_to_csv.py --weeks 4
    python export_snapshots_to_csv.py --output /data/snapshots_2026_w12.csv
"""

import argparse
import csv
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Añadir backend al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings
from app.models import CompanySnapshot


def export_snapshots_to_csv(
    output_path: str,
    weeks: int = 1,
    db_url: str = None
):
    """
    Exporta snapshots a CSV.
    
    Args:
        output_path: Ruta del archivo CSV de salida
        weeks: Semanas hacia atrás para exportar
        db_url: URL de la base de datos (opcional)
    """
    # Conectar a DB
    if not db_url:
        settings = get_settings()
        db_url = settings.DATABASE_URL
    
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    # Calcular fecha desde
    from_date = datetime.utcnow() - timedelta(weeks=weeks)
    
    print(f"Exportando snapshots desde {from_date.isoformat()}...")
    
    # Query snapshots
    snapshots = db.query(CompanySnapshot).filter(
        CompanySnapshot.snapshot_date >= from_date
    ).order_by(CompanySnapshot.snapshot_date.desc()).all()
    
    print(f"Encontrados {len(snapshots)} snapshots")
    
    if not snapshots:
        print("No hay datos para exportar")
        return
    
    # Definir columnas
    columns = [
        'id', 'ruc', 'snapshot_date',
        'sunat_status', 'sunat_debt', 'sunat_num_trabajadores',
        'osce_inhabilitado', 'osce_sanciones_count', 'osce_sanciones_vigentes',
        'tce_sanciones_count',
        'dias_ultimo_pago', 'dias_ultima_sancion_osce', 'score_calculado',
        'source_api', 'created_at'
    ]
    
    # Escribir CSV
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        
        for snapshot in snapshots:
            row = {
                'id': snapshot.id,
                'ruc': snapshot.ruc,
                'snapshot_date': snapshot.snapshot_date.isoformat() if snapshot.snapshot_date else '',
                'sunat_status': snapshot.sunat_status or '',
                'sunat_debt': snapshot.sunat_debt or 0,
                'sunat_num_trabajadores': snapshot.sunat_num_trabajadores or '',
                'osce_inhabilitado': snapshot.osce_inhabilitado,
                'osce_sanciones_count': snapshot.osce_sanciones_count or 0,
                'osce_sanciones_vigentes': snapshot.osce_sanciones_vigentes or 0,
                'tce_sanciones_count': snapshot.tce_sanciones_count or 0,
                'dias_ultimo_pago': snapshot.dias_ultimo_pago or '',
                'dias_ultima_sancion_osce': snapshot.dias_ultima_sancion_osce or '',
                'score_calculado': snapshot.score_calculado or '',
                'source_api': snapshot.source_api or '',
                'created_at': snapshot.created_at.isoformat() if snapshot.created_at else ''
            }
            writer.writerow(row)
    
    print(f"✅ Exportado a: {output_path}")
    print(f"   Total registros: {len(snapshots)}")
    print(f"   RUCs únicos: {len(set(s.ruc for s in snapshots))}")
    
    db.close()


def main():
    parser = argparse.ArgumentParser(description='Exportar snapshots a CSV para ML')
    parser.add_argument('--weeks', type=int, default=1, help='Semanas hacia atrás')
    parser.add_argument('--output', type=str, help='Ruta de salida CSV')
    parser.add_argument('--db-url', type=str, help='URL de la base de datos')
    
    args = parser.parse_args()
    
    # Generar nombre por defecto si no se especifica
    if not args.output:
        now = datetime.utcnow()
        week_number = now.isocalendar()[1]
        args.output = f"data/company_snapshots_{now.year}_w{week_number:02d}.csv"
    
    export_snapshots_to_csv(
        output_path=args.output,
        weeks=args.weeks,
        db_url=args.db_url
    )


if __name__ == '__main__':
    main()
