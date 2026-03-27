"""
Servicio para colectar datos de múltiples fuentes para un RUC.
Combina SUNAT, OSCE, RNP/TCE en una sola respuesta.
"""
from typing import Dict, Any
from app.services.external_api import get_external_api
from app.services.osce_datos_abiertos import osce_datos_abiertos
from app.services.rnp_datos import rnp_service
from app.core.cache import cache


async def collect_all_data(ruc: str) -> Dict[str, Any]:
    """
    Colecta datos de todas las fuentes disponibles para un RUC.
    
    Args:
        ruc: Número de RUC de 11 dígitos
        
    Returns:
        Dict con datos combinados de SUNAT, OSCE, RNP/TCE
    """
    cache_key = f"collected_data:{ruc}"
    
    # Intentar obtener del caché
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    # Obtener datos de SUNAT
    external_api = get_external_api()
    sunat_data = external_api.get_sunat_data(ruc)
    
    # Obtener datos de OSCE desde PostgreSQL
    osce_data = osce_datos_abiertos.get_sanciones_from_db(ruc) or {
        'ruc': ruc,
        'cantidad_sanciones': 0,
        'cantidad_penalidades': 0,
        'cantidad_inhabilitaciones': 0,
        'sanciones_vigentes': 0,
        'score_osce_anual': 100,
        'monto_total_penalidades': 0,
        'fuente': 'none'
    }
    
    # Obtener detalles de sanciones OSCE
    osce_detalle = osce_datos_abiertos.get_sanciones_detalle_from_db(ruc) or []
    
    # Obtener datos de RNP/TCE
    rnp_data = rnp_service.get_sanciones_from_db(ruc) or {
        'ruc': ruc,
        'cantidad_sanciones': 0,
        'sanciones_vigentes': 0,
        'sanciones_definitivas': 0,
        'sanciones_temporales': 0,
        'monto_total_multas': 0,
        'fuente': 'none'
    }
    
    # Obtener detalle de sanciones RNP
    rnp_detalle = rnp_service.get_sanciones_detalle(ruc) or []
    
    # Combinar todos los datos
    result = {
        'ruc': ruc,
        'razon_social': sunat_data.get('razon_social') or sunat_data.get('nombre_comercial', ''),
        'sunat': {
            'estado': sunat_data.get('estado_contribuyente', 'DESCONOCIDO'),
            'condicion': sunat_data.get('condicion_domicilio', 'DESCONOCIDO'),
            'direccion': sunat_data.get('direccion', ''),
            'departamento': sunat_data.get('departamento', ''),
            'provincia': sunat_data.get('provincia', ''),
            'distrito': sunat_data.get('distrito', ''),
            'ubigeo': sunat_data.get('ubigeo', ''),
            'fuente': sunat_data.get('fuente', 'desconocido'),
            'fecha_consulta': sunat_data.get('fecha_consulta'),
            'deuda': sunat_data.get('deuda_coactiva', 0) if 'deuda_coactiva' in sunat_data else 0
        },
        'osce': {
            'cantidad_sanciones': osce_data.get('cantidad_sanciones', 0),
            'cantidad_penalidades': osce_data.get('cantidad_penalidades', 0),
            'cantidad_inhabilitaciones': osce_data.get('cantidad_inhabilitaciones', 0),
            'sanciones_vigentes': osce_data.get('sanciones_vigentes', 0),
            'score_osce_anual': osce_data.get('score_osce_anual', 100),
            'monto_total_penalidades': float(osce_data.get('monto_total_penalidades', 0)),
            'detalle': osce_detalle,
            'fuente': osce_data.get('fuente', 'none')
        },
        'rnp': {
            'cantidad_sanciones': rnp_data.get('cantidad_sanciones', 0),
            'sanciones_vigentes': rnp_data.get('sanciones_vigentes', 0),
            'sanciones_definitivas': rnp_data.get('sanciones_definitivas', 0),
            'sanciones_temporales': rnp_data.get('sanciones_temporales', 0),
            'monto_total_multas': float(rnp_data.get('monto_total_multas', 0)),
            'detalle': rnp_detalle,
            'fuente': rnp_data.get('fuente', 'none')
        }
    }
    
    # Guardar en caché por 15 minutos
    cache.set(cache_key, result, expire=900)
    
    return result


def calculate_risk_score(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calcula un score de riesgo simplificado basado en los datos colectados.
    
    Args:
        data: Datos colectados del RUC
        
    Returns:
        Dict con score, nivel de riesgo y resumen
    """
    from app.services.scoring import scoring_engine
    
    ruc = data.get('ruc', '')
    razon_social = data.get('razon_social', '')
    sunat = data.get('sunat', {})
    
    # Obtener sanciones como lista para el scoring engine
    osce_detalle = data.get('osce', {}).get('detalle', [])
    sanciones_list = [
        {
            'sanction_id': s.get('id', ''),
            'description': s.get('entidad', ''),
            'date': s.get('fecha_inicio'),
            'status': s.get('estado', ''),
            'severity': 'alta' if s.get('tipo') == 'inhabilitacion' else 'media',
            'entity': s.get('entidad', 'OSCE'),
            'fecha_fin': s.get('fecha_fin'),
            'tipo': s.get('tipo', '')
        }
        for s in osce_detalle
    ]
    
    # Usar el scoring engine existente
    score_result = scoring_engine.calculate_total_score(
        ruc=ruc,
        razon_social=razon_social,
        estado=sunat.get('estado', 'ACTIVO'),
        condicion=sunat.get('condicion', 'HABIDO'),
        deuda=sunat.get('deuda', 0),
        osce_sanctions=sanciones_list,
        tce_sanctions=[]  # RNP/TCE ya se incluye en scoring_engine.calculate_rnp_score
    )
    
    # Extraer resumen de sanciones para mostrar
    fines_summary = []
    
    # Agregar sanciones OSCE
    for s in osce_detalle[:3]:  # Máximo 3
        estado = s.get('estado', 'DESCONOCIDO')
        fecha_fin = s.get('fecha_fin', '')
        fines_summary.append({
            'tipo': 'OSCE',
            'entidad': s.get('entidad', ''),
            'resolucion': s.get('numero_resolucion', ''),
            'estado': estado,
            'fecha_fin': fecha_fin,
            'tipo_sancion': s.get('tipo', '')
        })
    
    # Agregar sanciones RNP
    for s in data.get('rnp', {}).get('detalle', [])[:3]:
        estado = s.get('estado', 'DESCONOCIDO')
        fecha_hasta = s.get('fecha_hasta', '')
        fines_summary.append({
            'tipo': 'TCE',
            'resolucion': s.get('resolucion', ''),
            'tipo_sancion': s.get('tipo_sancion', ''),
            'estado': estado,
            'fecha_hasta': fecha_hasta,
            'monto_multa': s.get('monto_multa', 0)
        })
    
    return {
        'score': score_result['total_score'],
        'risk_level': score_result['risk_level'],
        'fines_summary': fines_summary,
        'detalle': score_result
    }
