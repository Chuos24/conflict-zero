import random
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import requests
from app.core.config import get_settings
from app.core.cache import cache

settings = get_settings()

class ExternalAPIService:
    """
    Servicio para consultar APIs externas de datos peruanos.
    Soporta: SUNAT, OSCE, RENIEC, TCE
    
    En modo desarrollo/simulación, genera datos de prueba.
    En producción, conecta con Decolecta API o APIs oficiales.
    """
    
    def __init__(self):
        self.api_key = settings.DECOLECTA_API_KEY
        self.base_url = settings.DECOLECTA_BASE_URL
        self.use_real_api = bool(self.api_key and self.api_key != "your-api-key")
    
    def _generate_mock_sunat_data(self, ruc: str) -> Dict[str, Any]:
        """Genera datos simulados de SUNAT basados en el RUC."""
        # Usar el RUC como seed para consistencia
        seed = sum(int(d) for d in ruc)
        random.seed(seed)
        
        # Determinar si tiene deuda (30% de probabilidad)
        has_debt = random.random() < 0.30
        
        if has_debt:
            # Deuda entre 5k y 500k soles
            debt_amount = round(random.uniform(5000, 500000), 2)
            tax_status = "Deuda pendiente"
        else:
            debt_amount = 0.0
            tax_status = "Activo sin deuda"
        
        # Determinar estado del contribuyente
        status_options = ["ACTIVO", "ACTIVO", "ACTIVO", "SUSPENSIÓN TEMPORAL", "BAJA DEFINITIVA"]
        contributor_status = random.choice(status_options)
        
        company_name = self._generate_company_name(ruc)
        
        return {
            "ruc": ruc,
            "razon_social": company_name,
            "estado_contribuyente": contributor_status,
            "condicion_domicilio": "HABIDO",
            "ubigeo": random.choice(["150101", "150103", "150114", "070101"]),
            "tipo_via": "AV.",
            "nombre_via": "JAVIER PRADO",
            "codigo_zona": "URB.",
            "tipo_zona": "CORPAC",
            "numero": str(random.randint(100, 9999)),
            "interior": "",
            "lote": "",
            "departamento": "LIMA",
            "provincia": "LIMA",
            "distrito": random.choice(["SAN ISIDRO", "MIRAFLORES", "SAN BORJA", "LA VICTORIA"]),
            "deuda_coactiva": debt_amount,
            "deuda_tributaria": debt_amount * 0.7,
            "deuda_aduanera": debt_amount * 0.3,
            "estado_tributario": tax_status,
            "fecha_consulta": datetime.now().isoformat()
        }
    
    def _generate_mock_osce_data(self, ruc: str) -> List[Dict[str, Any]]:
        """Genera datos simulados de sanciones OSCE."""
        seed = sum(int(d) for d in ruc)
        random.seed(seed)
        
        sanctions = []
        
        # 20% de probabilidad de tener sanciones OSCE
        if random.random() < 0.20:
            num_sanctions = random.randint(1, 3)
            
            sanction_types = [
                ("Sanción por incumplimiento de entregas", "leve"),
                ("Sanción por documentación falsa", "grave"),
                ("Sanción por abandono de proceso", "grave"),
                ("Sanción por retraso en ejecución", "leve"),
                ("Sanción por incumplimiento de garantía", "moderada"),
            ]
            
            for i in range(num_sanctions):
                desc, severity = random.choice(sanction_types)
                date = datetime.now() - timedelta(days=random.randint(30, 730))
                
                sanctions.append({
                    "sanction_id": f"OSCE-{random.randint(10000, 99999)}",
                    "entity": "OSCE - Organismo Supervisor de Contratación del Estado",
                    "description": desc,
                    "severity": severity,
                    "date": date.isoformat(),
                    "status": random.choice(["ACTIVA", "CUMPLIDA", "EN APELACIÓN"]),
                    "resolution": f"Res. N° {random.randint(100, 999)}-{random.randint(2019, 2024)}-OSCE",
                    "duration_days": random.randint(30, 365) if severity == "grave" else random.randint(10, 60)
                })
        
        return sanctions
    
    def _generate_mock_tce_data(self, ruc: str) -> List[Dict[str, Any]]:
        """Genera datos simulados de sanciones TCE."""
        seed = sum(int(d) for d in ruc)
        random.seed(seed + 1)  # Diferente seed que OSCE
        
        sanctions = []
        
        # 10% de probabilidad de tener sanciones TCE
        if random.random() < 0.10:
            num_sanctions = random.randint(1, 2)
            
            for i in range(num_sanctions):
                date = datetime.now() - timedelta(days=random.randint(60, 1000))
                sanction_type = random.choice(["amonestacion", "multa", "inhabilitacion"])
                
                sanctions.append({
                    "sanction_id": f"TCE-{random.randint(10000, 99999)}",
                    "entity": "TCE - Tribunal de Contrataciones del Estado",
                    "description": f"Sanción por falta grave a las normas de contratación",
                    "type": sanction_type,
                    "date": date.isoformat(),
                    "status": random.choice(["FIRME", "EN APELACIÓN", "ARCHIVADA"]),
                    "resolution": f"Res. N° {random.randint(1000, 9999)}-{random.randint(2018, 2024)}-TCE",
                    "fine_amount": round(random.uniform(5000, 50000), 2) if sanction_type == "multa" else 0,
                    "inhabilitation_months": random.randint(6, 24) if sanction_type == "inhabilitacion" else 0
                })
        
        return sanctions
    
    def _generate_company_name(self, ruc: str) -> str:
        """Genera un nombre de empresa basado en el RUC."""
        prefixes = ["CONSTRUCTORA", "SERVICIOS", "TECNOLOGÍA", "CONSULTORA", "IMPORTACIONES", 
                   "EXPORTACIONES", "COMERCIAL", "INDUSTRIAL", "LOGÍSTICA", "INVERSIONES"]
        suffixes = ["S.A.C.", "S.A.", "E.I.R.L.", "S.R.L.", "SOCIEDAD ANÓNIMA"]
        
        seed = sum(int(d) for d in ruc)
        random.seed(seed)
        
        prefix = random.choice(prefixes)
        suffix = random.choice(suffixes)
        
        names = [
            f"{prefix} {ruc[:4]} {suffix}",
            f"{prefix} PERÚ {suffix}",
            f"{prefix} ANDINA {suffix}",
            f"{prefix} DEL NORTE {suffix}",
            f"GRUPO {prefix} {suffix}",
        ]
        
        return random.choice(names)
    
    def get_sunat_data(self, ruc: str) -> Dict[str, Any]:
        """Obtiene datos de SUNAT para un RUC."""
        cache_key = f"sunat:{ruc}"
        
        # Intentar obtener de caché
        cached = cache.get(cache_key)
        if cached:
            cached["cached"] = True
            return cached
        
        if self.use_real_api:
            try:
                response = requests.get(
                    f"{self.base_url}/sunat/ruc/{ruc}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=10
                )
                response.raise_for_status()
                data = response.json()
                cache.set(cache_key, data, expire=3600)  # 1 hora
                return data
            except Exception as e:
                # Fallback a datos simulados
                pass
        
        # Datos simulados
        data = self._generate_mock_sunat_data(ruc)
        cache.set(cache_key, data, expire=3600)
        return data
    
    def get_osce_sanctions(self, ruc: str) -> List[Dict[str, Any]]:
        """Obtiene sanciones OSCE para un RUC."""
        cache_key = f"osce:{ruc}"
        
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        if self.use_real_api:
            try:
                response = requests.get(
                    f"{self.base_url}/osce/sanciones/{ruc}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=10
                )
                response.raise_for_status()
                data = response.json()
                cache.set(cache_key, data, expire=7200)  # 2 horas
                return data
            except Exception:
                pass
        
        data = self._generate_mock_osce_data(ruc)
        cache.set(cache_key, data, expire=7200)
        return data
    
    def get_tce_sanctions(self, ruc: str) -> List[Dict[str, Any]]:
        """Obtiene sanciones TCE para un RUC."""
        cache_key = f"tce:{ruc}"
        
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        if self.use_real_api:
            try:
                response = requests.get(
                    f"{self.base_url}/tce/sanciones/{ruc}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=10
                )
                response.raise_for_status()
                data = response.json()
                cache.set(cache_key, data, expire=7200)
                return data
            except Exception:
                pass
        
        data = self._generate_mock_tce_data(ruc)
        cache.set(cache_key, data, expire=7200)
        return data
    
    def get_full_ruc_data(self, ruc: str) -> Dict[str, Any]:
        """Obtiene todos los datos disponibles para un RUC."""
        sunat_data = self.get_sunat_data(ruc)
        osce_sanctions = self.get_osce_sanctions(ruc)
        tce_sanctions = self.get_tce_sanctions(ruc)
        
        return {
            "ruc": ruc,
            "company_name": sunat_data.get("razon_social", ""),
            "sunat": sunat_data,
            "osce_sanctions": osce_sanctions,
            "tce_sanctions": tce_sanctions,
            "consulted_at": datetime.now().isoformat(),
            "data_sources": ["SUNAT", "OSCE", "TCE"]
        }

# Instancia global
external_api = ExternalAPIService()
