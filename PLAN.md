# PLAN.md — Plan por fases (sección 21 de la especificación)

Marca cada casilla `[x]` al terminar. Si pierdes el hilo, relee AGENTS.md y continúa con la primera tarea sin marcar.

## Fase 0 — Memoria del proyecto, estructura y diseño base
- [x] Guardar prompt completo en docs/ESPECIFICACION.md
- [x] Crear AGENTS.md y PLAN.md
- [x] Inicializar git (commit al final de la fase)
- [x] Estructura de carpetas, venv, requirements.txt, .env.example, .gitignore
- [x] Proyecto Django `config` con settings (es-co, America/Bogota, SQLite WAL vía DATABASE_URL, estáticos, whitenoise, caché, correo consola)
- [x] Crear las 11 apps (esqueleto) + usuario personalizado en accounts
- [x] Modelo base: SiteConfig singleton en core (datos del negocio, WhatsApp, IVA, logo) + admin en español con unfold
- [x] Diseño base: variables CSS, tipografías auto-hospedadas, layout, header, footer, favicon, logo SVG
- [x] Páginas institucionales placeholder (quienes-somos, contacto, etc.) y 404/500 amigables
- [x] Smoke test: check, migrate, prueba de home + SiteConfig, runserver OK

## Fase 1 — Catálogo
- [ ] Categorías con subcategorías, imagen, orden y SEO
- [ ] Proveedor, Producto y Variante (SKU) con estados, precios, stock, fotos múltiples
- [ ] Conversión a WebP y miniaturas con Pillow; marcadores SVG de posición
- [ ] Inicio completa (hero, categorías, ofertas semana con cuenta regresiva, más vendidos, novedades, banner bordados, combos, beneficios, reseñas, suscripción, footer)
- [ ] Listado de tienda con filtros laterales (categoría, talla, color, material, precio, oferta, stock, calificación, marca, hilos, gramaje), chips, orden y "cargar más" (HTMX)
- [ ] Ficha de producto: galería, selectores, precio, WhatsApp, envío por municipio, pestañas, reseñas, relacionados, schema.org
- [ ] Búsqueda normalizada con sinónimos y tolerancia a errores; autocompletado HTMX; registro de búsquedas sin resultados
- [ ] Comando seed_demo (8 categorías, 40 productos, proveedores, ofertas, imágenes placeholder)

## Fase 2 — Compra
- [ ] Carrito persistente en sesión (drawer + página), fusión al iniciar sesión, cupones, envío por municipio, barra de envío gratis, resumen por WhatsApp
- [ ] Motor de ofertas: descuentos por producto/variante/categoría, cupones, 2x1/3x2, combos, volumen, venta relámpago, envío gratis desde monto
- [ ] Checkout en 3 pasos (datos + mayor de edad + términos; envío Santander con municipios y zonas; pago)
- [ ] Zonas de envío configurables + lista oficial de municipios de Santander
- [ ] Cuentas: registro/ingreso, mis pedidos, direcciones, lista de deseos, mis datos, recuperar contraseña, borrado Habeas Data; compra como invitado siempre
- [ ] Botón flotante de WhatsApp y mensajes wa.me prellenados

## Fase 3 — Pagos y pedidos
- [ ] Pasarela simulada local (Aprobado/Rechazado/Pendiente) con misma interfaz que la real
- [ ] Transferencia/Nequi/Daviplata manual con comprobante (imagen/PDF validado), aprobación con un clic
- [ ] Reserva de stock (15 min checkout / X horas transferencia) + comandos cancel_expired_orders y release_stock_reservations
- [ ] Estados de pedido con historial; seguimiento público por número + celular
- [ ] Correos de marca por plantilla (consola en dev) + aviso interno por email/WhatsApp; send_abandoned_cart_emails
- [ ] Wompi sandbox opcional: endpoints y firma según documentación vigente, webhook idempotente con verificación, ocultar si no hay llaves

## Fase 4 — Administración
- [ ] Dashboard con métricas y gráficas (Chart.js local)
- [ ] Inventario: movimientos, alertas, valorizado, órdenes de compra
- [ ] Importar/exportar CSV de productos con plantilla y validación por fila
- [ ] Reportes exportables a CSV (ventas, producto, categoría, proveedor, municipio, cupones, inventario)
- [ ] Roles (Administradora/Empleado/Solo lectura), auditoría y 2FA con django-otp
- [ ] Ajustes del negocio: métodos de pago, datos bancarios, zonas, textos legales, plantillas de correo

## Fase 5 — Pulido
- [ ] SEO: títulos/descripciones, URLs limpias, sitemap.xml, robots.txt, Open Graph, schema.org
- [ ] Analítica opcional (GA4/Meta Pixel con consentimiento) y feed CSV para WhatsApp Business
- [ ] Textos legales completos con nota de revisión profesional; banner de cookies; PQRS; retracto 5 días hábiles
- [ ] Rendimiento (Lighthouse móvil >= 90), accesibilidad AA, pruebas completas
- [ ] Comando backup_db + README completo: instalación, variables, Wompi, PythonAnywhere, Render (advertencia), costos futuros, guía para la dueña

## Decisiones anotadas (opción más simple y segura)
- Python del equipo: 3.14.7 (no hay 3.12 instalada); Django 5.2.18 instalado y verificado funcionando sobre 3.14. Spec dice 3.12: se usa la versión disponible porque el código no depende de 3.12 en particular.
- git no estaba instalado en la máquina; se instaló Git 2.56.0.3 (gratuito) con winget para poder cumplir los commits por fase.
