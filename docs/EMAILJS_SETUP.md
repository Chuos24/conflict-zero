# EmailJS Setup - Conflict Zero

## Paso 1: Crear cuenta EmailJS

1. Ve a https://www.emailjs.com/
2. Click "Get Started" → Sign up con Google
3. Confirmar email

## Paso 2: Crear Email Service

1. En el dashboard, click "Email Services" → "Add New Service"
2. Selecciona tu proveedor (Gmail recomendado)
3. Conecta tu cuenta de Gmail
4. **Guarda el Service ID** (ej: `service_abc123`)

## Paso 3: Crear Email Template

1. Click "Email Templates" → "Create New Template"
2. Nombre: "Fundador Application"
3. Configura:

**To:** `contacto@czperu.com`
**From:** `{{from_email}}`
**Subject:** `Nueva Aplicación Fundador - {{company_name}}`

**Body (HTML):**
```html
<h2 style="color: #C5A059;">Nueva Aplicación Programa Fundador</h2>

<table style="font-family: Inter, sans-serif; border-collapse: collapse;">
  <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Referencia:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{{reference}}</td></tr>
  <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Empresa:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{{company_name}}</td></tr>
  <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>RUC:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{{ruc}}</td></tr>
  <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Representante:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{{contact_name}}</td></tr>
  <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Email:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{{contact_email}}</td></tr>
  <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Teléfono:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{{contact_phone}}</td></tr>
  <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Volumen Anual:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{{annual_volume}}</td></tr>
  <tr><td style="padding: 8px;"><strong>Subcontratistas:</strong></td><td style="padding: 8px;">{{subcontractor_count}}</td></tr>
</table>

<p style="margin-top: 20px; color: #666; font-size: 12px;">
  Enviado el {{submitted_at}}<br>
  Conflict Zero - Estándar de Verificación Institucional
</p>
```

4. **Guarda el Template ID** (ej: `template_xyz789`)

## Paso 4: Obtener Public Key

1. Ve a "Account" → "General"
2. Copia tu **Public Key**

## Paso 5: Configurar en el código

Abre `founders.html` y reemplaza:

```javascript
// Línea ~1050
emailjs.init('YOUR_PUBLIC_KEY');

// Línea ~990
await emailjs.send(
    'service_cz_default',  // ← Tu Service ID
    'template_founder_app', // ← Tu Template ID
    templateParams
);
```

## Paso 6: Verificar dominio (opcional pero recomendado)

1. En "Account" → "Security"
2. Agrega `czperu.com` a dominios permitidos

## Límites Gratis

- 200 emails/mes
- Suficiente para 200 aplicaciones fundador

## Test

1. Abre https://czperu.com/founders.html
2. Llena con datos de prueba
3. Submit
4. Revisa contacto@czperu.com

---

**¿Necesitas ayuda con algún paso?** Dime en qué te atascaste.
