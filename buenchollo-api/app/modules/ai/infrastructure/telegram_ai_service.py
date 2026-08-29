"""Telegram publication AI assistant for category/hashtag suggestion."""

import logging
import re
import unicodedata
from app.modules.ai.domain.ports import LLMClientProtocol

logger = logging.getLogger(__name__)


def _normalize_tag(tag: str) -> str:
    """Normaliza un hashtag para comparación insensible a mayúsculas, acentos y almohadilla."""
    clean = tag.strip().lstrip("#").lower()
    return "".join(c for c in unicodedata.normalize("NFD", clean) if unicodedata.category(c) != "Mn")


SYNONYM_MAP: dict[str, str] = {
    "auricular": "#Auriculares",
    "auriculares": "#Auriculares",
    "headphone": "#Auriculares",
    "headphones": "#Auriculares",
    "earbuds": "#Auriculares",
    "bluetooth": "#Auricularesbluetooth",
    "altavoz": "#Altavoces",
    "altavoces": "#Altavoces",
    "speaker": "#Altavoces",
    "soundbar": "#BarrasdeSonido",
    "barra de sonido": "#BarrasdeSonido",
    "raton": "#Ratones",
    "ratones": "#Ratones",
    "mouse": "#Ratones",
    "teclado": "#Teclados",
    "teclados": "#Teclados",
    "keyboard": "#Teclados",
    "monitor": "#Monitores",
    "monitores": "#Monitores",
    "portatil": "#OrdenadorPortatil",
    "laptop": "#OrdenadorPortatil",
    "notebook": "#OrdenadorPortatil",
    "movil": "#SmartPhones",
    "smartphone": "#SmartPhones",
    "smartphones": "#SmartPhones",
    "telefono": "#SmartPhones",
    "smartwatch": "#SmartWatches",
    "reloj inteligente": "#SmartWatches",
    "smart tv": "#SmartTv",
    "televisor": "#Televisores",
    "televisores": "#Televisores",
    "tv": "#Televisores",
    "gopro": "#GoPro",
    "camara": "#Camara",
    "microfono": "#Microfono",
    "disco duro": "#DiscosDuros",
    "ssd": "#Almacenamiento",
    "hdd": "#HDD",
    "power bank": "#PowerBank",
    "cargador": "#Cargadores",
    "cargadores": "#Cargadores",
    "enchufe inteligente": "#EnchufesInteligentes",
    "domotica": "#Domotica",
    "smart home": "#SmartHome",
    "gaming": "#Gaming",
    "gamer": "#Gaming",
    "juego": "#Gaming",
    "switch": "#Switch",
    "nintendo": "#Nintendo",
    "tablet": "#Tablets",
    "tablets": "#Tablets",
    "ipad": "#Tablets",
    "impresora": "#Impresora",
    "router": "#Router",
    "wifi": "#Redes",
    "silla gaming": "#SillaGaming",
    "fuente alimentacion": "#FuentesAlimentación",
    "fuente de alimentacion": "#FuentesAlimentación",
    "fuente de poder": "#FuentesAlimentación",
}


class TelegramAIService:
    """Provides AI-powered hashtag and categorization suggestions for Telegram deals."""

    def __init__(self, llm_client: LLMClientProtocol) -> None:
        self.llm_client = llm_client

    @staticmethod
    def extract_heuristic_tags(
        title: str,
        description: str,
        available: list[str],
    ) -> list[str]:
        """Extrae de 1 a 2 hashtags del catálogo disponible buscando coincidencias léxicas y sinónimos."""
        if not available:
            return []

        lookup = {_normalize_tag(cat): cat for cat in available}
        selected: list[str] = []
        seen: set[str] = set()

        text_to_search = f"{title} {description}".lower()
        norm_text = _normalize_tag(text_to_search)

        # 1. Búsqueda por sinónimos comunes directos
        for keyword, target_tag in SYNONYM_MAP.items():
            norm_kw = _normalize_tag(keyword)
            if norm_kw in norm_text:
                canonical = lookup.get(_normalize_tag(target_tag), target_tag if target_tag in available else None)
                if canonical and canonical in available and canonical not in seen:
                    seen.add(canonical)
                    selected.append(canonical)
                    if len(selected) >= 2:
                        return selected

        # 2. Búsqueda por subcadenas directas del catálogo
        for norm_key, canonical in lookup.items():
            if len(norm_key) >= 4 and norm_key in norm_text:
                if canonical not in seen:
                    seen.add(canonical)
                    selected.append(canonical)
                    if len(selected) >= 2:
                        return selected

        return selected

    async def suggest_categories(
        self,
        title: str,
        description: str,
        available: list[str],
    ) -> list[str]:
        """Llama al motor de IA para elegir 1-2 hashtags pertinentes del catálogo disponible con fallback heurístico."""
        if not available:
            return []

        lookup = {_normalize_tag(cat): cat for cat in available}
        selected: list[str] = []
        seen: set[str] = set()

        try:
            cats_str = " ".join(available)
            prompt = (
                "Eres un clasificador taxonómico para un canal de ofertas tecnológicas en Telegram.\n"
                "Elige exactamente 1 o 2 hashtags que mejor describan el producto, seleccionando ÚNICAMENTE de la lista permitida.\n"
                "Responde únicamente con los 1 o 2 hashtags elegidos de la lista separados por un espacio (ejemplo: #Gaming #Auriculares).\n\n"
                f"LISTA DISPONIBLE:\n{cats_str}\n\n"
                f"PRODUCTO:\nTítulo: {title}\nDetalles: {description}"
            )
            messages = [
                {
                    "role": "system",
                    "content": "Eres un clasificador taxonómico conciso. Responde únicamente con 1 o 2 hashtags de la lista disponible, sin explicaciones ni texto adicional.",
                },
                {"role": "user", "content": prompt},
            ]

            result = await self.llm_client.agenerate_text(messages, temperature=0.2, max_tokens=200)
            raw = result.content.strip()

            tokens = re.findall(r"#?[A-Za-z0-9áéíóúÁÉÍÓÚñÑüÜ]+", raw)
            for token in tokens:
                norm = _normalize_tag(token)
                if norm in lookup:
                    canonical = lookup[norm]
                    if canonical not in seen:
                        seen.add(canonical)
                        selected.append(canonical)
                        if len(selected) >= 2:
                            break

        except Exception as exc:
            logger.warning("Error en TelegramAIService al sugerir categorías con IA: %s", exc)

        # Fallback de rescate heurístico garantizado si la IA falló o no encontró etiquetas
        if not selected:
            selected = self.extract_heuristic_tags(title, description, available)

        return selected
