# Integración Perú API - Consulta RUC

## Registro
1. Ir a https://peruapi.com/
2. Crear cuenta gratuita
3. Obtener API Token desde el panel

## Planes
- **Free**: 100 consultas/día, 1,000/mes
- **Pro**: $9/mes - 5,000 consultas/mes
- **Business**: $29/mes - ilimitado

## Endpoint
```
GET https://peruapi.com/api/ruc/{ruc}?api_token={TOKEN}
```

## Respuesta
```json
{
  "ruc": "20529400790",
  "razon_social": "CONSTRUCTORA ZAMORA JARA SAC",
  "estado": "ACTIVO",
  "condicion": "HABIDO",
  "direccion": "AV. JOSE LEONARDO ORTIZ NRO. 430 INT. 304",
  "ubigeo": "140141",
  "departamento": "LIMA",
  "provincia": "LIMA",
  "distrito": "LA VICTORIA",
  "fecha_actualizacion": "2025-03-26 03:18:59",
  "mensaje": "OK",
  "code": "200"
}
```

## Configuración en Render
Variable de entorno:
```
PERUAPI_TOKEN=tu_token_aqui
```
