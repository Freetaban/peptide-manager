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
        "www.homopeptide.com": "Homopeptide",
        "www.lipo-peptide.com": "Lipo Peptide",
        "lipo-peptide.com": "Lipo Peptide",
        # Innopeptide variants
        "innopeptide.com": "Innopeptide",
        "www.innopeptide.com": "Innopeptide",
        "innopeptide": "Innopeptide",
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
        "mandy bio": "Mandy Bio",  # All variants
        "peptidegurus.com": "Peptide Gurus",
        "www.peptidegurus.com": "Peptide Gurus",
        "peptidegurus": "Peptide Gurus",  # Variante senza .com
        "peptide gurus": "Peptide Gurus",  # Con spazio
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
        "https://t.me/glasscompounds": "Unknown",  # Telegram channel, not a vendor
        "t.me/": "Unknown",  # Any Telegram link
        
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
        "lilitide technology co., ltd": "Lilitide",
        "lilitide technology": "Lilitide",
        "lilitide": "Lilitide",
        "lilitide tech": "Lilitide",
        "lilitide co., ltd": "Lilitide",
        "madz-wheat": "Madz-Wheat",
        "santeria pharmaceuticals": "Santeria Pharmaceuticals",
        "retralab": "Retralab",
    }
    
    @staticmethod
    def _clean_domain_to_name(domain: str) -> str:
        """
        Converte un dominio web in un nome vendor pulito.
        
        Args:
            domain: Dominio es. "innopeptide.com" o "www.peptide-gurus.com"
            
        Returns:
            Nome pulito es. "Innopeptide" o "Peptide Gurus"
        """
        # Rimuovi www. e estensioni
        name = domain.lower()
        name = re.sub(r'^www\.', '', name)
        name = re.sub(r'\.(com|org|net|co\.uk|cn|is|io)/?$', '', name)
        
        # Sostituisci trattini con spazi
        name = name.replace('-', ' ')
        
        # Rimuovi "peptide" o "peptides" ridondanti alla fine se c'è già nel nome
        # es. "peptide peptides" → "peptide"
        
        # Title case
        name = name.title()
        
        # Fix abbreviazioni comuni
        name = re.sub(r'\bQsc\b', 'QSC', name)
        name = re.sub(r'\bKbr\b', 'KBR', name)
        name = re.sub(r'\bMtm\b', 'MTM', name)
        name = re.sub(r'\bUwa\b', 'UWA', name)
        name = re.sub(r'\bHk\b', 'HK', name)
        name = re.sub(r'\bSh\b', 'SH', name)
        name = re.sub(r'\bZlz\b', 'ZLZ', name)
        name = re.sub(r'\bZztai\b', 'ZZTAI', name)
        name = re.sub(r'\bUs\b', 'US', name)
        
        return name.strip()
    
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
        
        # 3. Rileva contatti (WhatsApp, Telegram, email) → Unknown (private individuals)
        if any(pattern in normalized for pattern in ['whatsapp', '@', 'telegram', '+31 ', '+86 ', 'wechat', 'signal', 't.me/']):
            return "Unknown"
        
        # 3b. Rileva pattern di privati (non venditori reali)
        # - Nomi personali corti (1-2 parole senza suffissi aziendali)
        # - "Mr.", "Ms.", "Dr." prefissi
        # - Nomi che iniziano con "I am" o "My name"
        # - Pattern come "John D." o "J. Smith"
        private_patterns = [
            r'^(mr|ms|mrs|dr|prof)\.?\s',  # Titoli personali
            r'^(i am|my name|hello|hi)\b',  # Frasi personali
            r'^[a-z]{2,10}\s[a-z]\.?$',  # "John D." o "Jane S"
            r'^\w+\s(from|via|through)\s',  # "John from Reddit"
            r'^(reddit|forum|discord)\s*:?',  # Social handles
            r'^\+\d{2,3}\s?\d',  # Phone numbers
            r'^[a-z]{2,8}@',  # email addresses
        ]
        if any(re.match(pattern, normalized) for pattern in private_patterns):
            return "Unknown"
        
        # 3c. Rileva URL che sono solo siti (non vendor)
        url_only_patterns = [
            r'^(http|www\.)',  # Pure URL without company name context
        ]
        # Se è un URL puro senza mapping, estrailo e normalizza
        
        # 4. Rileva URL lunghi (>40 char con slash/dots) → estrai dominio
        if len(normalized) > 40 and ('/' in normalized or normalized.count('.') >= 2):
            # Estrai dominio base
            domain_match = re.match(r'^([a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:com|org|net|co\.uk|cn|is))', normalized)
            if domain_match:
                domain = domain_match.group(1)
                # Riprova mapping con dominio
                if domain in SupplierNormalizer.MANUAL_MAPPINGS:
                    return SupplierNormalizer.MANUAL_MAPPINGS[domain]
                # Capitalizza dominio senza estensione
                return SupplierNormalizer._clean_domain_to_name(domain)
        
        # 4b. Se è un URL corto tipo "site.com", convertilo a nome pulito
        domain_match = re.match(r'^([a-z0-9-]+)\.(?:com|org|net|co\.uk|cn|is)/?$', normalized)
        if domain_match:
            domain = domain_match.group(0).rstrip('/')
            # Prima controlla mapping
            if domain in SupplierNormalizer.MANUAL_MAPPINGS:
                return SupplierNormalizer.MANUAL_MAPPINGS[domain]
            # Converti dominio a nome pulito
            return SupplierNormalizer._clean_domain_to_name(domain)
        
        # 5. Capitalizza primo carattere di ogni parola (fallback)
        result = raw_name.strip().title()
        
        # Fix abbreviazioni comuni (maiuscole complete)
        result = re.sub(r'\bQsc\b', 'QSC', result)
        result = re.sub(r'\bKbr\b', 'KBR', result)
        result = re.sub(r'\bTfc\b', 'TFC', result)
        result = re.sub(r'\bXtp\b', 'XTP', result)
        result = re.sub(r'\bZjh\b', 'ZJH', result)
        result = re.sub(r'\bMtm\b', 'MTM', result)
        result = re.sub(r'\bUwa\b', 'UWA', result)
        result = re.sub(r'\bUs\b', 'US', result)
        result = re.sub(r'\bHk\b', 'HK', result)
        result = re.sub(r'\bSh\b', 'SH', result)
        result = re.sub(r'\bZlz\b', 'ZLZ', result)
        result = re.sub(r'\bZztai\b', 'ZZTAI', result)
        
        # Fix "Of" → "of" per titoli
        result = re.sub(r'\bOf\b', 'of', result)
        
        # Fix suffissi aziendali
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
