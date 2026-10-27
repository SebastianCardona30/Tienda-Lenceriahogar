# Lencería de Hogar Ciudad Bonita

Tienda online de ropa de cama y artículos para el hogar en **Bucaramanga, Santander (Colombia)**.
Construida con Django, 100 % con herramientas gratuitas: **costo $0** para desarrollar, probar y publicar.

## Requisitos

- Python 3.12 o superior (probado con Python 3.14)
- Nada más: la base de datos es SQLite y viene incluida con Python.

## Instalación local (Windows)

```powershell
cd proyectolencceriahogar
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py runserver
```

Abre http://127.0.0.1:8000/ y el panel en http://127.0.0.1:8000/admin/ (crea tu usuario con `python manage.py createsuperuser`).

## Instalación local (Mac / Linux)

```bash
cd proyectolencceriahogar
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

## Comandos útiles

| Comando | Para qué sirve |
| --- | --- |
| `python manage.py runserver` | Arrancar la tienda en desarrollo |
| `python manage.py test` | Correr las pruebas automáticas |
| `python manage.py migrate` | Aplicar cambios de base de datos |
| `python manage.py createsuperuser` | Crear usuario para el panel admin |
| `python manage.py seed_demo` | Cargar productos y ofertas de ejemplo (Fase 1) |
| `python manage.py backup_db` | Copia de seguridad de base de datos y fotos (Fase 5) |

## Variables de entorno (.env)

Copia `.env.example` a `.env`. Ningún secreto va en el código.
Incluye: `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `DATABASE_URL` (SQLite por defecto;
para PostgreSQL solo cambia esta variable), correo SMTP opcional y las llaves de
Wompi (opcionales: sin ellas el método se oculta).

## Integraciones externas: siempre opcionales

- **Pagos:** pasarela simulada local (sin internet) y Wompi sandbox (gratis para pruebas).
  En producción Wompi cobra comisión por transacción: ese costo solo aparece cuando vendas de verdad.
- **Correo:** en desarrollo se imprime en consola; en producción puedes usar SMTP gratis (p. ej. Gmail).
- **Sin** Cloudinary, Redis, Celery ni Docker: imágenes en disco, tareas como comandos.

## Licencias de las dependencias (todas gratuitas)

| Paquete | Licencia |
| --- | --- |
| Django | BSD-3-Clause |
| dj-database-url | MIT |
| python-dotenv | BSD-3-Clause |
| Pillow | MIT-CMU |
| django-unfold | MIT |
| django-otp | MIT |
| django-axes | MIT |
| rapidfuzz | MIT |
| whitenoise | MIT |
| HTMX (static/vendor) | BSD-2-Clause |
| Alpine.js (static/vendor) | MIT |
| Chart.js (static/vendor) | MIT |
| Playfair Display y Nunito Sans (static/fonts) | SIL OFL 1.1 |

## Nota importante

Los textos legales (términos, privacidad, retracto) son plantillas y deben
revisarse con un abogado o contador antes de vender.
