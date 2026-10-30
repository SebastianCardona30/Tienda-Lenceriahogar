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

## Fase 1 — Catálogo ✅ (25/25 pruebas OK)
- [x] Categorías con subcategorías, imagen, orden y SEO — menú **interactivo**: desplegables en escritorio, panel lateral con acordeón en celular (pedido del usuario)
- [x] Proveedor, Producto y Variante (SKU) con estados, precios, stock, fotos múltiples — reseñas, combos, sinónimos y búsquedas sin resultados también en models
- [x] Conversión a WebP y miniaturas con Pillow; marcadores SVG de posición (seed genera 2 fotos SVG por producto)
- [x] Inicio completa (hero, categorías con imagen, ofertas semana con cuenta regresiva vía Alpine, más vendidos, novedades, banner bordados, combos, beneficios, reseñas, suscripción al boletín, footer)
- [x] Listado de tienda con filtros laterales (categoría, talla, color swatches, material, precio, oferta, stock, calificación, marca, hilos, gramaje), chips removibles, orden y "cargar más" (HTMX) + panel deslizable en celular
- [x] Ficha de producto: galería, selectores de variante (Alpine, precio/stock en vivo), WhatsApp prellenado, pestañas, reseñas con formulario, relacionados, vistos recientemente, schema.org JSON-LD, barra de compra fija en celular
- [x] Búsqueda normalizada con sinónimos y tolerancia a errores (rapidfuzz); autocompletado HTMX; registro de búsquedas sin resultados en admin
- [x] Comando seed_demo idempotente (8 categorías con subcategorías, 40 productos, variantes, 4 proveedores, 8 reseñas, 3 combos, 8 sinónimos, 3 cupones, ofertas_hasta)
- [x] Carrito: solo stub `cart:agregar` informativo (el real llega en Fase 2)
- [x] Verificación: `manage.py check` OK, 25/25 pruebas, home/tienda/categoría/búsqueda/autocomplete responden 200

## Fase 2 — Compra
- [x] Carrito persistente en sesión (drawer + página), fusión al iniciar sesión, cupones, envío por municipio, barra de envío gratis, resumen por WhatsApp (Paso 3: cart/servicios.py, 28 pruebas; la fusión se conecta al login en el Paso 4)
- [x] Motor de ofertas: descuentos por producto/variante/categoría, cupones, 2x1/3x2, combos, volumen, venta relámpago, envío gratis desde monto (Paso 2: promotions/engine.py, cálculo en servidor, 27 pruebas)
- [x] Checkout en 3 pasos (datos + mayor de edad + términos; envío Santander con municipios y zonas; pago) (Paso 5: orders con Pedido/ItemPedido, precios congelados, descuento de stock en transacción y confirmación; reserva de 15 min y pago simulado llegan en Fase 3)
- [x] Zonas de envío configurables + lista oficial de municipios de Santander (Paso 1: 87 municipios, seed_municipios, 9 pruebas)
- [x] Cuentas: registro/ingreso, mis pedidos, direcciones, lista de deseos, mis datos, recuperar contraseña, borrado Habeas Data; compra como invitado siempre (Paso 4: accounts con fusión del carrito al ingresar, 32 pruebas)
- [x] Botón flotante de WhatsApp y mensajes wa.me prellenados (Paso 6: el flotante viaja con mensaje según la página —inicio, tienda, categoría, búsqueda, ofertas, combos, ficha de producto y carrito—; los botones "Comprar por WhatsApp" y "Enviar mi pedido" ya existían)

## Fase 3 — Pagos y pedidos
- [x] Pasarela simulada local (Aprobado/Rechazado/Pendiente) con misma interfaz que la real (Paso 1: app payments, pantalla con formato de monto + referencia, `orders.servicios.cambiar_estado`, admin de Pago, 13 pruebas; se oculta con PASARELA_SIMULADA=0 o con llaves WOMPI_* en .env)
- [x] Transferencia/Nequi/Daviplata manual con comprobante (imagen/PDF validado), aprobación con un clic (Paso 2: datos de cuenta como marcadores en SiteConfig, subida con validación real Pillow/PDF y 5 MB, pedido pasa a "Pago por verificar", acciones del admin aprueban/rechazan en un clic, 12 pruebas; el medio se oculta del checkout si no tiene datos)
- [x] Reserva de stock (15 min checkout / X horas transferencia) + comandos cancel_expired_orders y release_stock_reservations (Paso 3: Pedido.reserva_hasta + stock_devuelto, devolución idempotente en cambiar_estado, horas de reserva configurables en SiteConfig, comandos con --simular y margen de seguridad, 10 pruebas; al pagar se libera la reserva)
- [x] Estados de pedido con historial; seguimiento público por número + celular (Paso 4: vista pública /seguimiento/ que valida número + últimos 10 dígitos del celular sin cuenta, línea de tiempo del historial, enlace desde confirmación y pie de página, 6 pruebas; HistorialPedido ya existía desde Fase 2)
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

## Puesta en línea en Vercel (pedido del usuario — 27/10/2026)
- [x] Adaptar settings.py para Vercel: hosts `*.vercel.app`, DEBUG apagado, CSRF, base SQLite horneada copiada a /tmp en el arranque y media/ servido desde el bundle
- [x] build.py (ejecuta Vercel en cada despliegue): migrate + seed_demo + collectstatic + copia media/ → public/media
- [x] pyproject.toml con `[tool.vercel.scripts]` y `.python-version` (3.12)
- [x] iniciar.bat (arranque local completo en un clic) y publicar-vercel.bat (despliegue en un clic)
- [x] README.md completo: instalación, despliegue en Vercel, variables de entorno y licencias (costo $0)
- [x] Verificación local: build.py en limpio OK, 25/25 pruebas, simulación VERCEL=1 (home/tienda/estáticos 200)
- [x] Desplegar a Vercel y verificar la URL pública — **https://ciudad-bonita.vercel.app** (proyecto outi2/ciudad-bonita; SECRET_KEY guardada como variable de entorno; build remoto OK con uv desde pyproject.toml)

## Decisiones anotadas (opción más simple y segura)
- Python del equipo: 3.14.7 (no hay 3.12 instalada); Django 5.2.18 instalado y verificado funcionando sobre 3.14. Spec dice 3.12: se usa la versión disponible porque el código no depende de 3.12 en particular.
- git no estaba instalado en la máquina; se instaló Git 2.56.0.3 (gratuito) con winget para poder cumplir los commits por fase.
- Fase 1: propiedades de Producto renombradas (`tiene_oferta`, `stock_disponible`) para no chocar con las anotaciones ORM (`en_oferta`, `stock_total`).
- Fase 1: orden de URLs en config/urls.py — apps específicas (catalog, cart) ANTES del catch-all `<slug:slug>/` de core.
- Fase 1: "Ofertas de la semana" usa `SiteConfig.ofertas_hasta` (cuenta regresiva) + variantes con `precio_oferta`; el motor de descuentos completo llega en Fase 2.
- Fase 2: motor de ofertas — cada línea del carrito recibe UNA sola oferta automática (la que más descuente: relámpago, descuento directo, 2x1/3x2 o volumen); el cupón va al final y si no es acumulable se compara el total de ambas opciones y gana la más barata para el cliente. Todo en promotions/engine.py con pruebas.
- Fase 2: cupón de bienvenida por suscripción — `Cupon.es_bienvenida` marca la plantilla (BIENVENIDA10 en seed_demo) y `Cupon.crear_bienvenida()` genera un código único de un solo uso por suscriptor, mostrado en pantalla (sin correo).
- Fase 2: el carrito vive en la sesión (`cart/servicios.py`) y se expone en todas las páginas con un context processor (contador, drawer, resumen). El stepper del carrito envía `cantidad` (botones −/+) y `cantidad_ingresada` (campo digitado) porque el botón − va antes que el input en el DOM y, con el mismo nombre, su valor perdía.
- Fase 2: cuentas — el correo es el nombre de usuario; el carrito del invitado se fusiona con el guardado en la cuenta al iniciar sesión o registrarse (`fusionar_carrito`, suma cantidades) y `Usuario.carrito` se sincroniza en cada guardado para que salir y volver no duplique. El borrado de cuenta (Habeas Data) borra direcciones, deseos y carrito en cascada.
- Fase 2: pedidos — `Pedido` guarda una foto de los datos y precios al confirmar (nombre, envío, descuentos, total) y el usuario es `SET_NULL` (la venta sobrevive). Al borrar la cuenta se anonimizan los pedidos (nombre→"Cliente eliminada", email/teléfono/dirección vacíos), como manda la Ley 1581. Contraentrega entra "En preparación"; transferencia queda "Pendiente de pago" (el comprobante llega en Fase 3).
- Fase 3: pagos — `metodo_pago` incluye "pasarela" (primera opción del checkout cuando está habilitada). Contraentrega entra "En preparación"; pasarela y transferencia entran "Pendiente de pago". La pasarela simulada es una pantalla propia con el mismo formato de monto y referencia que la real: con una llave de Wompi se cambia solo la vista y la simulada se oculta sola. Todas las transiciones de estado pasan por `orders.servicios.cambiar_estado` (escribe en `HistorialPedido`).
- Fase 2: WhatsApp — el botón flotante de `base.html` usa el bloque `mensaje_whatsapp` (con `{% filter urlencode %}`); cada página lo sobreescribe con un mensaje propio (la ficha menciona el producto, la búsqueda la consulta, etc.). Sin número en `SiteConfig.whatsapp` no se muestra.
- Fase 1: `escapejson` no existe en Django 5.2; el JSON-LD y los textos para JS se arman en la vista con `json.dumps` + `|safe`.
