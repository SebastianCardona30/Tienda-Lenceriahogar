# AGENTS.md — Lencería de Hogar Ciudad Bonita

**Instrucción clave:** al iniciar cada sesión o fase, lee AGENTS.md, PLAN.md y la sección relevante de docs/ESPECIFICACION.md.

## Qué es
Tienda online de lencería y ropa de cama en Bucaramanga, Santander (Colombia). Español de Colombia, tuteo, moneda COP.

## Regla maestra: COSTO $0
Solo librerías/herramientas gratuitas y de código abierto, anotadas en README con su licencia.
Integraciones externas (pasarela, analítica, correo) son OPCIONALES: el sistema debe funcionar completo sin ellas.

## Stack (decidido, no cambiar)
- Python 3.12+ / Django 5.x, plantillas HTML en servidor (sin SPA, sin build de frontend).
- SQLite WAL por defecto vía DATABASE_URL; sin funciones exclusivas de PostgreSQL.
- CSS propio con variables (sin compilación), HTMX + Alpine.js + Chart.js servidos desde static/vendor/ (nunca CDN en runtime).
- Pillow (WebP y miniaturas), media/ en disco. django-unfold (admin en español), django-otp, django-axes, rapidfuzz, python-dotenv, dj-database-url, whitenoise.
- Sin Celery/Redis/Docker: tareas = comandos manage.py ejecutados con cron o a mano.
- Correos: consola en desarrollo; SMTP opcional por .env. Secretos solo en .env (nunca en código).

## Paleta CSS (valores fijos)
--ciruela #5B2A86 · --purpura #8A4FBF · --lavanda #F1E8FA · --rosa-cta #C2185B · --rosa-suave #FBD5E5
--crema #FFF8FB · --texto #2A2230 · --texto-2 #6A6173 · --borde #E7DCEE · --oferta #E0245E
--exito #2E9E6B · --aviso #F2A516 · --error #D93F3F
Tipografías: títulos "Playfair Display" (600/700); texto "Nunito Sans" (400/600/700), auto-hospedadas en static/fonts con fallback de sistema.

## Convenciones
- Comentarios y todo texto visible para el usuario: español de Colombia. Código: identificadores en inglés, comentarios en español.
- Apps Django: core, catalog, cart, orders, payments, shipping, promotions, accounts, inventory, notifications, dashboard.
- Moneda COP sin decimales ($89.900) con filtro `cop` (core.templatetags.format_tags). IVA incluido y configurable.
- Marcadores configurables en el admin para datos no inventados ([NIT], [DIRECCIÓN], [TELÉFONO], [EMAIL]).
- Mobile-first (probar 360, 768, 1280 px), AA, objetivos táctiles 44 px, bordes 10–16 px, transiciones 150–250 ms.
- Pruebas automáticas por área; al cerrar fase: `manage.py check`, `manage.py test`, y verificar que runserver arranca.
- Commit por fase con mensaje claro en español. Actualizar PLAN.md siempre.

## Comandos (Windows; en Mac/Linux igual sin .\ y con python3)
- Crear entorno: `python -m venv venv` · Activar: `.\venv\Scripts\Activate.ps1` · Dependencias: `.\venv\Scripts\pip install -r requirements.txt`
- Servidor: `.\venv\Scripts\python manage.py runserver`
- Migraciones: `.\venv\Scripts\python manage.py migrate`
- Admin: `.\venv\Scripts\python manage.py createsuperuser`
- Pruebas: `.\venv\Scripts\python manage.py test`
- Datos demo: `.\venv\Scripts\python manage.py seed_demo` · Backup: `manage.py backup_db`

## Recordatorio de contexto (modelos con poca memoria)
Si el plan se perdió: relee PLAN.md, marca lo hecho y sigue con la siguiente tarea sin pedir confirmaciones.
