"""
Supplier Name Normalizer - Janoshik

Normalizza nomi supplier estratti da certificati Janoshik per gestire variazioni:
- URL/siti web → nome pulito
- Contatti (WhatsApp, Telegram) → "Unknown"
- Slogan promozionali → pulizia
- Variazioni ortografiche → standardizzazione
"""

import re
from typing import Optional, Dict


class SupplierNormalizer:
    """Normalizzatore nomi supplier Janoshik"""
    
    # Mapping manuale variazioni comuni → nome standard
    MANUAL_MAPPINGS = {
        # URL-based vendors
        "homopeptide.com": "Homopeptide",
        "www.lipo-peptide.com": "Lipo Peptide",
        "lipo-peptide.com": "Lipo Peptide",
        "peptidegurus.com": "Peptide Gurus",
        "www.peptidegurus.com": "Peptide Gurus",
        "peptidegurus": "Peptide Gurus",  # Variante senza .com
        "royal-peptides.com": "Royal Peptides",
        "royal-peptides.com usa & canada": "Royal Peptides",
        "www.rayshine-peptide.com": "Rayshine Peptides",
        "rayshine-peptide.com": "Rayshine Peptides",
        "rayshine-peptide.com/": "Rayshine Peptides",  # With trailing slash
        "rayshine peptides": "Rayshine Peptides",
        "https://www.rayshine-peptide.com/": "Rayshine Peptides",
        "cocerpeptides.com": "Cocer Peptides",
        "mtmeipeptide.com": "MTM Peptide",
        "protopeptide.is": "Proto Peptide",
        "usroids.com": "US Roids",
        "texpeptide.com": "Tex Peptide",
        "www.meipeptide.com": "Mei Peptide",
        "meipeptide.com": "Mei Peptide",
        "www.meipepetide.com": "Mei Peptide",  # Typo variant
        "meipepetide.com": "Mei Peptide",
        "www.mandybio.com": "Mandy Bio",
        "mandybio.com": "Mandy Bio",
        "regenix peptides": "Regenix Peptides",
        "regenix": "Regenix Peptides",
        "biotek peptides": "Biotek Peptides",
        "aminopure peptides": "Aminopure Peptides",
        "peptiatlas": "Peptiatlas",
        "www.peptiatlas.com": "Peptiatlas",
        "fenrilabs.co.uk": "Fenrilabs",
        "www.licensedpeptides.com": "Licensed Peptides",
        "licensedpeptides.com": "Licensed Peptides",
        "www.reta-peptide.com": "Reta Peptide",
        "reta-peptide.com": "Reta Peptide",
        "reta-peptide": "Reta Peptide",
        "retaeu netherlands": "Reta Peptide",  # Same vendor, EU branch
        "www.qinglishangmao.com": "Qinglishangmao",
        "www.shpeptide.com": "SH Peptide",
        "www.uwa-biotech.com": "UWA Biotech",
        "www.ywaozuo.com": "Ywaozuo",
        "researchchem.is": "Research Chem",
        "researchism": "Researchism",
        "puruspeptides.com": "Purus Peptides",
        "ptb(peptronix.com)": "Peptronix",
        
        # Shopify stores
        "https://badandboujeeoppat.myshopify.com/": "Bad And Boujee",
        
        # Mai peptides variants
        "https://mai-peptides.com": "Mai Peptides",
        "mai-peptides.com": "Mai Peptides",
        
        # ZZTAI variants  
        "https://zztai-tech.com/": "ZZTAI Tech",
        "zztai-tech.com": "ZZTAI Tech",
        
        # Sigmatech variants
        "https://www.sigmatech-peptide.com/": "Sigmatech Peptide",
        "sigmatech-peptide.com": "Sigmatech Peptide",
        
        # Peptides of London
        "https://www.peptidesoflondon.com/": "Peptides of London",
        "peptidesoflondon.com": "Peptides of London",
        
        # Lipo peptide variants
        "https://www.lipo-peptide.com/": "Lipo Peptide",
        
        # Chinese URL-based (keep as-is for now, hard to identify)
        "http://www.hemanpeptide.com/": "Heman Peptide",
        "http://www.hkpeptide.com/": "HK Peptide",
        "http://www.sahepeptides.com/": "Sahe Peptides",
        "http://www.zlzpeptide.com": "ZLZ Peptide",
        "http://www.zlzpeptide.com/": "ZLZ Peptide",
        "http://www.zyzhuoyanlab.com/": "Zyzhuo Yan Lab",
        
        # Vendor con nomi multipli
        "qsc": "QSC",
        "q s c": "QSC",
        "qingdao sigma chemical": "QSC",
        
        # Vendor cinesi
        "shanghai alimopeptide biotechnology co., ltd": "Shanghai Alimopeptide",
        "jinan elitepeptide chemical co., ltd.": "Jinan Elitepeptide",
        "jilin qijian biotechnology co., ltd": "Jilin Qijian",
        "wuhan wansheng bio": "Wuhan Wansheng",
        "yiwu weide trading co., ltd": "Yiwu Weide Trading",
        
        # Vendor con slogan
        "we are the peptidesciences of peptides in china.": "PeptideSciences China",
        
        # Telegram handles
        "@thegreyhq (telegram)": "Unknown",
        "@thegreyhq": "Unknown",
        
        # WhatsApp
        "whatsapp +31 6 22738233": "Unknown",
        
        # UK/EU vendors
        "eros labs": "Eros Labs",
        "eros peptides": "Eros Peptides",
        "made by alluvi.org": "Alluvi",
        "alluvi health care": "Alluvi",  # Same vendor
        
        # Peptira variants
        "peptira": "Peptira",
        "peptira llc": "Peptira",
        
        # Altri
        "unknown": "Unknown",
        "bioamino labs": "BioAmino Labs",
        "cellpept research": "Cellpept Research",
        "alpha biopharma": "Alpha BioPharma",
        "alpha pro": "Alpha Pro",
        "good": "GOOD",
        "kbr": "KBR",
        "xtp": "XTP",
        "zjh": "ZJH",
        "tfc": "TFC",
        "modern research llc": "Modern Research",
        "penguin peptides": "Penguin Peptides",
        "raw pharma": "Raw Pharma",
        "lunarbiotech": "Lunarbiotech",
        "allen biotechnology": "Allen Biotechnology",
        "dragon pharma": "Dragon Pharma",
        "tirzeplab": "Tirzeplab",
        "xenolabs": "Xenolabs",
        "lilitide technology co., ltd": "Lilitide Technology",
        "madz-wheat": "Madz-Wheat",
        "santeria pharmaceuticals": "Santeria Pharmaceuticals",
        "retralab": "Retralab",
    }
    
    @staticmethod
    def normalize(raw_name: str) -> str:
        """
        Normalizza nome supplier.
        
        Args:
            raw_name: Nome estratto da certificato
            
        Returns:
            Nome normalizzato
        """
        if not raw_name or not isinstance(raw_name, str):
            return "Unknown"
        
        # Trim e lowercase per matching
        normalized = raw_name.strip().lower()
        
        # 1. Check manual mapping
        if normalized in SupplierNormalizer.MANUAL_MAPPINGS:
            return SupplierNormalizer.MANUAL_MAPPINGS[normalized]
        
        # 2. Rimuovi protocolli URL
        normalized = re.sub(r'^https?://', '', normalized)
        normalized = re.sub(r'^www\.', '', normalized)
        
        # Check di nuovo dopo pulizia URL
        if normalized in SupplierNormalizer.MANUAL_MAPPINGS:
            return SupplierNormalizer.MANUAL_MAPPINGS[normalized]
        
        # 3. Rileva contatti (WhatsApp, Telegram, email) → Unknown
        if any(pattern in normalized for pattern in ['whatsapp', '@', 'telegram', '+31 ', '+86 ']):
            return "Unknown"
        
        # 4. Rileva URL lunghi (>40 char con slash/dots) → estrai dominio
        if len(normalized) > 40 and ('/' in normalized or normalized.count('.') >= 2):
            # Estrai dominio base
            domain_match = re.match(r'^([a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:com|org|net|co\.uk|cn))', normalized)
            if domain_match:
                domain = domain_match.group(1)
                # Riprova mapping con dominio
                if domain in SupplierNormalizer.MANUAL_MAPPINGS:
                    return SupplierNormalizer.MANUAL_MAPPINGS[domain]
                # Capitalizza dominio senza estensione
                return domain.replace('.com', '').replace('.org', '').replace('-', ' ').title()
        
        # 5. Capitalizza primo carattere di ogni parola (fallback)
        result = raw_name.strip().title()
        
        # Fix abbreviazioni comuni (maiuscole)
        result = re.sub(r'\bQsc\b', 'QSC', result)
        result = re.sub(r'\bKbr\b', 'KBR', result)
        result = re.sub(r'\bTfc\b', 'TFC', result)
        result = re.sub(r'\bXtp\b', 'XTP', result)
        result = re.sub(r'\bZjh\b', 'ZJH', result)
        result = re.sub(r'\bCo\.,\sLtd', 'Co., Ltd', result)
        result = re.sub(r'\bLtd\b', 'Ltd', result)
        result = re.sub(r'\bLlc\b', 'LLC', result)
        result = re.sub(r'\bInc\b', 'Inc', result)
        
        return result
    
    @staticmethod
    def extract_website(raw_name: str) -> Optional[str]:
        """
        Estrae sito web se presente nel nome.
        
        Args:
            raw_name: Nome estratto
            
        Returns:
            URL pulito o None
        """
        if not raw_name:
            return None
        
        # Cerca URL completo
        url_match = re.search(r'(https?://[^\s]+)', raw_name)
        if url_match:
            return url_match.group(1).rstrip('/')
        
        # Cerca dominio
        domain_match = re.search(r'([a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:com|org|net|co\.uk|cn))', raw_name.lower())
        if domain_match:
            domain = domain_match.group(1)
            return f"https://{domain}"
        
        return None
    
    @staticmethod
    def get_normalization_stats(supplier_names: list) -> Dict:
        """
        Analizza lista nomi supplier e mostra statistiche normalizzazione.
        
        Args:
            supplier_names: Lista nomi da analizzare
            
        Returns:
            Dict con statistiche
        """
        stats = {
            'total': len(supplier_names),
            'unique_raw': len(set(supplier_names)),
            'unique_normalized': 0,
            'url_based': 0,
            'contact_based': 0,
            'unknown': 0,
            'mappings': {},
        }
        
        normalized_set = set()
        for raw_name in supplier_names:
            normalized = SupplierNormalizer.normalize(raw_name)
            normalized_set.add(normalized)
            
            if normalized not in stats['mappings']:
                stats['mappings'][normalized] = []
            if raw_name not in stats['mappings'][normalized]:
                stats['mappings'][normalized].append(raw_name)
            
            if 'http' in raw_name.lower() or '.com' in raw_name.lower():
                stats['url_based'] += 1
            elif any(p in raw_name.lower() for p in ['whatsapp', '@', 'telegram']):
                stats['contact_based'] += 1
            elif normalized == "Unknown":
                stats['unknown'] += 1
        
        stats['unique_normalized'] = len(normalized_set)
        
        return stats


def normalize_supplier_name(raw_name: str) -> str:
    """
    Helper function - normalizza nome supplier.
    
    Args:
        raw_name: Nome da normalizzare
        
    Returns:
        Nome normalizzato
    """
    return SupplierNormalizer.normalize(raw_name)
