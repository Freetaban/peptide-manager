"""
LLM Multi-Provider System per estrazione dati certificati Janoshik.

Supporta:
- OpenAI GPT-4o Vision
- Anthropic Claude 3.5 Sonnet
- Google Gemini 2.0 Flash
- Ollama (llama3.2-vision) locale
"""

import base64
import json
import os
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Dict, Optional


class LLMProvider(Enum):
    """Provider LLM disponibili"""
    GPT4O = "gpt-4o"
    CLAUDE_SONNET = "claude-3-5-sonnet-20241022"
    GEMINI_FLASH = "gemini-2.0-flash-exp"
    OLLAMA_LLAMA = "llama3.2-vision"


class BaseLLMExtractor(ABC):
    """Classe base astratta per estrattori LLM"""
    
    EXTRACTION_PROMPT = """Analyze this Janoshik analytical certificate and extract ALL data as JSON.

Extract:
1. Task Number
2. Testing ordered, Sample received, Analysis conducted (dates)
3. Client (supplier/vendor name)
4. Sample (full peptide/product name - EXACTLY as written)
5. Peptide Name (STANDARDIZED - extract base peptide name)
   - Remove dosages, formulations, variants
   - Standardize spelling: BPC-157/BPC157/BPC 157 → "BPC157"
   - Examples: "Tirzepatide", "Semaglutide", "BPC157", "TB500", "HGH"
6. Quantity Nominal (declared quantity from product name)
   - Extract numeric value only (e.g., "30mg" → 30)
7. Unit of Measure (from product name)
   - Common: "mg", "mcg", "IU", "g"
   - Standardize: mcg/µg → "mcg", IU/iu → "IU"
8. Manufacturer
9. Batch
10. Test Type - IMPORTANT: Classify into ONE category:
   - "purity" if testing peptide purity/quantity (default)
   - "endotoxin" if testing endotoxins (EU/mg)
   - "heavy_metals" if testing heavy metals (Pb, Cd, Hg, As)
   - "microbiology" if testing TAMC/TYMC (bacteria/yeast counts)
11. Results (ALL parameters from table - CRITICAL!)
12. Heavy Metals (if present): Pb, Cd, Hg, As in ppm
13. Microbiology (if present): TAMC and TYMC counts in CFU/g
14. Endotoxins (if present): value in EU/mg
15. Comments
16. Verification Key

IMPORTANT for Results:
- Extract EVERY parameter from Results table
- Include name, value, and unit
- If parameters in Comments (e.g. "KPV: 11.75 mg"), add to results
- Look for Purity (%), Quantity (mg), Endotoxins (EU/mg)
- For heavy metals test: extract Pb, Cd, Hg, As values
- For microbiology test: extract TAMC (Total Aerobic Microbial Count) and TYMC (Total Yeast/Mold Count)
- Examples: {"Retatrutide": "44.33 mg", "Purity": "99.720%", "Endotoxins": "<50 EU/mg"}

IMPORTANT for Peptide Name Standardization:
- GLP-1 Agonists: Tirzepatide, Semaglutide, Retatrutide, Liraglutide, Cagrilintide
- Repair Peptides: BPC157 (all variants), TB500, KPV, GHK-Cu
- Growth Hormones: HGH (Somatropin/Qitrope), Ipamorelin, CJC-1295, Tesamorelin
- Anti-Aging: NAD+, Epithalon, MOTS-C, NMN
- Nootropics: Selank, Semax, P21
- Metabolic: AOD-9604, 5-Amino-1MQ
- Immune: Thymosin-Alpha-1, LL-37
- Sexual: PT-141, Melanotan-II
- Other: DSIP, HCG, IGF-1, Enclomiphene

Return ONLY valid JSON:
{
  "task_number": "82282",
  "testing_ordered": "02 OCT '25",
  "sample_received": "07 OCT '25",
  "analysis_conducted": "09 OCT 2025",
  "client": "www.licensedpeptides.com",
  "sample": "Retatrutide 40mg | 99.5% Purity",
  "peptide_name": "Retatrutide",
  "quantity_nominal": 40,
  "unit_of_measure": "mg",
  "manufacturer": "www.licensedpeptides.com",
  "batch": "reta40100926g",
  "test_type": "Assessment of a peptide vial",
  "test_category": "purity",
  "results": {
    "Retatrutide": "44.33 mg",
    "Purity": "99.720%"
  },
  "endotoxin_level": null,
  "heavy_metals": null,
  "microbiology_tamc": null,
  "microbiology_tymc": null,
  "comments": "",
  "verification_key": "I3NR16JGXTL8"
}

Example with HGH (IU units):
{
  "sample": "Qitrope 10 IU",
  "peptide_name": "HGH",
  "quantity_nominal": 10,
  "unit_of_measure": "IU"
}

Example with BPC-157 variants:
{
  "sample": "BPC-157 5mg",
  "peptide_name": "BPC157",
  "quantity_nominal": 5,
  "unit_of_measure": "mg"
}

For endotoxin test example:
{
  "test_category": "endotoxin",
  "endotoxin_level": 25.5,
  "results": {"Endotoxins": "25.5 EU/mg"}
}

For heavy metals test example:
{
  "test_category": "heavy_metals",
  "heavy_metals": {"Pb": 0.5, "Cd": 0.1, "Hg": 0.05, "As": 0.2},
  "results": {"Pb": "0.5 ppm", "Cd": "0.1 ppm", "Hg": "0.05 ppm", "As": "0.2 ppm"}
}

For microbiology test example:
{
  "test_category": "microbiology",
  "microbiology_tamc": 100,
  "microbiology_tymc": 50,
  "results": {"TAMC": "100 CFU/g", "TYMC": "50 CFU/g"}
}

For microbiology "Pass" result (no contamination):
{
  "test_category": "microbiology",
  "microbiology_tamc": 0,
  "microbiology_tymc": 0,
  "results": {"TAMC": "Pass", "TYMC": "Pass"}
}

For heavy metals "not detected" result:
{
  "test_category": "heavy_metals",
  "heavy_metals": {"Pb": 0.0, "Cd": 0.0, "Hg": 0.0, "As": 0.0},
  "results": {"Pb": "not detected", "Cd": "not detected", "Hg": "not detected", "As": "not detected"}
}

Empty fields use null. ONLY JSON, no other text."""
    
    @abstractmethod
    def extract_certificate_data(self, image_path: str) -> Dict:
        """
        Estrae dati da certificato.
        
        Args:
            image_path: Percorso immagine certificato
            
        Returns:
            Dict con dati estratti
        """
        pass
    
    @abstractmethod
    def get_cost_per_image(self) -> float:
        """Ritorna costo stimato per immagine"""
        pass
    
    @abstractmethod
    def supports_batch(self) -> bool:
        """Supporta batch processing?"""
        pass
    
    def _parse_json_response(self, response_text: str) -> Dict:
        """Parse risposta LLM in JSON"""
        response_text = response_text.strip()
        
        # Rimuovi markdown code blocks se presenti
        if response_text.startswith('```'):
            lines = response_text.split('\n')
            response_text = '\n'.join(lines[1:-1])
            if response_text.startswith('json'):
                response_text = response_text[4:].strip()
        
        return json.loads(response_text)


class GPT4oExtractor(BaseLLMExtractor):
    """OpenAI GPT-4o Vision extractor"""
    
    def __init__(self, api_key: Optional[str] = None):
        if not api_key:
            api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY non trovata")
        
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o"
    
    def extract_certificate_data(self, image_path: str) -> Dict:
        """Estrae dati con GPT-4o Vision"""
        
        # Codifica immagine
        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": self.EXTRACTION_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_data}"}
                    }
                ]
            }],
            max_tokens=2000,
            temperature=0
        )
        
        return self._parse_json_response(response.choices[0].message.content)
    
    def get_cost_per_image(self) -> float:
        return 0.0125  # Stimato
    
    def supports_batch(self) -> bool:
        return True


class ClaudeSonnetExtractor(BaseLLMExtractor):
    """Anthropic Claude 3.5 Sonnet extractor"""
    
    def __init__(self, api_key: Optional[str] = None):
        if not api_key:
            api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY non trovata")
        
        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20241022"
    
    def extract_certificate_data(self, image_path: str) -> Dict:
        """Estrae dati con Claude Sonnet"""
        
        with open(image_path, 'rb') as f:
            image_data = base64.standard_b64encode(f.read()).decode('utf-8')
        
        message = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": self.EXTRACTION_PROMPT
                    }
                ],
            }]
        )
        
        return self._parse_json_response(message.content[0].text)
    
    def get_cost_per_image(self) -> float:
        return 0.015  # Stimato
    
    def supports_batch(self) -> bool:
        return True


class GeminiFlashExtractor(BaseLLMExtractor):
    """Google Gemini 2.0 Flash extractor"""
    
    def __init__(self, api_key: Optional[str] = None):
        if not api_key:
            api_key = os.environ.get('GOOGLE_API_KEY')
        if not api_key:
            raise ValueError("GOOGLE_API_KEY non trovata")
        
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    def extract_certificate_data(self, image_path: str) -> Dict:
        """Estrae dati con Gemini Flash"""
        
        from PIL import Image
        img = Image.open(image_path)
        
        response = self.model.generate_content([
            self.EXTRACTION_PROMPT,
            img
        ])
        
        return self._parse_json_response(response.text)
    
    def get_cost_per_image(self) -> float:
        return 0.0  # Free tier generoso
    
    def supports_batch(self) -> bool:
        return False  # Rate limits più stretti


class OllamaExtractor(BaseLLMExtractor):
    """Ollama local LLM extractor"""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.model = "llama3.2-vision"
    
    def extract_certificate_data(self, image_path: str) -> Dict:
        """Estrae dati con Ollama locale"""
        
        import requests
        
        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": self.EXTRACTION_PROMPT,
                "images": [image_data],
                "stream": False
            },
            timeout=120
        )
        
        if response.status_code != 200:
            raise RuntimeError(f"Ollama error: {response.text}")
        
        return self._parse_json_response(response.json()['response'])
    
    def get_cost_per_image(self) -> float:
        return 0.0  # Locale, gratis
    
    def supports_batch(self) -> bool:
        return True  # Locale, no rate limits


def get_llm_extractor(
    provider: LLMProvider,
    api_key: Optional[str] = None,
    **kwargs
) -> BaseLLMExtractor:
    """
    Factory per creare estrattore LLM.
    
    Args:
        provider: Provider LLM da usare
        api_key: API key (opzionale se in env)
        **kwargs: Parametri aggiuntivi (es. ollama_url)
        
    Returns:
        Estrattore LLM configurato
        
    Raises:
        ValueError: Se provider non supportato o configurazione invalida
    """
    
    if provider == LLMProvider.GPT4O:
        return GPT4oExtractor(api_key)
    
    elif provider == LLMProvider.CLAUDE_SONNET:
        return ClaudeSonnetExtractor(api_key)
    
    elif provider == LLMProvider.GEMINI_FLASH:
        return GeminiFlashExtractor(api_key)
    
    elif provider == LLMProvider.OLLAMA_LLAMA:
        base_url = kwargs.get('ollama_url', 'http://localhost:11434')
        return OllamaExtractor(base_url)
    
    else:
        raise ValueError(f"Provider non supportato: {provider}")
