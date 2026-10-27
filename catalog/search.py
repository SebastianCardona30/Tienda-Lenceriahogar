"""
Búsqueda sin servicios externos: texto normalizado (sin tildes ni mayúsculas),
sinónimos editables desde el admin y tolerancia a errores con rapidfuzz.
"""
import unicodedata

from rapidfuzz import fuzz, process


def normalizar_texto(texto):
    """Minúsculas, sin tildes ni caracteres raros. 'Sábanas' -> 'sabanas'."""
    if not texto:
        return ""
    texto = str(texto).lower().strip()
    texto = "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )
    return " ".join(texto.split())


def expandir_consulta(consulta, sinonimos):
    """
    Devuelve la consulta y sus sinónimos como palabras clave.

    Ej.: 'sabanas' con sinónimo (sábana, sabanas, sabana) -> ['sabanas', 'sabana'].
    """
    base = normalizar_texto(consulta)
    if not base:
        return []
    palabras = [base]
    for palabra in base.split():
        for grupo in sinonimos:
            # Cada grupo puede venir como texto con comas o ya como lista
            if isinstance(grupo, str):
                opciones = [normalizar_texto(o) for o in grupo.split(",")]
            else:
                opciones = [normalizar_texto(o) for o in grupo]
            if palabra in opciones:
                palabras.extend(opciones)
    # Quita duplicados conservando el orden
    vistas, resultado = set(), []
    for p in palabras:
        if p and p not in vistas:
            vistas.add(p)
            resultado.append(p)
    return resultado


def busqueda_tolerante(consulta, candidatos, umbral=60):
    """
    Para consultas cortas, devuelve candidatos parecidos aunque tengan
    errores de ortografía. 'edreon' encuentra 'edredon'.

    candidatos: lista de textos normalizados para comparar.
    """
    if not consulta or not candidatos:
        return []
    resultado = process.extract(
        normalizar_texto(consulta),
        candidatos,
        scorer=fuzz.partial_ratio,
        limit=8,
    )
    return [texto for texto, puntaje, _idx in resultado if puntaje >= umbral]
