# Future Features & Improvements

## 💉 Gestione Wastage e Somministrazioni Multi-Preparazione

### Problema da Risolvere
Situazione reale comune:
- Sistema indica 0.4ml rimanenti in Prep A
- Realtà: solo 0.18ml disponibili (wastage 0.22ml)
- Necessario iniettare dose completa 0.4ml
- Soluzione: combinare 0.18ml (Prep A) + 0.22ml (Prep B)

### Implementazione

#### Database Schema
```sql
-- Nuova tabella per tracciare preparazioni multiple per somministrazione
CREATE TABLE administration_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    administration_id INTEGER NOT NULL,
    preparation_id INTEGER NOT NULL,
    volume_ml REAL NOT NULL,
    is_depleting BOOLEAN DEFAULT 0, -- True se questa prep viene esaurita
    FOREIGN KEY (administration_id) REFERENCES administrations(id),
    FOREIGN KEY (preparation_id) REFERENCES preparations(id)
);

-- Indici per performance
CREATE INDEX idx_admin_sources_admin ON administration_sources(administration_id);
CREATE INDEX idx_admin_sources_prep ON administration_sources(preparation_id);
```

#### Workflow GUI (Opzione 2 - Guidato)
1. **Step 1**: Utente clicca "Somministra" su Preparazione A
2. **Step 2**: Sistema rileva volume insufficiente
   ```
   ⚠️ Volume Insufficiente
   
   Dose richiesta: 0.40 ml
   Disponibile in Prep #45: 0.18 ml
   Mancante: 0.22 ml
   
   Wastage stimato: 0.22 ml
   
   [Registra Wastage e Completa con Altra Prep]
   [Annulla]
   ```

3. **Step 3**: Se conferma → Dialog selezione preparazione integrativa
   ```
   Seleziona preparazione per completare dose
   
   Preparazioni compatibili (stesso peptide):
   ○ Prep #46 - 2.5ml disponibili ✓
   ○ Prep #47 - 1.8ml disponibili ✓
   
   Volume da prelevare: 0.22 ml
   ```

4. **Step 4**: Sistema registra automaticamente:
   - 1 somministrazione (0.4ml totale)
   - 2 righe in `administration_sources`:
     - Prep A: 0.18ml (is_depleting=true)
     - Prep B: 0.22ml (is_depleting=false)
   - Wastage su Prep A: 0.22ml, reason='measurement_error'
   - Status Prep A → 'depleted'
   - Volume Prep B → -0.22ml

#### GUI Components

**1. Dialog Registra Wastage**
```python
def show_wastage_dialog(prep_id, estimated_wastage_ml):
    """
    Dialog per confermare e registrare wastage.
    
    Campi:
    - Wastage ML (pre-filled con stima)
    - Reason (dropdown): measurement_error, spillage, contamination, other
    - Notes (textarea)
    - Checkbox: "Completa dose con altra preparazione"
    """
```

**2. Visualizzazione Somministrazioni Multi-Prep**
Nel dettaglio somministrazione mostrare:
```
Somministrazione #123
Dose: 0.4 ml
Data: 2025-11-20

Preparazioni utilizzate:
├─ Prep #45: 0.18ml (esaurita) 🔴
└─ Prep #46: 0.22ml ✓
```

**3. Report Wastage**
Aggiungere vista "Analisi Wastage":
- Wastage totale per preparazione
- Wastage per motivo (grafico)
- Trend wastage nel tempo
- Preparazioni con alto wastage (alert qualità)

### Funzioni Backend

```python
# peptide_manager/__init__.py

def record_multi_prep_administration(
    preparations: List[Dict],  # [{"prep_id": 45, "volume_ml": 0.18, "depleting": True}, ...]
    total_dose_ml: float,
    protocol_id: int = None,
    administration_datetime: datetime = None,
    injection_site: str = None,
    notes: str = None,
) -> int:
    """
    Registra somministrazione da multiple preparazioni.
    
    Returns:
        administration_id
    """
    pass

def mark_preparation_depleted(
    prep_id: int,
    wastage_ml: float,
    wastage_reason: str,
    wastage_notes: str = None,
) -> bool:
    """
    Marca preparazione come depleted con wastage tracking.
    """
    pass
```

### Migration
```sql
-- 009_add_administration_sources.sql
CREATE TABLE administration_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    administration_id INTEGER NOT NULL,
    preparation_id INTEGER NOT NULL,
    volume_ml REAL NOT NULL,
    is_depleting BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (administration_id) REFERENCES administrations(id) ON DELETE CASCADE,
    FOREIGN KEY (preparation_id) REFERENCES preparations(id) ON DELETE RESTRICT
);

CREATE INDEX idx_admin_sources_admin ON administration_sources(administration_id);
CREATE INDEX idx_admin_sources_prep ON administration_sources(preparation_id);

-- Registra migration
INSERT INTO schema_migrations (migration_name, description)
VALUES ('009_add_administration_sources', 'Add support for multi-preparation administrations');
```

### Testing Scenarios
1. Somministrazione singola prep (esistente) → continua a funzionare
2. Wastage detection su prep insufficiente
3. Completamento con seconda prep
4. Visualizzazione somministrazione multi-prep
5. Report wastage aggregato

### Priority
🔴 Alta - Migliora significativamente usabilità e accuratezza tracking

---

## 🎨 Sistema Temi Personalizzabili

### Temi Progress Bar
- Ocean Blue (implementato) ✅
- Success Green
- Warm Progress
- Purple Luxury
- Cool Clinical
- Rainbow Energy
- Monochrome Green

### Temi Colore Globale
- Dark Mode (attuale) ✅
- Light Mode
- High Contrast (accessibilità)
- Custom (utente sceglie colori primari/secondari)

### Temi Cicli Specifici
- Medical Blue (professionale)
- Wellness Green (naturale)
- Performance Orange (energia)
- Recovery Purple (riposo)

### Implementazione Tecnica
```python
# peptide_manager/settings.py
class ThemeManager:
    THEMES = {
        'ocean': {
            'primary': ft.Colors.BLUE_400,
            'progress': ['CYAN_400', 'BLUE_400', 'INDIGO_400'],
            'accent': ft.Colors.CYAN_600,
            'cards': ft.Colors.BLUE_GREY_900,
        },
        'success': {
            'primary': ft.Colors.GREEN_400,
            'progress': ['LIGHT_GREEN_400', 'GREEN_400', 'TEAL_400'],
            'accent': ft.Colors.GREEN_600,
            'cards': ft.Colors.GREEN_900,
        },
        # ... altri temi
    }
    
    @staticmethod
    def load_user_theme() -> str:
        """Load saved theme preference from settings."""
        pass
    
    @staticmethod
    def apply_theme(page: ft.Page, theme_name: str):
        """Apply theme to entire application."""
        pass
```

### Persistenza Preferenze
- File `user_settings.json` per configurazioni locali
- Tabella `user_preferences` in database per sync multi-device
- Applicazione automatica tema all'avvio

### UI per Selezione Tema
- Aggiungere sezione "Impostazioni" nel navigation rail
- Preview live dei temi
- Reset a default

---

## 📊 Grafici e Analytics

### Aderenza Protocollo
- % somministrazioni completate vs pianificate
- Calendario heatmap con giorni completati
- Streak tracking (giorni consecutivi)

### Progressi nel Tempo
- Grafico trend dosaggi (line chart)
- Confronto cicli multipli
- Efficacia per peptide

### Timeline Visuale
- Gantt chart cicli sovrapposti
- Timeline somministrazioni
- Indicatori eventi (pause, side effects)

### Statistiche Aggregate
- Report per peptide (dosi totali, costo medio)
- Analisi fornitori (affidabilità, prezzi)
- Previsioni scorte

---

## 📄 Reportistica Avanzata

### Export Formati
- CSV con filtri avanzati
- PDF report formattato
- Excel con grafici integrati

### Report Cicli
- Riepilogo completo ciclo
- Date chiave e milestone
- Dosi totali e costi
- Aderenza percentuale
- Side effects tracking

### Report Comparativi
- Ciclo A vs Ciclo B
- Efficacia per protocollo
- Costo/beneficio analysis

---

## ⚠️ Validazioni e Warning System

### Alert Scorte
- Warning scorte insufficienti per ciclo pianificato
- Notifica quando batch sotto soglia minima
- Previsione esaurimento basata su consumi

### Cicli Monitoring
- Warning cicli inattivi da X giorni
- Alert somministrazioni saltate
- Promemoria programmati

### Scadenze
- Notifica preparazioni in scadenza durante ciclo attivo
- Alert batch prossimi a scadenza
- Reminder certificati mancanti

### Validazioni Intelligenti
- Controllo sovrapposizione cicli (stesso peptide)
- Warning dosi fuori range consigliato
- Alert interazioni peptidi (se configurate)

---

## 🔧 Altre Idee

### Backup Automatico
- Backup schedulato giornaliero
- Retention policy configurabile
- Export cloud (Google Drive, Dropbox)

### Multi-User Support
- Login utenti multipli
- Permessi (admin, user, read-only)
- Activity log per audit

### Mobile App
- Companion app per tracking veloce
- Notifiche push per promemoria
- Sync con desktop app

### Integrazioni
- Import dati da Excel/CSV batch
- Export calendario (iCal) per somministrazioni
- API REST per integrazioni custom

### AI/ML Features
- Suggerimenti dosaggi basati su storico
- Predizione side effects
- Ottimizzazione protocolli

---

**Note**: Features ordinate per priorità e fattibilità. Implementare in modo incrementale basandosi su feedback utilizzo quotidiano.
