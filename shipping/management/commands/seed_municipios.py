"""
Carga los municipios oficiales de Santander y sus zonas de envío.

Idempotente: se puede ejecutar varias veces sin duplicar.
La lista corresponde a los 87 municipios del departamento
(86 municipios + Bucaramanga como distrito especial), según la
división político-administrativa oficial.
"""
from django.core.management.base import BaseCommand

from shipping.models import MunicipioSantander, ZonaEnvio

# Municipios de Santander en orden alfabético (fuente: DANE / Wikipedia).
MUNICIPIOS = [
    "Aguada", "Albania", "Aratoca", "Barbosa", "Barichara", "Barrancabermeja",
    "Betulia", "Bolívar", "Bucaramanga", "Cabrera", "California", "Capitanejo",
    "Carcasí", "Cepitá", "Cerrito", "Charalá", "Charta", "Chima", "Chipatá",
    "Cimitarra", "Concepción", "Confines", "Contratación", "Coromoro", "Curití",
    "El Carmen de Chucurí", "El Guacamayo", "El Peñón", "El Playón", "Encino",
    "Enciso", "Floridablanca", "Florián", "Galán", "Gámbita", "Girón", "Guaca",
    "Guadalupe", "Guapotá", "Guavatá", "Güepsa", "Hato", "Jesús María",
    "Jordán", "La Belleza", "La Paz", "Landázuri", "Lebrija", "Los Santos",
    "Macaravita", "Málaga", "Matanza", "Mogotes", "Molagavita", "Ocamonte",
    "Oiba", "Onzaga", "Palmar", "Palmas del Socorro", "Páramo", "Piedecuesta",
    "Pinchote", "Puente Nacional", "Puerto Parra", "Puerto Wilches", "Rionegro",
    "Sabana de Torres", "San Andrés", "San Benito", "San Gil", "San Joaquín",
    "San José de Miranda", "San Miguel", "San Vicente del Chucurí",
    "Santa Bárbara", "Santa Helena del Opón", "Simacota", "Socorro", "Suaita",
    "Sucre", "Suratá", "Tona", "Valle de San José", "Vélez", "Vetas",
    "Villanueva", "Zapatoca",
]

# Área metropolitana de Bucaramanga: entrega propia, tarifa baja.
AREA_METROPOLITANA = ["Bucaramanga", "Floridablanca", "Girón", "Piedecuesta"]


class Command(BaseCommand):
    help = "Carga zonas de envío de ejemplo y los 87 municipios de Santander (idempotente)."

    def handle(self, *args, **kwargs):
        # Zonas de ejemplo editables en el admin.
        metro, _ = ZonaEnvio.objects.get_or_create(
            nombre="Área metropolitana de Bucaramanga",
            defaults={
                "descripcion": "Entrega propia con mensajero de la tienda.",
                "tarifa": 8000,
                "envio_gratis_desde": 150000,
                "tiempo_estimado": "Mismo día o al siguiente día hábil",
                "recogida_disponible": True,
                "activa": True,
                "orden": 1,
            },
        )
        resto, _ = ZonaEnvio.objects.get_or_create(
            nombre="Resto de Santander",
            defaults={
                "descripcion": "Envío por transportadora (Servientrega, Coordinadora u otra).",
                "tarifa": 15000,
                "envio_gratis_desde": 250000,
                "tiempo_estimado": "2 a 4 días hábiles",
                "recogida_disponible": False,
                "activa": True,
                "orden": 2,
            },
        )

        creados = 0
        for nombre in MUNICIPIOS:
            zona = metro if nombre in AREA_METROPOLITANA else resto
            _, creado = MunicipioSantander.objects.get_or_create(
                nombre=nombre, defaults={"zona": zona}
            )
            if creado:
                creados += 1

        total = MunicipioSantander.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Listo: 2 zonas y {total} municipios de Santander "
                f"({creados} nuevos)."
            )
        )
