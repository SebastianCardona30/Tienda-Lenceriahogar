# Lencería de Hogar Ciudad Bonita — Tienda online

Tienda online de lencería y ropa de cama para Bucaramanga, Santander (Colombia).
Django + SQLite, 100 % con **costo $0**: solo herramientas gratuitas y de código abierto.
Todo el texto visible está en español de Colombia y los precios en pesos colombianos sin decimales ($89.900).

> Estado actual: **Fase 1 completa** (catálogo, búsqueda, filtros, ficha de producto e inicio).
> Sigue la Fase 2: carrito, ofertas, checkout y cuentas. Ver `PLAN.md`.

---

## Contenido rápido

1. [Ejecutar la tienda en tu PC](#ejecutar-la-tienda-en-tu-pc)
2. [Publicarla en Vercel (gratis)](#publicarla-en-vercel-gratis)
3. [Estructura del proyecto](#estructura-del-proyecto)
4. [Comandos útiles](#comandos-útiles)
5. [Variables de entorno (.env)](#variables-de-entorno-env)
6. [Avisos sobre la demo en Vercel](#avisos-sobre-la-demo-en-vercel)
7. [Dependencias y licencias (costo $0)](#dependencias-y-licencias-costo-0)

---

## Ejecutar la tienda en tu PC

**Requisitos:** Windows con Python 3.12 o superior ([python.org](https://www.python.org/downloads/), gratis — al instalar marca *Add Python to PATH*).

**Opción A — con un doble clic:** ejecuta `iniciar.bat`.
La primera vez crea el entorno virtual, instala las dependencias, prepara la base con datos
demo y abre la tienda en el navegador.

**Opción B — manual (igual en Mac/Linux):**

```bash
python -m venv venv
venv\Scripts\activate          # Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo     # carga 40 productos de ejemplo
python manage.py runserver
```

- Tienda: <http://127.0.0.1:8000/>
- Panel de administración: <http://127.0.0.1:8000/admin/> (crea tu usuario con `python manage.py createsuperuser`)
- Para borrar todo y empezar de cero: borra `db.sqlite3` y la carpeta `media/`, y repite `migrate` + `seed_demo`.

---

## Publicarla en Vercel (gratis)

Vercel sirve la tienda en internet con el **plan Hobby ($0)**. El proyecto ya trae la
configuración necesaria (`build.py`, `pyproject.toml`, `.python-version`).

**Pasos (solo la primera vez):**

1. Instala **Node.js** desde <https://nodejs.org> (gratuito; es necesario solo para la herramienta de publicación).
2. Crea tu cuenta gratuita en <https://vercel.com/signup>.
3. En una terminal, dentro de la carpeta del proyecto, inicia sesión una vez:
   ```bash
   npx vercel login
   ```

**Publicar (cualquier vez):** ejecuta `publicar-vercel.bat` — o desde la terminal:

```bash
npx vercel deploy --prod
```

Vercel instala las dependencias, ejecuta `build.py` (que migra, carga los datos demo,
recopila los estáticos y copia las imágenes) y te devuelve una dirección tipo
`https://tu-tienda.vercel.app`.

**Secretos en Vercel:** las variables se configuran en <https://vercel.com> → tu proyecto →
*Settings → Environment Variables*. La más importante es `SECRET_KEY` (una clave larga y aleatoria).
Las demás (correo SMTP, llaves de Wompi, etc.) son opcionales y llegan en fases posteriores.

---

## Estructura del proyecto

```
config/          Configuración de Django (settings, urls, wsgi/asgi)
core/            Configuración del negocio (SiteConfig), páginas institucionales, inicio
catalog/         Catálogo: categorías, productos, variantes, búsqueda, filtros, reseñas, combos
cart/            Carrito (en la Fase 2 quedará completo)
orders/ payments/ shipping/   Pedidos, pagos y envíos (Fases 2 y 3)
promotions/      Cupones y promociones
accounts/        Clientes y personal (Fase 2)
inventory/ notifications/ dashboard/   Inventario, avisos y panel (Fase 4)
templates/       Plantillas HTML (español)
static/          CSS propio, JavaScript (HTMX + Alpine.js locales), fuentes, imágenes
media/           Imágenes subidas (se ignora en git)
docs/            Especificación completa del proyecto
build.py         Construcción automática para Vercel
iniciar.bat      Arranque rápido en Windows
publicar-vercel.bat  Publicación en Vercel en un clic
PLAN.md          Avance por fases
```

---

## Comandos útiles

| Comando | Para qué |
|---|---|
| `python manage.py runserver` | Arrancar la tienda en local |
| `python manage.py migrate` | Aplicar cambios de base de datos |
| `python manage.py seed_demo` | Cargar/actualizar datos demo (no duplica) |
| `python manage.py test` | Ejecutar las pruebas automáticas |
| `python manage.py check` | Revisar que todo esté bien conectado |
| `python manage.py createsuperuser` | Crear usuario del panel admin |
| `python build.py` | Simular la construcción que corre Vercel al desplegar |

---

## Variables de entorno (.env)

Copia `.env.example` como `.env` y ajusta los valores. **Nunca subas `.env` a git.**

| Variable | Para qué |
|---|---|
| `SECRET_KEY` | Clave secreta de Django (obligatoria en producción) |
| `DEBUG` | `True` solo en local; en Vercel queda apagado |
| `ALLOWED_HOSTS` | Dominios permitidos (Vercel añade `*.vercel.app` solo) |
| `DATABASE_URL` | SQLite por defecto; para PostgreSQL basta cambiar esta variable |
| `EMAIL_*` | Correo (en desarrollo los correos se imprimen en consola) |
| `WOMPI_*` | Pasarela opcional (Fase 3; sin llaves, el método no se muestra) |

---

## Avisos sobre la demo en Vercel

El plan gratis de Vercel no tiene disco persistente, así que la demo funciona así:

- **Base de datos:** viaja "horneada" en el despliegue con los datos demo. Cada visita
  puede escribir en una copia temporal; si Vercel recicla la instancia, vuelve al estado inicial.
  Es perfecto para **mostrar la tienda**, no para vender todavía.
- **Imágenes:** las de ejemplo (SVG) se sirven desde el CDN de Vercel sin problema.
- **Para la tienda real** (pedidos, pagos y clientes que no se borren) hay dos caminos gratis:
  - Una base de datos externa gratuita (por ejemplo Neon) y poner su dirección en `DATABASE_URL`
    de Vercel — el código ya lo soporta, no hay que tocar nada más.
  - Un hosting con disco como PythonAnywhere o Render (gratis con límites), siguiendo la guía
    que quedará en el README de la Fase 5.

---

## Dependencias y licencias (costo $0)

Todas son gratuitas y de código abierto. Ninguna necesita tarjeta de crédito.

| Paquete | Licencia | Para qué |
|---|---|---|
| Django 5.2 | BSD-3-Clause | Framework web |
| dj-database-url | MIT | Leer `DATABASE_URL` (SQLite o PostgreSQL) |
| python-dotenv | BSD-3-Clause | Variables de entorno en `.env` |
| Pillow | MIT-CMU (HPND) | Imágenes: WebP y miniaturas |
| django-unfold | MIT | Panel admin en español y bonito |
| django-otp | MIT | Segundo factor para el admin (Fase 4) |
| django-axes | MIT | Bloqueo tras intentos fallidos de ingreso |
| rapidfuzz | MIT | Búsqueda tolerante a errores de ortografía |
| whitenoise | MIT | Sirve los estáticos sin servidor extra |

Frontend sin build ni CDNs: **HTMX** y **Alpine.js** se sirven desde `static/vendor/` con sus
licencias (HTMX BSD-3-Clause, Alpine.js MIT); las tipografías Playfair Display y Nunito Sans
son OFL (SIL Open Font License), auto-hospedadas en `static/fonts/`.
Chart.js (Fase 4) también se servirá desde `static/vendor/` con licencia MIT.

---

## Próximos pasos

- **Fase 2 — Compra:** carrito persistente, motor de ofertas y cupones, checkout en 3 pasos,
  envíos por municipio de Santander, cuentas de cliente y botón de WhatsApp.
- **Fase 3 — Pagos y pedidos:** pasarela simulada, comprobantes, reservas de stock y seguimiento.
- **Fase 4 — Administración:** dashboard con gráficas, inventario, importar/exportar CSV, roles y 2FA.
- **Fase 5 — Pulido:** SEO, textos legales, rendimiento, backups y guía completa de hosting.
