"""
Peptide Name Normalizer - Janoshik

Normalizza nomi peptidi estratti da certificati Janoshik per gestire variazioni:
- Varianti spelling (BPC-157, BPC157, BPC 157 → "BPC157")
- Nomi commerciali vs generici (GLP vs Semaglutide)
- Codici vs nomi completi (GLP-2TZ vs Tirzepatide)
- Alias e sinonimi comuni
"""

import re
from typing import Optional


class PeptideNormalizer:
    """Normalizzatore nomi peptidi Janoshik"""
    
    # Mapping manuale: varianti → nome standard
    # Formato: "variante_lowercase" → "Nome Standard"
    MANUAL_MAPPINGS = {
        # GLP-1 Agonists
        "glp": "Semaglutide",
        "glp-1": "Semaglutide",
        "glp1": "Semaglutide",
        "semaglutide": "Semaglutide",
        "sema": "Semaglutide",
        
        "glp-2tz": "Tirzepatide",
        "glp2tz": "Tirzepatide",
        "tirz": "Tirzepatide",
        "tirzepatide": "Tirzepatide",
        
        "glp-3rt": "Retatrutide",
        "glp3rt": "Retatrutide",
        "reta": "Retatrutide",
        "retatrutide": "Retatrutide",
        
        "liraglutide": "Liraglutide",
        "lira": "Liraglutide",
        
        "cagrilintide": "Cagrilintide",
        "cagri": "Cagrilintide",
        
        # Repair Peptides
        "bpc-157": "BPC-157",
        "bpc157": "BPC-157",
        "bpc 157": "BPC-157",
        "bpc": "BPC-157",
        
        "tb-500": "TB500",
        "tb500": "TB500",
        "tb 500": "TB500",
        "tb4": "TB500",
        "thymosin beta-4": "TB500",
        "thymosin": "TB500",
        
        "kpv": "KPV",
        
        "ghk-cu": "GHK-Cu",
        "ghk cu": "GHK-Cu",
        "ghkcu": "GHK-Cu",
        "ghk": "GHK-Cu",
        
        # Growth Hormones & Secretagogues
        "hgh": "HGH",
        "somatropin": "HGH",
        "growth hormone": "HGH",
        "qitrope": "HGH",
        
        "ipamorelin": "Ipamorelin",
        "ipam": "Ipamorelin",
        "ipa": "Ipamorelin",
        
        "cjc-1295": "CJC-1295",
        "cjc1295": "CJC-1295",
        "cjc 1295": "CJC-1295",
        "cjc": "CJC-1295",
        
        "tesamorelin": "Tesamorelin",
        "tesa": "Tesamorelin",
        
        "mk-677": "MK-677",
        "mk677": "MK-677",
        "mk 677": "MK-677",
        "ibutamoren": "MK-677",
        
        "ghrp-2": "GHRP-2",
        "ghrp2": "GHRP-2",
        "ghrp 2": "GHRP-2",
        
        "ghrp-6": "GHRP-6",
        "ghrp6": "GHRP-6",
        "ghrp 6": "GHRP-6",
        
        "hexarelin": "Hexarelin",
        "hexa": "Hexarelin",
        
        # Anti-Aging & Longevity
        "nad+": "NAD+",
        "nad": "NAD+",
        "nicotinamide adenine dinucleotide": "NAD+",
        
        "epithalon": "Epithalon",
        "epitalon": "Epithalon",
        "epithalamin": "Epithalon",
        
        "mots-c": "MOTS-C",
        "motsc": "MOTS-C",
        "mots c": "MOTS-C",
        "mots": "MOTS-C",
        
        "nmn": "NMN",
        "nicotinamide mononucleotide": "NMN",
        
        # Nootropics
        "selank": "Selank",
        "semax": "Semax",
        "p21": "P21",
        "dihexa": "Dihexa",
        
        # Metabolic
        "aod-9604": "AOD-9604",
        "aod9604": "AOD-9604",
        "aod 9604": "AOD-9604",
        "aod": "AOD-9604",
        
        "5-amino-1mq": "5-Amino-1MQ",
        "5amino1mq": "5-Amino-1MQ",
        "5-amino 1mq": "5-Amino-1MQ",
        "5 amino 1mq": "5-Amino-1MQ",
        
        # Immune
        "thymosin-alpha-1": "Thymosin-Alpha-1",
        "thymosin alpha 1": "Thymosin-Alpha-1",
        "thymosinalpha1": "Thymosin-Alpha-1",
        "ta1": "Thymosin-Alpha-1",
        
        "ll-37": "LL-37",
        "ll37": "LL-37",
        "ll 37": "LL-37",
        
        # Sexual & Cosmetic
        "pt-141": "PT-141",
        "pt141": "PT-141",
        "pt 141": "PT-141",
        "bremelanotide": "PT-141",
        
        "melanotan-ii": "Melanotan-II",
        "melanotan ii": "Melanotan-II",
        "melanotan2": "Melanotan-II",
        "mt2": "Melanotan-II",
        "mt-2": "Melanotan-II",
        
        "melanotan-i": "Melanotan-I",
        "melanotan i": "Melanotan-I",
        "melanotan1": "Melanotan-I",
        "mt1": "Melanotan-I",
        "mt-1": "Melanotan-I",
        
        # Other
        "dsip": "DSIP",
        "delta sleep inducing peptide": "DSIP",
        
        "hcg": "HCG",
        "human chorionic gonadotropin": "HCG",
        
        "igf-1": "IGF-1",
        "igf1": "IGF-1",
        "igf 1": "IGF-1",
        "insulin-like growth factor": "IGF-1",
        
        "igf-1 lr3": "IGF-1 LR3",
        "igf1lr3": "IGF-1 LR3",
        "igf-1lr3": "IGF-1 LR3",
        
        "enclomiphene": "Enclomiphene",
        "enclo": "Enclomiphene",
        
        "gonadorelin": "Gonadorelin",
        "gnrh": "Gonadorelin",
        
        # Blends & Combos (mantieni come sono)
        "bpc157+tb500": "BPC157+TB500",
        "bpc-157+tb-500": "BPC157+TB500",
        "tb500+bpc157": "BPC157+TB500",
    }
    
    @staticmethod
    def normalize(raw_name: str) -> str:
        """
        Normalizza nome peptide.
        
        Args:
            raw_name: Nome estratto da certificato
            
        Returns:
            Nome normalizzato
        """
        if not raw_name or not isinstance(raw_name, str):
            return "Unknown"
        
        # Trim
        normalized = raw_name.strip()
        
        # Rimuovi dosaggi e formulations comuni
        # Es: "BPC-157 5mg" → "BPC-157"
        # Es: "Semaglutide (5mg)" → "Semaglutide"
        normalized = re.sub(r'\s*\(?\d+\.?\d*\s*(mg|mcg|iu|µg)\)?', '', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\s*\d+\.?\d*\s*(mg|mcg|iu|µg)', '', normalized, flags=re.IGNORECASE)
        
        # Rimuovi prefissi comuni come "peptide:", "compound:", ecc
        normalized = re.sub(r'^(peptide|compound|product):\s*', '', normalized, flags=re.IGNORECASE)
        
        # Lowercase per matching
        normalized_lower = normalized.strip().lower()
        
        # Check manual mapping
        if normalized_lower in PeptideNormalizer.MANUAL_MAPPINGS:
            return PeptideNormalizer.MANUAL_MAPPINGS[normalized_lower]
        
        # Check partial matches per blends (es: "BPC-157 + TB-500" → "BPC157+TB500")
        if '+' in normalized_lower or '&' in normalized_lower or 'and' in normalized_lower:
            # Split e normalizza ogni componente
            parts = re.split(r'\s*[+&]\s*|\s+and\s+', normalized_lower)
            normalized_parts = []
            for part in parts:
                part = part.strip()
                if part in PeptideNormalizer.MANUAL_MAPPINGS:
                    normalized_parts.append(PeptideNormalizer.MANUAL_MAPPINGS[part])
                else:
                    # Fallback: title case
                    normalized_parts.append(part.title())
            
            return "+".join(normalized_parts)
        
        # Fallback: Title case con fix comuni
        result = normalized.strip().title()
        
        # Fix numeri e trattini comuni
        result = re.sub(r'Bpc-?(\d+)', r'BPC\1', result)
        result = re.sub(r'Tb-?(\d+)', r'TB\1', result)
        result = re.sub(r'Cjc-?(\d+)', r'CJC-\1', result)
        result = re.sub(r'Aod-?(\d+)', r'AOD-\1', result)
        result = re.sub(r'Pt-?(\d+)', r'PT-\1', result)
        result = re.sub(r'Mk-?(\d+)', r'MK-\1', result)
        result = re.sub(r'Ll-?(\d+)', r'LL-\1', result)
        result = re.sub(r'Igf-?(\d+)', r'IGF-\1', result)
        result = re.sub(r'Ghrp-?(\d+)', r'GHRP-\1', result)
        result = re.sub(r'Mots-?C', r'MOTS-C', result)
        result = re.sub(r'Ghk-?Cu', r'GHK-Cu', result)
        result = re.sub(r'Ss-?(\d+)', r'SS-\1', result)
        result = re.sub(r'Pnc-?(\d+)', r'PNC-\1', result)
        result = re.sub(r'Peg-?Mgf', r'PEG-MGF', result, flags=re.IGNORECASE)
        result = re.sub(r'Snap-?(\d+)', r'SNAP-\1', result)
        result = re.sub(r'Slu-?Pp', r'SLU-PP', result, flags=re.IGNORECASE)
        result = re.sub(r'Slp-?Pp', r'SLP-PP', result, flags=re.IGNORECASE)
        
        # Fix acronyms completamente maiuscoli (2-4 lettere all'inizio o fine parola)
        result = re.sub(r'\b([A-Z]{2,4})\b', lambda m: m.group(1).upper(), result)
        
        # Fix acronyms comuni
        result = re.sub(r'\bHgh\b', 'HGH', result)
        result = re.sub(r'\bHcg\b', 'HCG', result)
        result = re.sub(r'\bNad\b', 'NAD+', result)
        result = re.sub(r'\bNmn\b', 'NMN', result)
        result = re.sub(r'\bKpv\b', 'KPV', result)
        result = re.sub(r'\bDsip\b', 'DSIP', result)
        result = re.sub(r'\bVip\b', 'VIP', result)
        result = re.sub(r'\bNpp\b', 'NPP', result)
        result = re.sub(r'\bTre\b', 'TRE', result)
        result = re.sub(r'\bGlow\b', 'GLOW', result)
        result = re.sub(r'\bKlow\b', 'KLOW', result)
        
        return result
    
    @staticmethod
    def get_normalization_stats(peptide_names: list) -> dict:
        """
        Analizza lista nomi peptidi e mostra statistiche normalizzazione.
        
        Args:
            peptide_names: Lista nomi da analizzare
            
        Returns:
            Dict con statistiche
        """
        from collections import Counter
        
        # Normalizza tutti i nomi
        normalized_mapping = {}
        for name in peptide_names:
            if name:
                norm = PeptideNormalizer.normalize(name)
                if norm not in normalized_mapping:
                    normalized_mapping[norm] = []
                normalized_mapping[norm].append(name)
        
        # Trova duplicati (stesso nome normalizzato con varianti diverse)
        duplicates = {norm: variants for norm, variants in normalized_mapping.items() 
                     if len(set(variants)) > 1}
        
        # Conta frequenze
        normalized_counts = Counter([PeptideNormalizer.normalize(n) for n in peptide_names if n])
        
        return {
            'total_peptides': len(peptide_names),
            'unique_raw': len(set(peptide_names)),
            'unique_normalized': len(normalized_mapping),
            'duplicates_found': len(duplicates),
            'top_peptides': normalized_counts.most_common(10),
            'duplicate_groups': duplicates,
        }
    
    @staticmethod
    def suggest_missing_mappings(peptide_names: list) -> list:
        """
        Suggerisce nomi che potrebbero necessitare mapping manuale.
        
        Args:
            peptide_names: Lista nomi da analizzare
            
        Returns:
            Lista nomi sospetti che potrebbero essere sinonimi
        """
        suspicious = []
        
        for name in set(peptide_names):
            if not name:
                continue
            
            normalized = PeptideNormalizer.normalize(name)
            name_lower = name.lower().strip()
            
            # Se normalizzato è diverso da quello nel mapping, potrebbe servire un alias
            if name_lower not in PeptideNormalizer.MANUAL_MAPPINGS:
                # Check se contiene numeri o trattini (probabile variante)
                if re.search(r'\d|-|/', name_lower):
                    suspicious.append((name, normalized))
        
        return suspicious


# Funzione helper per uso diretto
def normalize_peptide_name(raw_name: str) -> str:
    """
    Normalizza nome peptide (funzione helper).
    
    Args:
        raw_name: Nome da normalizzare
        
    Returns:
        Nome normalizzato
    """
    return PeptideNormalizer.normalize(raw_name)
