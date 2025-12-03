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
4. Sample (full peptide/product name)
5. Manufacturer
6. Batch
7. Test Type
8. Results (ALL parameters from table - CRITICAL!)
9. Comments
10. Verification Key

IMPORTANT for Results:
- Extract EVERY parameter from Results table
- Include name, value, and unit
- If parameters in Comments (e.g. "KPV: 11.75 mg"), add to results
- Look for Purity (%), Quantity (mg), Endotoxins (EU/mg)
- Examples: {"Retatrutide": "44.33 mg", "Purity": "99.720%", "Endotoxins": "<50 EU/mg"}

Return ONLY valid JSON:
{
  "task_number": "82282",
  "testing_ordered": "02 OCT '25",
  "sample_received": "07 OCT '25",
  "analysis_conducted": "09 OCT 2025",
  "client": "www.licensedpeptides.com",
  "sample": "Retatrutide 40mg | 99.5% Purity",
  "manufacturer": "www.licensedpeptides.com",
  "batch": "reta40100926g",
  "test_type": "Assessment of a peptide vial",
  "results": {
    "Retatrutide": "44.33 mg",
    "Purity": "99.720%",
    "Endotoxins": "<50 EU/mg"
  },
  "comments": "",
  "verification_key": "I3NR16JGXTL8"
}

Empty fields use "". ONLY JSON, no other text."""
    
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
