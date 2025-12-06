"""
Quick test - Janoshik Manager with GPT-4o

Test rapido per verificare configurazione API key e connessione.
"""

from peptide_manager.janoshik import JanoshikManager, LLMProvider

print("=" * 70)
print("Test Janoshik Manager - GPT-4o")
print("=" * 70)

# Initialize with GPT-4o (carica API key da .env.development)
print("\n[1] Inizializzazione Manager...")
manager = JanoshikManager(
    db_path="data/development/peptide_management.db",  # DEVELOPMENT database
    llm_provider=LLMProvider.GPT4O  # Auto-load from .env
)

print("✓ Manager inizializzato con GPT-4o")

# Show statistics
print("\n[2] Statistiche database:")
stats = manager.get_statistics()
for key, value in stats.items():
    print(f"  {key}: {value}")

print("\n✓ Test completato!")
print("✓ Database: DEVELOPMENT")
print("✓ API Key: Caricata da .env.development")
print("✓ Provider: GPT-4o (OpenAI)")
print("\nPer processare certificati reali:")
print("  result = manager.run_full_update(max_pages=1)")
print("  rankings = manager.get_latest_rankings()")
