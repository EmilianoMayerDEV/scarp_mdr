# Buscador de clientes · Mayer Digital

Panel web local para encontrar **negocios sin página web** y contactarles de forma **semiautomática**:

1. **Busca** negocios por sector y ciudad en **Google Places** y **OpenStreetMap**, y elimina duplicados.
2. **Comprueba si tienen web**: la de su ficha, una búsqueda de su nombre en internet (Brave Search, opcional) y dominios típicos (`nombre.es`, `nombre.com`).
3. **Prepara un mensaje personalizado** (menciona sus reseñas, sus redes o que su web no carga).
4. **Tú lo revisas y lo envías con un clic**:
   - si tiene **email** → se envía desde tu correo de Hostinger (o se abre en tu programa de correo);
   - si no, y tiene **móvil** → se abre **WhatsApp** con el mensaje ya escrito;
   - si solo tiene **fijo** → botón para **llamar**.
5. Lleva el **registro** de a quién escribiste, un **límite diario**, una lista de **seguimiento** (sin respuesta tras X días) y una lista de **no contactar**.

## Por qué no es 100 % automático

- **Ley (LSSI, art. 21):** en España no se pueden enviar comunicaciones comerciales electrónicas no solicitadas, tampoco a empresas. Revisar y enviar uno a uno, poco volumen, mensaje personalizado y opción clara de baja reduce mucho el riesgo, pero **consulta con un asesor** si vas a escalar.
- **WhatsApp** bloquea los números que envían mensajes automáticos a desconocidos.
- **Tu dominio es nuevo**: muchos correos de golpe lo mandan a listas negras. Por eso hay un `LIMITE_DIARIO` (15 por defecto).

Cuando alguien responda «no», márcalo como **no_contactar** y el panel no te dejará volver a escribirle.

## Instalación

**Atajo:** en Windows haz doble clic en `iniciar.bat` (en Mac/Linux, `./iniciar.sh`). La primera vez instala todo y crea el `.env`; ciérralo, rellena el `.env` y vuelve a abrirlo.

O paso a paso:


Necesitas **Python 3.10 o superior** ([python.org](https://www.python.org/downloads/); en Windows marca *Add Python to PATH*).

```bash
git clone https://github.com/EmilianoMayerDEV/scarp_mdr.git
cd scarp_mdr
python -m venv .venv
```

Activa el entorno e instala:

- **Windows:** `.venv\Scripts\activate`
- **Mac/Linux:** `source .venv/bin/activate`

```bash
pip install -r requirements.txt
```

Copia `.env.example` como `.env` y rellénalo (ver abajo). Luego:

```bash
python app.py
```

Se abrirá **http://127.0.0.1:5000** en tu navegador. Solo funciona en tu ordenador (no es accesible desde internet).

## Configuración (`.env`)

| Variable | Para qué |
|---|---|
| `GOOGLE_PLACES_API_KEY` | Buscar en Google Maps. Sin ella solo se usa OpenStreetMap. |
| `BRAVE_API_KEY` | Buscar el nombre del negocio en internet. Opcional, pero mejora mucho la verificación. |
| `FIRMA_*` | Tu nombre, empresa, web y teléfono para la firma de los mensajes. |
| `SMTP_USUARIO` / `SMTP_CONTRASENA` | Tu correo de Hostinger (p. ej. `hola@mayerdigital.website`) para enviar los emails desde el panel. Sin esto, se abren en tu programa de correo. |
| `LIMITE_DIARIO` | Máximo de mensajes al día (email + WhatsApp). |
| `DIAS_SEGUIMIENTO` | Días sin respuesta tras los que un negocio pasa a «Seguimiento». |

### Clave de Google Places

1. Entra en [console.cloud.google.com](https://console.cloud.google.com), crea un proyecto y activa la facturación (pide tarjeta).
2. En **APIs y servicios → Biblioteca**, activa **Places API (New)**.
3. En **APIs y servicios → Credenciales**, crea una **clave de API** y restríngela a *Places API (New)*.
4. **Importante:** en **Cuotas** pon un límite diario de peticiones y crea una **alerta de presupuesto**, para no llevarte sorpresas. Google incluye un uso gratuito mensual; revisa los precios actuales de *Text Search* en su web.

Cada búsqueda (sector + ciudad) hace como máximo 3 peticiones y devuelve hasta 60 negocios.

### Clave de Brave Search (opcional)

Regístrate en [brave.com/search/api](https://brave.com/search/api/), elige un plan (revisa si hay uno gratuito en ese momento) y copia la clave. Se hace una consulta por negocio.

### Correo de Hostinger

Usa el mismo email y contraseña con los que entras al webmail. Servidor `smtp.hostinger.com`, puerto `465`. Con `SMTP_COPIA_A_MI=si` recibes una copia de cada correo enviado.

## Uso

1. Escribe un **sector** (hay sugerencias: peluquerías, restaurantes, talleres mecánicos…) y una **ciudad**, y pulsa **Buscar negocios**.
2. Espera a que termine la verificación (barra de progreso).
3. Pestañas:
   - **Sin web**: tus objetivos principales.
   - **Web caída**: tienen web en su ficha pero no carga. También son buenos clientes.
   - **Revisar**: algo parecido a su web apareció en internet; ábrelo y, si no es suya, cambia el estado con ↻ o descártalo.
   - **Seguimiento**: contactados hace más de `DIAS_SEGUIMIENTO` días sin marcar como «respondio».
4. Pulsa **Preparar**, revisa el mensaje, personalízalo y pulsa **Enviar email** / **Abrir WhatsApp**.
5. Cuando te respondan, cambia el estado a **respondio** (o **no_contactar** si no quieren).

Los sectores de OpenStreetMap se definen en `buscador/fuentes/osm.py` (`SECTORES`). Google acepta cualquier texto.
Los textos de los mensajes están en `buscador/mensajes.py`.
**Exportar CSV** descarga todo para abrirlo en Excel.

Los datos se guardan en `datos/negocios.db` (no se sube a GitHub).

**Datos de Google (30 días):** las condiciones de Google Maps Platform no permiten guardar sus datos de forma
permanente. Al abrir el panel y antes de cada búsqueda, el buscador borra lo que vino de Google hace más de 30 días:
los negocios que no contactaste se eliminan (vuelve a buscar para tenerlos actualizados) y de los que sí contactaste
se conserva solo tu historial (nombre, contacto usado, estado, notas e identificador de Google).

## Pruebas

```bash
pip install pytest
python -m pytest
```

## Webs modelo por sector

En `modelos/webs/` hay una web de ejemplo para cada uno de los 27 sectores del buscador (abre `modelos/webs/index.html`).
Sirven para enseñar a cada negocio cómo se vería su página. Los negocios, teléfonos y reseñas son **ficticios**,
y los recuadros de color marcan dónde irían las fotos reales del cliente.

- Textos, precios y colores: `modelos/contenido.py`
- Diseño: `modelos/generar.py`
- Para regenerarlas tras un cambio: `python modelos/generar.py`

Están publicadas en **https://mayerdigital.website/modelos/** (una carpeta por sector, p. ej. `/modelos/peluquerias/`),
y el buscador añade automáticamente el enlace del sector en cada mensaje (`MODELOS_URL` en el `.env`; vacío = sin enlace).
Para actualizar las publicadas tras editar el contenido:

```bash
python modelos/generar.py --publicar ../mayerdigital-website/modelos
```

y sube los cambios del repo de la web. Llevan `noindex` para que Google no las muestre como negocios reales.

Iconos: [Lucide](https://lucide.dev) (licencia ISC).
