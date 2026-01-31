"""
Definizioni protocolli standard per blend peptidici.

Contiene le composizioni nominali dei protocolli più comuni per calcolare
l'accuratezza di ogni singolo componente.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ProtocolComponent:
    """Singolo componente di un protocollo blend."""
    peptide_name: str  # Nome normalizzato (es. "BPC157", "TB500", "GHK-Cu", "KPV")
    ratio: float       # Proporzione rispetto agli altri componenti


@dataclass
class BlendProtocol:
    """Definizione di un protocollo blend standard."""
    name: str
    components: List[ProtocolComponent]

    def get_nominal_quantities(self, total_mg: float) -> Dict[str, float]:
        """
        Calcola le quantità nominali per ogni componente dato il totale.

        Args:
            total_mg: Quantità totale del blend in mg

        Returns:
            Dict {peptide_name: quantità_nominale_mg}
        """
        # Calcola somma ratios
        total_ratio = sum(c.ratio for c in self.components)

        # Calcola quantità per ogni componente
        quantities = {}
        for component in self.components:
            quantities[component.peptide_name] = (component.ratio / total_ratio) * total_mg

        return quantities

    def get_component_names(self) -> List[str]:
        """Ritorna lista nomi componenti normalizzati."""
        return [c.peptide_name for c in self.components]


# Definizioni protocolli standard
BLEND_PROTOCOLS = {
    'GLOW': BlendProtocol(
        name='GLOW',
        components=[
            ProtocolComponent('BPC157', 1.0),
            ProtocolComponent('TB500', 1.0),
            ProtocolComponent('GHK-Cu', 5.0),
        ]
    ),

    'BPC+TB': BlendProtocol(
        name='BPC+TB',
        components=[
            ProtocolComponent('BPC157', 1.0),
            ProtocolComponent('TB500', 1.0),
        ]
    ),

    'KLOW': BlendProtocol(
        name='KLOW',
        components=[
            ProtocolComponent('BPC157', 1.0),
            ProtocolComponent('TB500', 1.0),
            ProtocolComponent('KPV', 1.0),
            ProtocolComponent('GHK-Cu', 5.0),
        ]
    ),

    # Varianti con capitalizzazione diversa
    'Glow': BlendProtocol(
        name='Glow',
        components=[
            ProtocolComponent('BPC157', 1.0),
            ProtocolComponent('TB500', 1.0),
            ProtocolComponent('GHK-Cu', 5.0),
        ]
    ),

    'glow': BlendProtocol(
        name='glow',
        components=[
            ProtocolComponent('BPC157', 1.0),
            ProtocolComponent('TB500', 1.0),
            ProtocolComponent('GHK-Cu', 5.0),
        ]
    ),

    'Klow': BlendProtocol(
        name='Klow',
        components=[
            ProtocolComponent('BPC157', 1.0),
            ProtocolComponent('TB500', 1.0),
            ProtocolComponent('KPV', 1.0),
            ProtocolComponent('GHK-Cu', 5.0),
        ]
    ),

    'klow': BlendProtocol(
        name='klow',
        components=[
            ProtocolComponent('BPC157', 1.0),
            ProtocolComponent('TB500', 1.0),
            ProtocolComponent('KPV', 1.0),
            ProtocolComponent('GHK-Cu', 5.0),
        ]
    ),

    # Varianti con suffissi (KLOW80, Klow80, etc.)
    'KLOW80': BlendProtocol(
        name='KLOW80',
        components=[
            ProtocolComponent('BPC157', 1.0),
            ProtocolComponent('TB500', 1.0),
            ProtocolComponent('KPV', 1.0),
            ProtocolComponent('GHK-Cu', 5.0),
        ]
    ),

    'Klow80': BlendProtocol(
        name='Klow80',
        components=[
            ProtocolComponent('BPC157', 1.0),
            ProtocolComponent('TB500', 1.0),
            ProtocolComponent('KPV', 1.0),
            ProtocolComponent('GHK-Cu', 5.0),
        ]
    ),

    # Altri protocolli comuni
    'BPC-157/TB500': BlendProtocol(
        name='BPC-157/TB500',
        components=[
            ProtocolComponent('BPC157', 1.0),
            ProtocolComponent('TB500', 1.0),
        ]
    ),

    'BPC-157/TB-500': BlendProtocol(
        name='BPC-157/TB-500',
        components=[
            ProtocolComponent('BPC157', 1.0),
            ProtocolComponent('TB500', 1.0),
        ]
    ),

    'BPC157+TB500': BlendProtocol(
        name='BPC157+TB500',
        components=[
            ProtocolComponent('BPC157', 1.0),
            ProtocolComponent('TB500', 1.0),
        ]
    ),

    'TB-500/BPC-157': BlendProtocol(
        name='TB-500/BPC-157',
        components=[
            ProtocolComponent('TB500', 1.0),
            ProtocolComponent('BPC157', 1.0),
        ]
    ),

    'TB500/BPC157': BlendProtocol(
        name='TB500/BPC157',
        components=[
            ProtocolComponent('TB500', 1.0),
            ProtocolComponent('BPC157', 1.0),
        ]
    ),
}


def get_protocol(protocol_name: str) -> Optional[BlendProtocol]:
    """
    Recupera definizione protocollo per nome.

    Args:
        protocol_name: Nome protocollo (es. "GLOW", "BPC+TB", "KLOW")

    Returns:
        BlendProtocol se trovato, altrimenti None
    """
    if not protocol_name:
        return None

    # Cerca match esatto
    if protocol_name in BLEND_PROTOCOLS:
        return BLEND_PROTOCOLS[protocol_name]

    # Cerca match case-insensitive
    protocol_lower = protocol_name.lower()
    for name, protocol in BLEND_PROTOCOLS.items():
        if name.lower() == protocol_lower:
            return protocol

    # Cerca match parziale (es. "GLOW 70" → "GLOW")
    protocol_base = protocol_name.split()[0]  # Prendi prima parola
    if protocol_base in BLEND_PROTOCOLS:
        return BLEND_PROTOCOLS[protocol_base]

    # Cerca match con base case-insensitive
    protocol_base_lower = protocol_base.lower()
    for name, protocol in BLEND_PROTOCOLS.items():
        if name.lower().startswith(protocol_base_lower):
            return protocol

    return None


def calculate_component_nominal_quantities(
    protocol_name: str,
    total_nominal_mg: float
) -> Optional[Dict[str, float]]:
    """
    Calcola quantità nominali per ogni componente di un blend.

    Args:
        protocol_name: Nome protocollo (es. "GLOW", "KLOW")
        total_nominal_mg: Quantità totale nominale in mg

    Returns:
        Dict {peptide_name: quantità_nominale_mg} o None se protocollo sconosciuto

    Example:
        >>> calculate_component_nominal_quantities("GLOW", 70.0)
        {'BPC157': 10.0, 'TB500': 10.0, 'GHK-Cu': 50.0}
    """
    protocol = get_protocol(protocol_name)
    if not protocol:
        return None

    return protocol.get_nominal_quantities(total_nominal_mg)


def is_known_protocol(protocol_name: str) -> bool:
    """
    Verifica se un protocollo è noto.

    Args:
        protocol_name: Nome protocollo da verificare

    Returns:
        True se il protocollo è definito
    """
    return get_protocol(protocol_name) is not None
