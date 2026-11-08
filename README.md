# Lencería de Hogar Ciudad Bonita — Tienda Online

Tienda online de lencería y ropa de cama para Bucaramanga, Santander (Colombia).
Desarrollada con **Python 3.12+ / Django 5.x**, arquitectura limpia con plantillas en servidor (sin SPA, sin paso de compilación de frontend) y **100 % costo $0**: solo librerías y herramientas gratuitas y de código abierto.

Todo el texto visible para las clientas está en español de Colombia (tuteo), con precios en pesos colombianos sin decimales (**$89.900**) con IVA incluido.

> **Estado del proyecto:** ✅ **Fases 0 a 5 completadas** (detalle en la tabla de abajo).
> Incluye catálogo, carrito, promociones, checkout, zonas de Santander, pagos (simulado, transferencia y Wompi sandbox), panel de administración, inventario, reportes CSV, roles de usuario, auditoría, 2FA, SEO completo y copias de seguridad.

### Estado de fases

| Fase | Contenido | Estado |
|---|---|---|
| 0 | Base del proyecto: paleta, tipografías, estructura de apps | ✅ |
| 1 | Catálogo, búsqueda, páginas institucionales, botón WhatsApp | ✅ |
| 2 | Carrito, checkout en 3 pasos, cuentas, envíos, ofertas | ✅ |
| 3 | Pagos (simulado, transferencia, Nequi/Daviplata, Wompi sandbox), reserva de stock, seguimiento, correos | ✅ |
| 4 | Dashboard, inventario con bitácora, importar/exportar CSV, reportes, roles, auditoría, ajustes | ✅ |
| 5 | SEO, sitemap, feed WhatsApp, textos legales, cookies, backup de BD | ✅ |
| Rediseño visual | Sistema visual completo (tokens, header/pie, portada, tienda y ficha, carrito y checkout, cuentas y panel, admin con tema claro/oscuro), auditado a 360/768/1280 px | ✅ |
| Seguridad y despliegue | Sesión por inactividad y al cerrar el navegador, cookies httpOnly/Secure, enlaces de recuperación de 1 hora, GitHub + despliegue automático en Vercel, revisión responsive (360/768/1280 px) | ✅ |

> 📌 **Regla:** al cerrar cada fase hay que actualizar la tabla "Estado de fases" de este README (junto con PLAN.md).

### Despliegue automático (GitHub → Vercel)

El código vive en [github.com/SebastianCardona30/Tienda-Lenceriahogar](https://github.com/SebastianCardona30/Tienda-Lenceriahogar) y el proyecto está vinculado a Vercel: **cada push a la rama `main` genera un despliegue automático** en <https://ciudad-bonita.vercel.app>. En local, subir cambios es simplemente `git push origin main`.

---

## Contenido

1. [Puesta en marcha local en tu PC](#puesta-en-marcha-local-en-tu-pc)
2. [Guía rápida para la dueña del negocio](#guía-rápida-para-la-dueña-del-negocio)
3. [Comandos de administración y mantenimiento](#comandos-de-administración-y-mantenimiento)
4. [Pasarelas de pago y Wompi](#pasarelas-de-pago-y-wompi)
5. [Opciones de publicación gratuita (Hosting $0)](#opciones-de-publicación-gratuita-hosting-0)
6. [Variables de entorno (.env)](#variables-de-entorno-env)
7. [Copias de seguridad (Backups)](#copias-de-seguridad-backups)
8. [Costos futuros al crecer el negocio](#costos-futuros-al-crecer-el-negocio)
9. [Dependencias y licencias (costo $0)](#dependencias-y-licencias-costo-0)

---

## Puesta en marcha local en tu PC

**Requisitos:** Windows, Mac o Linux con Python 3.12 o superior.

### Opción A — En Windows con un clic
Ejecuta el archivo `iniciar.bat`.
Crea el entorno virtual, instala las dependencias, aplica las migraciones, carga los datos de demostración y abre la tienda en tu navegador.

### Opción B — Manual en consola (Windows / Mac / Linux)

```bash
# 1. Crear y activar el entorno virtual
python -m venv venv
.\venv\Scripts\Activate.ps1       # En Windows PowerShell
# En Mac/Linux: source venv/bin/activate

# 2. Instalar dependencias gratuitas
pip install -r requirements.txt

# 3. Aplicar migraciones y crear datos de prueba
python manage.py migrate
python manage.py setup_roles     # Configura los 3 roles de administración
python manage.py seed_demo       # Carga 40 productos realistas, cupones y municipios

# 4. Crear usuario administrador
python manage.py createsuperuser

# 5. Arrancar el servidor
python manage.py runserver
```

- **Tienda pública:** <http://127.0.0.1:8000/>
- **Panel de administración:** <http://127.0.0.1:8000/admin/>
- **Sitemap para buscadores:** <http://127.0.0.1:8000/sitemap.xml>
- **Feed CSV para catálogo de WhatsApp:** <http://127.0.0.1:8000/catalogo/feed.csv>

---

## Guía rápida para la dueña del negocio

El panel de administración está diseñado en español, claro y accesible desde cualquier computador o celular:

### 1. ¿Cómo crear o editar un producto?
1. Entra a `/admin/` con tu usuario y contraseña.
2. En la sección **Catálogo**, haz clic en **Productos** → *Añadir producto*.
3. Completa el nombre, categoría, descripción y fotos.
4. En la parte inferior, añade las **Variantes** (tallas: Sencilla, Semidoble, Doble, Queen, King; color, precio de venta, costo y stock disponible).
5. Guarda los cambios. El producto aparecerá de inmediato en la tienda y en el buscador.

### 2. Cargar catálogos masivos con Excel (CSV)
- Entra a **Productos** en el panel y haz clic en el botón superior **Plantilla de ejemplo**.
- Llena las filas en Excel con los productos y variantes de tus proveedores.
- Usa el botón **Importar CSV** para subir el archivo. El sistema valida fila por fila antes de guardar, indicándote si hay algún error.

### 3. ¿Cómo gestionar y despachar pedidos?
1. En el menú, ve a **Pedidos**.
2. Verás los pedidos ordenados del más reciente al más antiguo con su estado:
   - **Pendiente de pago:** esperando que el cliente pague en línea o transfiera.
   - **Pago por verificar:** el cliente subió su comprobante de Nequi/Daviplata/banco.
   - **Pagado / En preparación:** listo para alistar en bodega y empacar.
   - **Enviado:** despachado con la transportadora o mensajero.
3. Para aprobar una transferencia: abre el pedido o la sección **Pagos**, revisa la foto/PDF del comprobante y presiona el botón **✓ Aprobar pago**. El pedido pasa automáticamente a *Pagado* y se notifica a la clienta por correo y WhatsApp.

### 4. Consultar métricas y reportes
- En la página principal del panel tienes el **Dashboard** con ventas del día, semana, mes, pedidos pendientes y alerta de stock bajo.
- Para descargar los números en Excel, ve a **Descargar reportes CSV** y elige el tipo (ventas por período, por producto, por categoría, por municipio, cupones usados o inventario valorizado).

---

## Comandos de administración y mantenimiento

| Comando | Descripción |
|---|---|
| `python manage.py runserver` | Inicia el servidor local de desarrollo |
| `python manage.py test` | Ejecuta la batería de más de 305 pruebas automáticas |
| `python manage.py check` | Verifica la integridad y configuración del sistema |
| `python manage.py seed_demo` | Carga o refresca datos de prueba realistas (idempotente) |
| `python manage.py setup_roles` | Crea o actualiza los roles Administradora, Empleado y Solo lectura |
| `python manage.py backup_db` | Realiza una copia de seguridad fechada de la BD y la carpeta media/ |
| `python manage.py cancel_expired_orders` | Cancela pedidos con reserva vencida y devuelve el stock al inventario |
| `python manage.py send_abandoned_cart_emails` | Envía recordatorios por correo a carritos abandonados |

---

## Pasarelas de pago y Wompi

El sistema cuenta con 3 modalidades de pago:

1. **Pasarela simulada local (para desarrollo y pruebas):**
   Activa por defecto (`PASARELA_SIMULADA=True`). Permite probar pagos Aprobados, Rechazados o Pendientes sin conexión a internet ni cobros reales.
2. **Transferencia manual / Nequi / Daviplata:**
   Muestra los datos bancarios configurados en el panel. La clienta sube su comprobante y el equipo lo aprueba con un solo clic.
3. **Wompi Bancolombia (opcional):**
   - **Sandbox gratuito:** Wompi ofrece credenciales de prueba gratuitas para simular tarjetas, PSE, Nequi y DaviPlata.
   - **Producción:** En producción Wompi descuenta una comisión por cada transacción exitosa.
   - **Configuración:** Para activar Wompi, basta con definir en el archivo `.env`:
     ```env
     WOMPI_PUBLIC_KEY=pub_prod_... (o pub_test_...)
     WOMPI_PRIVATE_KEY=prv_prod_... (o prv_test_...)
     WOMPI_EVENTS_KEY=...
     WOMPI_INTEGRITY_SECRET=...
     ```
   - Si no se configuran llaves de Wompi, la tienda oculta automáticamente el botón de Wompi y opera sin errores. Nunca se almacenan números de tarjetas en la base de datos.

---

## Opciones de publicación gratuita (Hosting $0)

### Opción 1: PythonAnywhere (Recomendada para producción con SQLite)
- **Plan gratuito:** Ofrece 512 MB de almacenamiento y **disco persistente**. La base SQLite y las fotos subidas a `media/` no se borran al reiniciar.
- **Configuración:**
  1. Crea una cuenta gratuita en [pythonanywhere.com](https://www.pythonanywhere.com).
  2. Sube el código mediante git o archivo comprimido.
  3. Crea un virtualenv con Python 3.12 e instala `requirements.txt`.
  4. Configura el archivo WSGI apuntando a `config.wsgi.application`.
  5. En la pestaña *Tasks*, puedes programar `python manage.py cancel_expired_orders` diariamente a costo $0.

### Opción 2: Vercel (la usamos en producción)
- **Despliegue automático:** el repo de GitHub está vinculado al proyecto de Vercel; cada push a `main` genera un despliegue solo (build con `build.py`: migrate + seed_demo + collectstatic).
- Despliegue manual con `publicar-vercel.bat` o `npx vercel --prod`.
- La tienda queda en `https://tu-proyecto.vercel.app`.
- **Nota técnica:** Vercel usa funciones serverless de solo lectura. Para operar una tienda con ventas reales en Vercel, conecta una base PostgreSQL gratuita (ej. Neon o Supabase) configurando `DATABASE_URL` en las variables de entorno de Vercel.

### Opción 3: Render (Advertencia sobre disco efímero)
- El plan gratuito de Render apaga el servicio tras 15 minutos de inactividad y su disco es efímero (al reiniciarse se restablece al estado del último commit).
- Úsalo solo para demos temporales con datos generados por `seed_demo`.

---

## Variables de entorno (.env)

Copia `.env.example` a `.env` para personalizar tu entorno:

```env
# Clave secreta de Django (obligatoria y aleatoria en producción)
SECRET_KEY=clave-larga-y-aleatoria

# Modo de depuración (True en local, False en producción)
DEBUG=True

# Dominios autorizados separados por coma
ALLOWED_HOSTS=localhost,127.0.0.1,.vercel.app

# Base de datos (SQLite WAL local o PostgreSQL remoto)
DATABASE_URL=sqlite:///db.sqlite3

# Correo electrónico (en desarrollo imprime en consola)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=

# Wompi (opcional)
WOMPI_PUBLIC_KEY=
WOMPI_PRIVATE_KEY=
WOMPI_EVENTS_KEY=
WOMPI_INTEGRITY_SECRET=

# Analítica opcional (solo carga si la clienta acepta el banner de cookies)
GA4_MEASUREMENT_ID=
META_PIXEL_ID=
```

---

## Copias de seguridad (Backups)

Para resguardar la base de datos y todas las imágenes de productos y comprobantes:

```bash
python manage.py backup_db
```

Crea una carpeta fechada en `backups/backup_YYYYMMDD_HHMMSS/` conteniendo:
- El archivo `db.sqlite3` (y sus archivos auxiliares de registro WAL).
- La carpeta `media/` con todas las fotos de catálogo y comprobantes de pago.

Puedes guardar estas carpetas en Google Drive, OneDrive o una memoria USB para máxima seguridad.

---

## Costos futuros al crecer el negocio

El proyecto está diseñado para funcionar al **100 % sin costo inicial**. Cuando la tienda empiece a generar ventas constantes, estos son los únicos costos opcionales recomendados para crecer:

1. **Nombre de dominio propio:** Un dominio `.com` o `.com.co` (aprox. $40.000 a $80.000 COP al año).
2. **Comisión de pasarela Wompi:** Solo se cobra un porcentaje sobre las ventas cobradas exitosamente (sin costo de mantenimiento mensual).
3. **Hosting dedicado o VPS:** Si el catálogo supera miles de visitas diarias, un servidor VPS económico en Hetzner o DigitalOcean ($4 a $6 USD/mes) o una base de datos PostgreSQL administrada.

---

## Dependencias y licencias (costo $0)

Todas las dependencias son de código abierto y uso comercial permitido:

| Paquete | Licencia | Propósito |
|---|---|---|
| Django 5.2 | BSD-3-Clause | Framework web robusto y seguro |
| dj-database-url | MIT | Configuración unificada de base de datos |
| python-dotenv | BSD-3-Clause | Carga segura de variables de entorno |
| Pillow | MIT-CMU (HPND) | Optimización y conversión de imágenes WebP |
| django-unfold | MIT | Panel de administración moderno en español |
| django-otp | MIT | Autenticación en dos pasos (2FA) para administradores |
| django-axes | MIT | Protección contra ataques de fuerza bruta en logins |
| rapidfuzz | MIT | Búsqueda tolerante a errores ortográficos |
| whitenoise | MIT | Distribución eficiente de archivos estáticos |
| HTMX 2.0 | BSD-2-Clause | Interactividad ligera sin frameworks pesados (en `static/vendor/`) |
| Alpine.js 3.x | MIT | Lógica de selectores y galerías en cliente (en `static/vendor/`) |
| Chart.js 4.x | MIT | Gráficas del panel de administración (en `static/vendor/`) |
| Playfair & Nunito | OFL (SIL) | Tipografías auto-hospedadas (en `static/fonts/`) |
