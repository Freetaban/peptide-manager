# Future Features & Improvements

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
