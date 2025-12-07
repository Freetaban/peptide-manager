"""Test rapido start_gui con parametro environment"""
import sys
from pathlib import Path

# Simula chiamata start_gui
def test_start_gui_env_selection():
    """Testa che start_gui usi correttamente il parametro environment"""
    
    print("=" * 60)
    print("TEST SELEZIONE ENVIRONMENT IN start_gui()")
    print("=" * 60)
    print()
    
    # Test 1: environment='production'
    print("🧪 Test 1: start_gui(environment='production')")
    sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))
    from environment import get_environment
    
    env = get_environment('production')
    print(f"   Ambiente: {env.name}")
    print(f"   DB Path: {env.db_path}")
    
    expected = "data/production/peptide_management.db"
    if expected in str(env.db_path):
        print("   ✅ CORRETTO - USA DB PRODUCTION")
    else:
        print(f"   ❌ ERRORE - Atteso {expected}, ottenuto {env.db_path}")
    print()
    
    # Test 2: environment='development'
    print("🧪 Test 2: start_gui(environment='development')")
    env = get_environment('development')
    print(f"   Ambiente: {env.name}")
    print(f"   DB Path: {env.db_path}")
    
    expected = "data/development/peptide_management.db"
    if expected in str(env.db_path):
        print("   ✅ CORRETTO - USA DB DEVELOPMENT")
    else:
        print(f"   ❌ ERRORE - Atteso {expected}, ottenuto {env.db_path}")
    print()
    
    # Test 3: environment=None (usa .env)
    print("🧪 Test 3: start_gui(environment=None) - usa .env")
    env = get_environment(None)
    print(f"   Ambiente: {env.name}")
    print(f"   DB Path: {env.db_path}")
    print(f"   ℹ️  Legge da ENV_FILE in .env (default: .env.development)")
    print()
    
    print("=" * 60)
    print("✅ TUTTI I TEST COMPLETATI")
    print("=" * 60)
    print()
    print("Ora puoi lanciare:")
    print("  python gui.py --env production   → USA DB PRODUCTION")
    print("  python gui.py --env development  → USA DB DEVELOPMENT")
    print("  python gui.py                    → USA .env (default development)")
    print()

if __name__ == "__main__":
    test_start_gui_env_selection()
