# Especificación del proyecto — Lencería de Hogar Ciudad Bonita

> Documento de memoria del proyecto. Contiene el prompt completo tal cual fue entregado.
> Al iniciar cada sesión o fase: lee AGENTS.md, PLAN.md y la sección relevante de este archivo.

## Contexto previo al prompt (decisiones de costo $0)

Voy a verificar qué opciones gratuitas existen hoy para alojar Django, porque los planes gratis cambian seguido.

Entendido: todo a costo $0, pensado como prueba de prompt, pero sin bajar la calidad. Cambié estas cosas:

- **Base de datos:** SQLite en lugar de PostgreSQL, sin instalar ni pagar nada. El código queda listo para migrar a PostgreSQL después.
- **Pagos:** el modo de pruebas (sandbox) de Wompi es gratis, y agregué una pasarela simulada local para probar pagos aprobados, rechazados y pendientes sin internet. En producción, Wompi cobra comisión por transacción, así que ese costo solo aparece cuando vendas de verdad.
- **Sin servicios de pago:** quité Cloudinary, Redis, Celery y Docker obligatorio. Las imágenes se guardan en disco, los correos se ven en consola, y las tareas programadas son comandos que se ejecutan a mano o con cron.
- **Hosting gratis:** hay que elegirlo con cuidado. El plan gratis de Render se apaga tras 15 minutos sin tráfico, y su base de datos Postgres gratuita expira a los 30 días. PythonAnywhere ofrece plan gratis con una sola aplicación web y sin dominio propio. Por eso el prompt pide desarrollo local primero, y PythonAnywhere como opción gratuita de publicación (conserva el disco, así SQLite sirve). Render queda solo para demos temporales, porque su disco se borra al reiniciar.
- **Para OpenCode:** los modelos gratuitos suelen tener menos memoria de contexto. El agente guarda la especificación en archivos del proyecto (AGENTS.md, ESPECIFICACION.md y PLAN.md) y los relee al iniciar cada fase, para no perder el hilo. Si lo usas con un modelo gratuito, pega el prompt y espera a que termine la Fase 0 antes de pedir la siguiente.

---

## Prompt v2 (100% gratuito, listo para pegar en OpenCode)

```
ROL
Eres un ingeniero full-stack senior especializado en e-commerce para Colombia. Vas a construir la tienda online "Lencería de Hogar Ciudad Bonita". Trabaja por fases (sección 21), ejecuta y prueba el código tú mismo, y al terminar cada fase entrega un resumen corto de qué hiciste y cómo correrlo.

REGLA MAESTRA: COSTO $0
Todo debe construirse, probarse y poder publicarse sin pagar nada. Solo se permiten librerías y herramientas gratuitas y de código abierto. Prohibido depender de servicios de pago, planes con tarjeta obligatoria, o APIs que exijan pago para funcionar. Si una integración externa es útil (pasarela, analítica, correo), debe ser OPCIONAL y el sistema debe funcionar completo sin ella mediante una alternativa local. Antes de añadir cualquier dependencia nueva, confirma que es gratuita y mantenida, y anótala en README con su licencia.

PASO 0 — MEMORIA DEL PROYECTO (obligatorio, hazlo primero)
Tu contexto puede ser limitado. Antes de escribir código:
1) Guarda este prompt completo, tal cual, en docs/ESPECIFICACION.md.
2) Crea AGENTS.md en la raíz con un resumen de máximo 60 líneas: stack, regla de costo $0, paleta, convenciones, comandos para correr/probar, y la instrucción "al iniciar cada sesión o fase, lee AGENTS.md, PLAN.md y la sección relevante de docs/ESPECIFICACION.md".
3) Crea PLAN.md con la lista de tareas de las fases (sección 21) como casillas [ ] y márcalas [x] al terminar. Actualízalo siempre.
4) Inicializa git y haz un commit por fase con mensaje claro en español.
Si pierdes contexto, relee esos archivos antes de continuar. No pidas confirmaciones innecesarias: si algo es ambiguo, elige la opción más simple y segura, anótala en PLAN.md y sigue.

1. NEGOCIO
- Nombre: Lencería de Hogar Ciudad Bonita (Bucaramanga, Santander, Colombia). Negocio nuevo, casi sin presencia en redes: la web debe atraer clientes por sí sola (SEO, WhatsApp, ofertas).
- Vende productos de terceros (proveedores), al detal, a cualquier persona mayor de edad. Marca accesible, económica y confiable; tono cálido y claro, español de Colombia (tuteo).
- Moneda COP, formato $89.900 (punto de miles, sin decimales), precios con IVA incluido (configurable).
- Envíos solo dentro de Santander. Un único idioma: español.
- Catálogo: sábanas y juegos de cama, edredones, cobijas y cubrelechos, almohadas y protectores de colchón, toallas, artículos de baño (cortinas de baño, tapetes, accesorios), cortinas, cojines y decoración, mantelería y cocina, sets/combos y bordados personalizados.
- La administra una persona no técnica: el panel debe ser claro, en español y sin código.

2. STACK TÉCNICO (decidido, no cambiar)
- Python 3.12 + Django 5.x con plantillas HTML renderizadas en servidor.
- Frontend: HTML5 semántico, CSS propio con variables (sin paso de compilación), JavaScript ligero con HTMX y Alpine.js. Descarga estas librerías y guárdalas en static/vendor/ (nada de depender de CDN en tiempo de ejecución).
- Base de datos: SQLite (modo WAL) por defecto, configurada con DATABASE_URL para poder pasar a PostgreSQL más adelante sin cambiar código. No uses funciones exclusivas de PostgreSQL.
- Imágenes: Pillow, conversión a WebP y miniaturas, almacenamiento local en media/.
- Admin: Django Admin personalizado en español (django-unfold o jazzmin, gratuitos); si alguno falla, usa el admin estándar con CSS propio.
- Búsqueda: sin servicios externos. Campo de texto normalizado (minúsculas, sin tildes) + sinónimos editables + tolerancia a errores con difflib o rapidfuzz.
- Correos: backend de consola/archivo en desarrollo; SMTP opcional (por ejemplo Gmail con contraseña de aplicación) configurable por .env.
- Tareas programadas: sin Celery ni Redis. Usa comandos de gestión (manage.py cancel_expired_orders, release_stock_reservations, send_abandoned_cart_emails) que se ejecutan a mano o con cron/Tareas programadas del hosting.
- Caché: la de Django en memoria local o archivo.
- Gráficas del dashboard: Chart.js local (static/vendor) o SVG/CSS propio.
- Documentos imprimibles (rótulo de envío, hoja de preparación): HTML con CSS de impresión (@media print), sin librerías de PDF.
- Autenticación en dos pasos de administradores: django-otp (gratuito).
- Configuración por variables de entorno (.env); entrega .env.example. Ningún secreto en el código.

3. APPS DJANGO SUGERIDAS
core, catalog, cart, orders, payments, shipping, promotions, accounts, inventory, notifications, dashboard. Código limpio, comentarios útiles en español, pruebas automáticas.

4. PÁGINAS Y RUTAS
Públicas: Inicio; Tienda/Catálogo; Categoría y subcategoría; Resultados de búsqueda; Ficha de producto; Ofertas; Combos y sets; Bordados personalizados; Carrito; Checkout (3 pasos) y confirmación; Seguimiento de pedido (número de pedido + celular, sin cuenta); Lista de deseos; Quiénes somos; Contacto y PQRS; Preguntas frecuentes; Envíos y cobertura en Santander; Cambios, devoluciones y retracto; Términos y condiciones; Política de privacidad y tratamiento de datos (Ley 1581 de 2012); Política de cookies; 404 y 500 amigables.
Cuenta: registro/ingreso, mis pedidos, direcciones, lista de deseos, mis datos, recuperar contraseña. La compra como invitado SIEMPRE debe estar permitida.
Inicio, en este orden: barra superior de promo y WhatsApp; encabezado con logo, buscador grande, cuenta y carrito; hero con oferta principal; categorías con imagen; "Ofertas de la semana" con cuenta regresiva; más vendidos; novedades; banner de bordados; combos; beneficios (pago seguro, envío en Santander, cambios, atención por WhatsApp); reseñas; suscripción con cupón de bienvenida; footer con medios de pago, redes, políticas y datos de contacto.

5. DISEÑO VISUAL
Estilo limpio, cálido, femenino sin ser infantil, mucho aire en blanco, fotos grandes, mobile-first (la mayoría comprará desde el celular). Bordes redondeados (10–16 px), sombras sutiles, transiciones de 150–250 ms.
Variables CSS:
--ciruela #5B2A86 (títulos, header, footer) | --purpura #8A4FBF (hover, íconos) | --lavanda #F1E8FA (fondos de sección) | --rosa-cta #C2185B (botones de compra) | --rosa-suave #FBD5E5 (etiquetas) | --crema #FFF8FB (fondo general) | --texto #2A2230 | --texto-2 #6A6173 | --borde #E7DCEE | --oferta #E0245E | --exito #2E9E6B | --aviso #F2A516 | --error #D93F3F.
Tipografías: títulos Playfair Display (600/700); texto Nunito Sans (400/600/700). Auto-hospédalas en static/fonts (licencia OFL, gratuitas) con font-display: swap y fuentes del sistema como respaldo; si no puedes descargarlas, usa Google Fonts con ese mismo respaldo.
Componentes: botón primario rosa con texto blanco; botón secundario con borde ciruela; etiquetas "-20%", "Nuevo", "Últimas unidades", "Envío gratis"; tarjeta de producto con imagen, nombre, precio tachado y final, miniaturas de color (swatches) y botón "Agregar"; corazón de lista de deseos.
Accesibilidad AA: contraste, foco visible, alt en imágenes, teclado, objetivos táctiles de 44 px mínimo.
Logo: wordmark "Ciudad Bonita" en SVG con detalle de ropa de cama o floral en los colores de la paleta, editable desde el admin. Favicon incluido. Imágenes de producto: genera marcadores de posición SVG/WebP propios (sin imágenes con derechos de autor).

6. MODELO DE DATOS DEL CATÁLOGO
- Categoría (con subcategorías, imagen, orden, SEO).
- Producto: nombre, slug, descripción corta y larga, marca, proveedor, categorías, etiquetas, material, composición, cuidado, estado (borrador/publicado/agotado), destacado, SEO, fotos múltiples ordenables.
- Variante (SKU): talla/medida, color, material, conteo de hilos, gramaje; precio, precio de oferta, costo (privado), stock, umbral de stock bajo, peso para envío, foto propia.
- Tallas de cama en Colombia: Sencilla, Semidoble, Doble, Queen, King. Toallas: cara, mano, baño, playa, con gramaje g/m². Cortinas: medidas estándar y "a la medida" (ancho x alto con precio por reglas del admin).
- Proveedor (tercero): nombre, contacto, tiempo de reposición, notas.
- Reseñas: 1–5 estrellas, comentario, solo compradores verificados, moderadas desde el admin.
- Combos/sets con descuento.
- Bordado personalizado: texto o iniciales (límite de caracteres), 4–6 tipografías de bordado, color de hilo, ubicación, costo adicional, tiempo extra, vista previa del texto en la fuente elegida, y aviso claro de que los productos personalizados no tienen cambio ni retracto salvo defecto de fabricación.

7. BÚSQUEDA Y FILTROS
- Buscador en el encabezado con autocompletado (HTMX), tolerante a tildes y errores de ortografía, con sinónimos editables en el admin (sábana/sabana; cobija/frazada/manta; edredón/cubrelecho/plumón; cortina de baño/cortina ducha). Registra búsquedas sin resultados para verlas en el admin.
- Filtros laterales (en celular, panel deslizable): categoría, talla/medida, color (swatches), material, rango de precio, en oferta, disponible, calificación, marca, hilos, gramaje; con contador por opción, chips de filtros activos, "Limpiar todo" y filtros reflejados en la URL.
- Orden: relevancia, más vendidos, menor y mayor precio, novedades, mejor calificados. "Cargar más" con HTMX. Estado vacío con sugerencias y botón de WhatsApp.

8. FICHA DE PRODUCTO
Galería con zoom y miniaturas; calificación; precio (tachado, final y % de ahorro) con "IVA incluido"; selectores de talla, color y material con disponibilidad en tiempo real; cantidad; botón "Agregar al carrito" fijo abajo en celular; "Comprar por WhatsApp" con mensaje prellenado; lista de deseos; aviso de stock bajo; calculadora de envío por municipio de Santander; guía de tallas (modal); pestañas de descripción, materiales y cuidado, envíos y devoluciones; reseñas; "Completa tu set"; "También te puede gustar"; vistos recientemente; compartir por WhatsApp. Datos estructurados schema.org (Product, Offer, AggregateRating).

9. CARRITO
Drawer lateral y página completa. Persistente (sesión; se fusiona al iniciar sesión). Cambiar cantidad, eliminar, guardar para después, cupón, subtotal, descuentos, envío estimado por municipio y total. Validación de stock en tiempo real. Barra "te faltan $X para envío gratis". Botón "Enviar mi pedido por WhatsApp" que genera el resumen del carrito.

10. CHECKOUT Y PAGOS
Una página, 3 pasos, barra de progreso y resumen siempre visible.
Paso 1 — Datos: nombre, email, celular (WhatsApp), cédula opcional. Casillas obligatorias: "Soy mayor de edad" y "Acepto términos y política de datos".
Paso 2 — Envío: departamento fijo Santander; municipio (lista con todos los municipios de Santander); barrio, dirección, indicaciones; entrega a domicilio o recogida en punto (activable). Costo según zona.
Paso 3 — Pago, con métodos activables/desactivables desde el admin:
  a) Pasarela simulada local (activa por defecto en desarrollo): pantalla propia que permite elegir "Aprobado", "Rechazado" o "Pendiente" para probar todo el flujo sin internet ni costo. Misma interfaz que la pasarela real, para poder cambiar de una a otra.
  b) Wompi (opcional, sandbox gratuito): Web Checkout con tarjetas, PSE, Nequi y DaviPlata según lo que el sandbox y la cuenta tengan activo. Referencia única = número de pedido, monto en centavos y firma de integridad según la documentación oficial vigente de Wompi (consúltala; no supongas endpoints ni campos de memoria). Webhook de eventos con verificación de firma, idempotente, que actualiza el pedido. Llaves en .env; si no existen, el método Wompi se oculta. Nunca guardar datos de tarjeta. Documenta en el README que en producción Wompi cobra comisión por transacción.
  c) Transferencia bancaria / Nequi / Daviplata manual: muestra datos de cuenta (editables en admin), el cliente sube comprobante (imagen/PDF validado, tamaño limitado), el pedido queda "Pago por verificar" y el admin aprueba o rechaza con un clic. El stock se reserva X horas (configurable) y luego se libera con el comando cancel_expired_orders.
  d) Contraentrega: construida pero DESACTIVADA por defecto.
Confirmación: número de pedido, resumen, instrucciones, enlace de seguimiento, correo y mensaje sugerido de WhatsApp. Estados: Pendiente de pago, Pago por verificar, Pagado, En preparación (incluye "En bordado"), Enviado (transportadora y guía), Entregado, Cancelado, Devuelto/Reembolsado; con historial de fecha y usuario. Reserva de stock de 15 minutos durante el checkout.

11. ENVÍOS (SOLO SANTANDER)
Zonas configurables en el admin: (1) área metropolitana de Bucaramanga (Bucaramanga, Floridablanca, Girón, Piedecuesta) con entrega propia o mensajero y tarifa baja; (2) resto de municipios por transportadora (Servientrega, Coordinadora, Interrapidísimo u otra) con tarifa por zona. Carga la lista oficial de municipios de Santander y permite asignar cada uno a una zona. Tarifa fija por zona u opcionalmente por peso; envío gratis desde un monto por zona (valores de ejemplo editables: $150.000 área metropolitana, $250.000 resto de Santander); tiempo estimado por zona; recogida opcional; guía y enlace de rastreo por pedido.

12. OFERTAS (todo editable sin código)
Descuento porcentual o por valor en producto, variante o categoría con fechas; cupones (código, % o valor, monto mínimo, límite de usos total y por cliente, primera compra, categorías, acumulable o no); 2x1, 3x2 y "lleva 3 paga 2"; combos con precio especial; descuento por volumen; venta relámpago con cuenta regresiva y página "Ofertas"; envío gratis desde un monto; cupón de bienvenida por suscripción; calendario de campañas con plantillas de banner (Día de la Madre, Día del Padre, Amor y Amistad, Black Friday, Navidad). Fase 2 (no obligatoria): puntos y referidos. Todos los descuentos se calculan en el servidor y se cubren con pruebas.

13. CONFIANZA Y CUMPLIMIENTO
Logos de medios de pago y candado/HTTPS; botón flotante de WhatsApp; reseñas verificadas; políticas visibles; política de retracto: en ventas a distancia el consumidor puede retractarse dentro de los 5 días hábiles siguientes a la entrega, con aviso de la excepción para bienes personalizados (bordados); formulario de PQRS; datos del vendedor en el pie de página con marcadores configurables [NIT], [DIRECCIÓN], [TELÉFONO], [EMAIL]; banner de cookies con consentimiento; autorización de datos en registro y checkout; casilla de mayoría de edad. "Quiénes somos" con historia y foto. Deja un punto de extensión para facturación electrónica (Alegra, Siigo o Factus) sin implementarlo. Incluye en el README una nota de que los textos legales son plantillas y deben revisarse con un abogado o contador.

14. CUENTA DE CLIENTE
Registro/ingreso, direcciones guardadas, historial con botón "volver a comprar", lista de deseos, comprobante de compra imprimible, recuperar contraseña por email, y eliminación de cuenta y datos (derechos Habeas Data).

15. WHATSAPP, MARKETING Y SEO
- Botón flotante de WhatsApp y enlaces wa.me en producto, carrito y confirmación; el número se configura en el admin.
- SEO: títulos y descripciones por producto y categoría, URLs limpias, sitemap.xml, robots.txt, Open Graph, schema.org, textos orientados a Bucaramanga y Santander. Guía en el README para Google Business Profile y Search Console (gratuitos).
- Analítica opcional: campos en el admin para GA4 y Meta Pixel (vacíos por defecto, solo cargan con consentimiento de cookies).
- Feed de catálogo exportable en CSV para Facebook/Instagram Shop y WhatsApp Business.
- Enlaces a redes configurables y botones de compartir. Blog/guías simples en fase 2.

16. PANEL DE ADMINISTRACIÓN (control total)
- Dashboard: ventas de hoy/semana/mes; pedidos por estado; pedidos que requieren acción (pagos por verificar, por enviar); stock bajo; más vendidos; ingresos, costos y margen estimado; clientes nuevos; cupones más usados; búsquedas sin resultados; gráficas simples.
- Productos y variantes: crear/editar con fotos arrastrables; duplicar; importar y exportar CSV (clave para cargar catálogos de proveedores, con plantilla de ejemplo y validación de errores por fila); edición rápida de precios y stock en tabla; acciones masivas.
- Inventario: stock por variante, movimientos con motivo, alertas de stock bajo, reporte valorizado, órdenes de compra simples a proveedores.
- Pedidos: filtros por estado, fecha, municipio y pago; detalle, cambio de estado, aprobar o rechazar comprobantes, registrar guía, imprimir rótulo y hoja de preparación (HTML de impresión), notas internas, reembolsos y devoluciones.
- Clientes: lista, historial, valor total, notas, exportación.
- Ofertas, cupones, banners y contenido del inicio editables.
- Configuración: datos del negocio, logo, métodos de pago, datos bancarios, zonas y tarifas, municipios, textos legales, WhatsApp, redes, analítica, plantillas de correo.
- Reportes exportables a CSV: ventas por período, producto, categoría, proveedor y municipio; cupones; inventario.
- Roles: Administradora (todo), Empleado (pedidos e inventario), Solo lectura. Registro de auditoría. Verificación en dos pasos para administradores.
- Ayuda integrada: tooltips y guía "Cómo cargar tu primer producto".

17. NOTIFICACIONES
Correos con diseño de marca (confirmación, pago recibido, comprobante rechazado, enviado con guía, entregado con solicitud de reseña, restablecer contraseña, carrito abandonado) y aviso interno de pedido nuevo (email y enlace de WhatsApp). Plantillas editables. En desarrollo se muestran en consola o se guardan en archivos.

18. SEGURIDAD, RENDIMIENTO Y CALIDAD
- Seguridad: HTTPS en producción, CSRF, protección XSS/inyección (ORM), cabeceras de seguridad, hashing de contraseñas de Django, límite de intentos de login (django-axes), validación de archivos subidos, límite de tasa en formularios y webhooks, logs de errores.
- Rendimiento: objetivo Lighthouse móvil >= 90; imágenes WebP responsivas con lazy-loading; caché de consultas pesadas; índices de base de datos; CSS/JS minimizados.
- Responsive probado en 360, 768 y 1280 px.
- Pruebas automáticas para precios, descuentos, cupones, stock, carrito, checkout, estados de pedido, pasarela simulada, webhook y envíos.
- Comando seed_demo: 8 categorías, 40 productos realistas con variantes, proveedores, cupones y ofertas de ejemplo, e imágenes de marcador de posición.

19. DESPLIEGUE GRATUITO
- Principal: ejecución local con "python manage.py runserver" (README paso a paso para Windows, Mac y Linux).
- Publicación gratuita recomendada: PythonAnywhere (plan gratuito, mantiene el disco, por lo que SQLite y media funcionan; sin dominio propio, un solo sitio y almacenamiento limitado; revisa en su documentación las restricciones de conexiones salientes). Incluye guía paso a paso y comandos para tareas programadas.
- Demos temporales: Render (plan gratuito) con advertencia explícita: el servicio se duerme tras inactividad y su disco es efímero, así que SQLite y las imágenes subidas se pierden al reiniciar; usar solo con datos de demostración (seed_demo).
- Backups: comando manage.py backup_db que copia la base y media/ a una carpeta fechada.
- Nota en el README sobre costos futuros al crecer (dominio, hosting pago, PostgreSQL, comisiones de pasarela) para que la dueña los conozca.

20. DOCUMENTACIÓN
README en español: instalación local, variables de entorno, pruebas, carga de productos (manual y por CSV), configuración de Wompi sandbox y producción, publicación gratuita, backups y una guía corta para la dueña del negocio.

21. PLAN POR FASES (detente al final de cada una, actualiza PLAN.md, haz commit y resume)
Fase 0 — Memoria del proyecto (Paso 0), estructura, entorno, configuración, modelos base, diseño base (variables CSS, layout, header, footer), admin básico en español.
Fase 1 — Catálogo: categorías, productos, variantes, imágenes, inicio, listado, ficha de producto, búsqueda y filtros, seed_demo.
Fase 2 — Compra: carrito, cupones y ofertas, checkout en 3 pasos, zonas de envío de Santander, cuentas, lista de deseos, WhatsApp.
Fase 3 — Pagos y pedidos: pasarela simulada, transferencia con comprobante, estados de pedido, correos, seguimiento, y Wompi sandbox opcional con webhook.
Fase 4 — Administración: dashboard, inventario, importación/exportación CSV, reportes, roles, auditoría, ajustes del negocio.
Fase 5 — Pulido: SEO, analítica opcional, textos legales, rendimiento, accesibilidad, pruebas completas, backups y guía de publicación gratuita.
Criterio de aceptación final: sin pagar nada, un cliente puede entrar desde el celular, buscar y filtrar, agregar al carrito, pagar (simulado o por transferencia) y recibir confirmación; y la dueña puede cargar productos, gestionar pedidos, controlar inventario y crear ofertas sin tocar código.

22. REGLAS DE TRABAJO
- No inventes datos legales, bancarios ni de contacto: usa marcadores configurables en el admin.
- Prefiere soluciones simples y mantenibles; evita dependencias innecesarias.
- Si una tarea es muy grande para tu contexto, divídela en pasos pequeños, termina y prueba cada uno antes de seguir.
- Todo texto visible para el usuario va en español de Colombia.
- Al terminar cada fase: corre las pruebas, corrige errores y verifica que el servidor arranque antes de resumir.
```

**Cómo usarlo en OpenCode:**
1. Crea una carpeta vacía para el proyecto y abre OpenCode ahí.
2. Pega el prompt completo.
3. Cuando termine la Fase 0, revisa que existan AGENTS.md, PLAN.md y docs/ESPECIFICACION.md.
4. Para seguir, escribe "continúa con la Fase 1" (y así con cada fase).
5. Si el agente se pierde o se queda sin contexto, escríbele: "lee AGENTS.md y PLAN.md y continúa donde ibas".
