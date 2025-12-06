"""
Configuration Helper for Janoshik API Keys

Script per configurare API keys per LLM providers in modo sicuro.
"""

import os
from pathlib import Path
from typing import Optional


def setup_api_keys():
    """Setup interattivo API keys"""
    
    print("=" * 70)
    print("Janoshik LLM Provider - API Key Configuration")
    print("=" * 70)
    
    # Trova .env file
    project_root = Path(__file__).parent.parent.parent
    env_file = project_root / ".env.development"
    
    if not env_file.exists():
        env_file = project_root / ".env"
    
    print(f"\nConfigurazione in: {env_file}")
    
    # Leggi contenuto esistente
    existing_content = ""
    if env_file.exists():
        with open(env_file, 'r') as f:
            existing_content = f.read()
    
    # Chiedi API keys
    print("\n" + "-" * 70)
    print("Inserisci le API keys (premi Enter per saltare):")
    print("-" * 70)
    
    keys = {}
    
    # OpenAI GPT-4o
    print("\n[1] OpenAI GPT-4o ($0.0125/image)")
    current = os.getenv('OPENAI_API_KEY', '')
    if current and 'OPENAI_API_KEY' in existing_content:
        print(f"    Attuale: {current[:10]}...{current[-4:]}")
    openai_key = input("    API Key (sk-...): ").strip()
    if openai_key:
        keys['OPENAI_API_KEY'] = openai_key
    
    # Anthropic Claude
    print("\n[2] Anthropic Claude 3.5 Sonnet ($0.015/image)")
    current = os.getenv('ANTHROPIC_API_KEY', '')
    if current and 'ANTHROPIC_API_KEY' in existing_content:
        print(f"    Attuale: {current[:10]}...{current[-4:]}")
    anthropic_key = input("    API Key (sk-ant-...): ").strip()
    if anthropic_key:
        keys['ANTHROPIC_API_KEY'] = anthropic_key
    
    # Google Gemini
    print("\n[3] Google Gemini 2.0 Flash (FREE)")
    current = os.getenv('GOOGLE_API_KEY', '')
    if current and 'GOOGLE_API_KEY' in existing_content:
        print(f"    Attuale: {current[:10]}...{current[-4:]}")
    google_key = input("    API Key (AI...): ").strip()
    if google_key:
        keys['GOOGLE_API_KEY'] = google_key
    
    # Ollama (opzionale)
    print("\n[4] Ollama (locale, opzionale)")
    current = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
    print(f"    Attuale: {current}")
    ollama_host = input("    Host (default: http://localhost:11434): ").strip()
    if ollama_host:
        keys['OLLAMA_HOST'] = ollama_host
    
    if not keys:
        print("\n⚠️  Nessuna key inserita. Configurazione annullata.")
        return
    
    # Aggiorna .env file
    print("\n" + "-" * 70)
    print("Aggiornamento .env file...")
    
    # Rimuovi vecchie keys
    lines = existing_content.split('\n')
    new_lines = []
    janoshik_section_found = False
    
    for line in lines:
        # Salta vecchie keys Janoshik
        if any(key in line for key in ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'GOOGLE_API_KEY', 'OLLAMA_HOST']):
            if '# Janoshik' in existing_content and not janoshik_section_found:
                continue
        
        # Salta sezione Janoshik esistente
        if '# Janoshik LLM Providers' in line:
            janoshik_section_found = True
            continue
        
        new_lines.append(line)
    
    # Aggiungi nuova sezione Janoshik
    if new_lines and new_lines[-1].strip():
        new_lines.append('')
    
    new_lines.append('# Janoshik LLM Providers')
    for key, value in keys.items():
        new_lines.append(f'{key}={value}')
    
    # Scrivi file
    new_content = '\n'.join(new_lines)
    
    with open(env_file, 'w') as f:
        f.write(new_content)
    
    print(f"✓ API keys salvate in {env_file}")
    
    # Mostra riepilogo
    print("\n" + "=" * 70)
    print("Configurazione completata!")
    print("=" * 70)
    print("\nAPI Keys configurate:")
    for key in keys:
        provider = {
            'OPENAI_API_KEY': 'OpenAI GPT-4o',
            'ANTHROPIC_API_KEY': 'Anthropic Claude',
            'GOOGLE_API_KEY': 'Google Gemini',
            'OLLAMA_HOST': 'Ollama (locale)'
        }[key]
        print(f"  ✓ {provider}")
    
    print("\n" + "-" * 70)
    print("Uso:")
    print("-" * 70)
    print("""
# Metodo 1: Caricamento automatico da .env
from peptide_manager.janoshik import JanoshikManager, LLMProvider

manager = JanoshikManager(
    db_path="data/production/peptide_management.db",
    llm_provider=LLMProvider.GPT4O  # Usa automaticamente OPENAI_API_KEY da .env
)

# Metodo 2: API key esplicita
manager = JanoshikManager(
    db_path="data/production/peptide_management.db",
    llm_provider=LLMProvider.GPT4O,
    llm_api_key="sk-..."  # Override .env
)
""")


def test_api_key(provider: str = "openai"):
    """Test API key specifica"""
    from dotenv import load_dotenv
    
    # Carica .env
    load_dotenv()
    
    print(f"\nTest API Key: {provider}")
    print("-" * 70)
    
    if provider == "openai":
        key = os.getenv('OPENAI_API_KEY')
        if not key:
            print("❌ OPENAI_API_KEY non trovata in .env")
            return False
        
        print(f"Key: {key[:10]}...{key[-4:]}")
        
        try:
            from openai import OpenAI
            client = OpenAI(api_key=key)
            
            # Test con modello economico
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Say 'test ok'"}],
                max_tokens=10
            )
            
            print(f"✓ Test riuscito: {response.choices[0].message.content}")
            return True
            
        except Exception as e:
            print(f"❌ Test fallito: {e}")
            return False
    
    elif provider == "google":
        key = os.getenv('GOOGLE_API_KEY')
        if not key:
            print("❌ GOOGLE_API_KEY non trovata in .env")
            return False
        
        print(f"Key: {key[:10]}...{key[-4:]}")
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=key)
            
            model = genai.GenerativeModel('gemini-2.0-flash-exp')
            response = model.generate_content('Say "test ok"')
            
            print(f"✓ Test riuscito: {response.text}")
            return True
            
        except Exception as e:
            print(f"❌ Test fallito: {e}")
            return False


def show_current_config():
    """Mostra configurazione attuale"""
    from dotenv import load_dotenv
    
    load_dotenv()
    
    print("\nConfigurazione Attuale")
    print("=" * 70)
    
    providers = {
        'OPENAI_API_KEY': 'OpenAI GPT-4o',
        'ANTHROPIC_API_KEY': 'Anthropic Claude',
        'GOOGLE_API_KEY': 'Google Gemini',
        'OLLAMA_HOST': 'Ollama'
    }
    
    for key, name in providers.items():
        value = os.getenv(key)
        if value:
            if 'HOST' in key:
                print(f"✓ {name}: {value}")
            else:
                print(f"✓ {name}: {value[:10]}...{value[-4:]}")
        else:
            print(f"✗ {name}: Non configurato")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Janoshik API Key Configuration")
    parser.add_argument('--setup', action='store_true', help='Setup API keys interattivo')
    parser.add_argument('--test', type=str, choices=['openai', 'google'], help='Test API key')
    parser.add_argument('--show', action='store_true', help='Mostra configurazione attuale')
    
    args = parser.parse_args()
    
    if args.setup:
        setup_api_keys()
    elif args.test:
        test_api_key(args.test)
    elif args.show:
        show_current_config()
    else:
        setup_api_keys()
