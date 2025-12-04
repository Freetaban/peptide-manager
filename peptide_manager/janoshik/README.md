# Janoshik Supplier Ranking System

Sistema automatico per monitoraggio e ranking dei supplier di peptidi basato su certificati pubblici di analisi Janoshik.

## 🎯 Obiettivo

Identificare supplier "hot" (affidabili, attivi, alta qualità) mediante analisi quantitativa multi-parametrica dei certificati CoA pubblici su janoshik.com/public/.

---

## 🏗️ Architettura

```
peptide_manager/janoshik/
├── scraper.py              # Web scraping janoshik.com/public/
├── extractor.py            # Estrazione dati con LLM
├── llm_providers.py        # Multi-provider LLM (GPT-4o, Claude, Gemini, Ollama)
├── scorer.py               # Algoritmo scoring 5 componenti
├── manager.py              # Orchestrator workflow completo
├── models/                 # Data models
│   ├── janoshik_certificate.py
│   └── supplier_ranking.py
├── repositories/           # Database CRUD
│   ├── certificate_repository.py
│   └── ranking_repository.py
└── example_*.py            # Script demo
```

---

## 📊 Scoring Algorithm v1.1

**Formula**:
```
total_score = volume(25%) + quality(35%) + consistency(15%) + recency(15%) + endotoxin(10%)
```

### Componenti

1. **Volume Score (25%)**
   - Numero totale certificati
   - Bonus attività recente (+10 se ≥3 cert/30d)

2. **Quality Score (35%)**
   - Purity avg/min
   - Penalty -20 se min < 95%

3. **Consistency Score (15%)**
   - Std deviation purity
   - Bonus +10 se testing regolare (gap < 60d)

4. **Recency Score (15%)**
   - Days since last certificate
   - Bonus +15 se ≥2 cert/30d

5. **Endotoxin Score (10%)** ⭐ NEW
   - EU/mg levels (100 se <10, 50 neutro se no data)
   - Bonus +5 se ≥5 certificati con test

### Interpretazione

| Score | Badge | Label | Descrizione |
|-------|-------|-------|-------------|
| ≥80 | 🔥 | HOT | Top tier, altamente affidabile |
| 60-79 | ✅ | Buono | Affidabile, qualità consistente |
| 40-59 | ⚠️ | Mediocre | Da valutare, qualità variabile |
| <40 | ❌ | Scarso | Red flag, evitare |

---

## 🚀 Quick Start

### 1. Installation

```bash
pip install -r requirements.txt
```

### 2. Run Migration

```sql
-- Apply migration 008
sqlite3 data/production/peptide_management.db < migrations/008_janoshik_supplier_ranking.sql
```

### 3. Usage

#### Option A: Using Manager (Recommended)

```python
from peptide_manager.janoshik import JanoshikManager, LLMProvider

# Initialize
manager = JanoshikManager(
    db_path="data/production/peptide_management.db",
    llm_provider=LLMProvider.GEMINI_FLASH,  # Free
    llm_api_key="YOUR_API_KEY"
)

# Run full update (scraping + extraction + scoring)
result = manager.run_full_update(max_pages=5)

# Get top 10 suppliers
rankings = manager.get_latest_rankings(top_n=10)

for ranking in rankings:
    print(f"#{ranking.rank_position} {ranking.get_quality_badge()} {ranking.supplier_name}")
    print(f"  Score: {ranking.total_score:.1f}/100")
```

#### Option B: Manual Workflow

```python
from peptide_manager.janoshik import (
    JanoshikScraper, JanoshikExtractor, SupplierScorer,
    get_llm_extractor, LLMProvider
)

# 1. Scraping
scraper = JanoshikScraper()
certificates = scraper.scrape_and_download_all(max_pages=2)

# 2. Extraction
llm = get_llm_extractor(LLMProvider.GEMINI_FLASH, api_key="...")
extractor = JanoshikExtractor(llm_provider=llm)
image_paths = [cert['file_path'] for cert in certificates]
extracted_data = extractor.process_certificates(image_paths)

# 3. Scoring
scorer = SupplierScorer()
rankings = scorer.calculate_rankings(extracted_data)
print(rankings)
```

---

## 🤖 LLM Providers

| Provider | Model | Cost/Image | Quality | Speed | Notes |
|----------|-------|------------|---------|-------|-------|
| **Gemini Flash** | 2.0 Flash | **Free** | ⭐⭐⭐⭐ | Fast | ✅ Default |
| OpenAI | GPT-4o | $0.0125 | ⭐⭐⭐⭐⭐ | Medium | Best quality |
| Anthropic | Claude 3.5 | $0.015 | ⭐⭐⭐⭐⭐ | Medium | Best reasoning |
| Ollama | llama3.2-vision | **Free** | ⭐⭐⭐ | Slow | Local |

### Cost Estimation

```python
manager = JanoshikManager(...)
costs = manager.get_cost_estimate(num_certificates=100)
# {'GPT4O': 1.25, 'CLAUDE_SONNET': 1.50, 'GEMINI_FLASH': 0.0, 'OLLAMA_LLAMA': 0.0}
```

---

## 💾 Database Schema

### janoshik_certificates (20 columns)

```sql
CREATE TABLE janoshik_certificates (
    id INTEGER PRIMARY KEY,
    task_number TEXT UNIQUE NOT NULL,
    supplier_name TEXT NOT NULL,
    peptide_name TEXT NOT NULL,
    purity_percentage REAL,
    quantity_tested_mg REAL,
    endotoxin_level REAL,  -- EU/mg
    image_hash TEXT UNIQUE,
    -- ... 12 more columns
);
```

### supplier_rankings (24 columns)

```sql
CREATE TABLE supplier_rankings (
    id INTEGER PRIMARY KEY,
    supplier_name TEXT NOT NULL,
    total_score REAL NOT NULL,
    rank_position INTEGER,
    volume_score REAL,
    quality_score REAL,
    consistency_score REAL,
    recency_score REAL,
    endotoxin_score REAL,
    -- ... 15 more columns
);
```

---

## 📈 API Reference

### JanoshikManager

```python
manager = JanoshikManager(
    db_path: str,
    llm_provider: LLMProvider = LLMProvider.GEMINI_FLASH,
    llm_api_key: Optional[str] = None
)

# Main workflow
result = manager.run_full_update(
    max_pages: Optional[int] = None,
    progress_callback: Optional[Callable] = None
) -> Dict

# Queries
rankings = manager.get_latest_rankings(top_n: int = 10) -> List[SupplierRanking]
certificates = manager.get_supplier_certificates(supplier_name: str) -> List[JanoshikCertificate]
trend = manager.get_supplier_trend(supplier_name: str) -> List[Dict]
stats = manager.get_statistics() -> Dict

# Operations
rankings_df = manager.recalculate_rankings() -> pd.DataFrame
output_path = manager.export_rankings_to_csv(output_path: str) -> str
deleted = manager.cleanup_old_rankings(keep_last_n: int = 10) -> int
```

### Repositories

```python
from peptide_manager.janoshik.repositories import (
    JanoshikCertificateRepository,
    SupplierRankingRepository
)

cert_repo = JanoshikCertificateRepository(db_path)
cert_id = cert_repo.insert(certificate)
certificates = cert_repo.get_by_supplier("amopure.net")
exists = cert_repo.exists_by_image_hash(hash)

ranking_repo = SupplierRankingRepository(db_path)
rankings = ranking_repo.get_latest(limit=10)
trend = ranking_repo.get_supplier_trend("amopure.net")
```

---

## 📝 Examples

### Example 1: Quick Update

```bash
python peptide_manager/janoshik/example_manager.py
```

### Example 2: Recalculate Only

```bash
python peptide_manager/janoshik/example_manager.py --recalculate
```

### Example 3: Supplier Detail

```bash
python peptide_manager/janoshik/example_manager.py --supplier "amopure.net"
```

### Example 4: Custom Workflow

```python
from peptide_manager.janoshik import (
    JanoshikManager, LLMProvider
)

manager = JanoshikManager(
    db_path="data/production/peptide_management.db",
    llm_provider=LLMProvider.GPT4O,  # Use GPT-4o for best quality
    llm_api_key="sk-..."
)

# Progress tracking
def progress(stage, message):
    print(f"[{stage}] {message}")

result = manager.run_full_update(
    max_pages=10,
    progress_callback=progress
)

# Export results
manager.export_rankings_to_csv("rankings.csv")

# Cleanup
manager.cleanup_old_rankings(keep_last_n=5)
```

---

## 🧪 Testing

```bash
# Test scorer with dummy data
python peptide_manager/janoshik/example_pipeline.py --quick-scorer

# Test scraper (no LLM needed)
python peptide_manager/janoshik/example_pipeline.py --quick-scraper
```

---

## 📚 Documentation

- **SCORING_ALGORITHM.md**: Detailed algorithm explanation with examples
- **ENDOTOXIN_INTEGRATION.md**: Changelog for endotoxin feature
- **example_pipeline.py**: Full end-to-end demo
- **example_manager.py**: Simplified manager demo

---

## 🛠️ Configuration

### Environment Variables

```bash
# LLM API Keys
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="AI..."

# Ollama (if using local)
export OLLAMA_HOST="http://localhost:11434"
```

### Storage Directories

```
data/janoshik/
├── images/          # Downloaded certificate images
├── cache/           # Processing cache
└── rankings/        # Exported ranking CSV files
```

---

## ⚙️ Advanced Usage

### Custom LLM Provider

```python
from peptide_manager.janoshik.llm_providers import BaseLLMExtractor

class CustomLLMExtractor(BaseLLMExtractor):
    def extract_certificate_data(self, image_path: str) -> Dict:
        # Your implementation
        pass
    
    def get_cost_per_image(self) -> float:
        return 0.01
    
    def supports_batch(self) -> bool:
        return True
```

### Custom Scoring Weights

```python
from peptide_manager.janoshik import SupplierScorer

scorer = SupplierScorer()
# Override weights
scorer.WEIGHT_QUALITY = 0.50  # Prioritize quality
scorer.WEIGHT_ENDOTOXIN = 0.15  # More weight to endotoxins
scorer.WEIGHT_VOLUME = 0.15
scorer.WEIGHT_CONSISTENCY = 0.10
scorer.WEIGHT_RECENCY = 0.10

rankings = scorer.calculate_rankings(certificates)
```

---

## 🚨 Troubleshooting

### Issue: Import errors

```bash
# Install missing dependencies
pip install openai anthropic google-generativeai requests beautifulsoup4 pillow
```

### Issue: Database not found

```bash
# Ensure database exists and migration applied
ls data/production/peptide_management.db
sqlite3 data/production/peptide_management.db < migrations/008_janoshik_supplier_ranking.sql
```

### Issue: LLM API errors

```python
# Check API key is set
manager = JanoshikManager(
    db_path="...",
    llm_provider=LLMProvider.GEMINI_FLASH,
    llm_api_key="YOUR_KEY_HERE"  # Explicit key
)

# Or use environment variable
import os
os.environ['GOOGLE_API_KEY'] = "YOUR_KEY"
```

---

## 🔮 Future Enhancements

- [ ] GUI integration (Flet tab "Janoshik Rankings")
- [ ] Scheduler for automatic updates (daily/weekly)
- [ ] Email alerts for new top suppliers
- [ ] Trend charts (score over time)
- [ ] Comparison tool (supplier A vs B)
- [ ] ML-based anomaly detection
- [ ] Integration with suppliers table (auto-update janoshik_score)
- [ ] PDF report generation
- [ ] REST API endpoints

---

## 📄 License

Part of Peptide Management System - MIT License

---

## 👥 Contributing

1. Follow existing code style
2. Add tests for new features
3. Update documentation
4. One feature per commit

---

## 📞 Support

For issues or questions, open an issue on GitHub.

---

**Version**: 0.3.0  
**Last Updated**: December 4, 2025
