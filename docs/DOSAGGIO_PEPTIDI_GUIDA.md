# Calcolo Dosaggio Peptidi - Guida Utente

## 🎯 Come Funziona il Dosaggio nei Protocolli

### Concetto Base

Nei protocolli peptidici, il dosaggio viene definito come **dosaggio giornaliero totale** in microgrammi (mcg).

Il sistema calcola automaticamente la **dose per singola somministrazione** dividendo per la frequenza giornaliera.

---

## 📋 Esempio Pratico

### Scenario: Ipamorelin per supporto GLP

**Obiettivo:**
- Somministrare 250 mcg di Ipamorelin per volta
- 2 volte al giorno (mattina e sera)

**Come inserire nel protocollo:**

```
Nome: Ipamorelin - supporto a GLP
Frequenza: 2 volte/giorno
Giorni ON: 7
Giorni OFF: 0
Durata ciclo: 24 settimane

Peptidi:
  - Ipamorelin
    Dosaggio giornaliero: 500 mcg  ← (250 + 250)
    → Per somministrazione: 250.0 mcg  ← CALCOLATO AUTOMATICAMENTE
```

### Come Viene Calcolato

```
Dose per somministrazione = Dosaggio giornaliero ÷ Frequenza
                          = 500 mcg ÷ 2
                          = 250 mcg
```

---

## 🔄 Altri Esempi

### Esempio 1: BPC-157 una volta al giorno

```
Peptide: BPC-157
Dosaggio giornaliero: 500 mcg
Frequenza: 1 volta/giorno

→ Per somministrazione: 500.0 mcg
```

### Esempio 2: TB-500 tre volte al giorno

```
Peptide: TB-500
Dosaggio giornaliero: 1500 mcg
Frequenza: 3 volte/giorno

→ Per somministrazione: 500.0 mcg
```

### Esempio 3: Protocollo GLOW (multi-peptide)

```
Frequenza: 2 volte/giorno

Peptidi:
  - BPC-157: 1000 mcg/giorno → 500.0 mcg per somministrazione
  - GHK-Cu: 5000 mcg/giorno → 2500.0 mcg per somministrazione
  - TB-500: 1000 mcg/giorno → 500.0 mcg per somministrazione
```

---

## 💉 Come Calcolare il Volume da Iniettare

Il volume **NON** è definito nel protocollo perché dipende dalla concentrazione della preparazione usata.

### Formula

```
Volume (ml) = Dose target (mcg) ÷ Concentrazione (mcg/ml)
```

### Esempio Pratico

**Protocollo:**
- Ipamorelin: 250 mcg per somministrazione

**Preparazione disponibile:**
- Ipamorelin 5 mg/ml in 10 ml
- Concentrazione: 5000 mcg/ml

**Calcolo volume:**
```
Volume = 250 mcg ÷ 5000 mcg/ml
       = 0.05 ml
       = 5 unità su siringa da insulina (100 unità = 1 ml)
```

---

## ✅ Best Practices

### 1. Pensa in Termini di Dosaggio Giornaliero

La letteratura scientifica esprime sempre i dosaggi come:
- "BPC-157: 500 mcg/die"
- "TB-500: 2-5 mg/settimana"

Usa questi valori come riferimento.

### 2. Verifica Sempre l'Hint

Quando inserisci il dosaggio giornaliero, controlla l'hint blu:
```
→ 250.0 mcg per somministrazione
```

Questo ti dice esattamente quanto iniettare ogni volta.

### 3. Considera la Frequenza

- **1x/giorno**: Tutta la dose in una volta (semplice)
- **2x/giorno**: Dividi equamente (es: mattina e sera)
- **3x/giorno**: Dividi in tre dosi (es: mattina, pomeriggio, sera)

### 4. Il Volume Dipende dalla Preparazione

Non preoccuparti del volume in ml quando crei il protocollo.

Il sistema lo calcolerà automaticamente quando registri una somministrazione, in base alla concentrazione della preparazione che usi.

---

## 🎓 Perché Questa Logica?

### Vantaggi del Dosaggio Giornaliero

✅ **Standard medico**: Coerente con letteratura scientifica
✅ **Flessibile**: Cambi frequenza senza ricalcolare
✅ **Chiaro**: Totale giornaliero sempre visibile
✅ **Sicuro**: Evita errori di calcolo

### Svantaggi della Dose Singola

❌ Devi ricalcolare se cambi frequenza
❌ Meno standard rispetto alla letteratura
❌ Non vedi immediatamente il totale giornaliero

---

## 🔧 Interfaccia Utente

### Nel Form di Creazione

```
┌─────────────────────────────────────┐
│ Ipamorelin                          │
│ Dosaggio (mcg/giorno): [500]        │
│ → 250.0 mcg per somministrazione    │ ← HINT DINAMICO
└─────────────────────────────────────┘
```

### Nei Dettagli Protocollo

```
💊 Peptidi nel Protocollo:
   • Ipamorelin: 500 mcg/giorno (250.0 mcg × 2x/die)
   • BPC-157: 1000 mcg/giorno (500.0 mcg × 2x/die)
```

---

## ❓ FAQ

### "Devo inserire 250 o 500 se inietto 250 mcg due volte?"

**Inserisci 500 mcg** (il totale giornaliero).
Il sistema calcola automaticamente: 500 ÷ 2 = 250 mcg per somministrazione.

### "E se cambio la frequenza da 2 a 3 volte al giorno?"

Nessun problema! Il dosaggio giornaliero rimane 500 mcg.
La dose per somministrazione diventa: 500 ÷ 3 = 166.7 mcg.

### "Come faccio a sapere quanto volume iniettare?"

Dipende dalla concentrazione della tua preparazione:
- Preparazione 1000 mcg/ml → 0.25 ml
- Preparazione 5000 mcg/ml → 0.05 ml

Il sistema lo calcola quando registri la somministrazione.

### "Posso creare un protocollo senza specificare la frequenza?"

Sì, default è 1 volta/giorno. Ma è meglio essere espliciti.

---

## 📞 Supporto

Per domande o dubbi sul calcolo dei dosaggi, consulta:
- La letteratura scientifica sul peptide specifico
- Il tuo medico o consulente sanitario
- Le linee guida del fornitore

---

*Ultimo aggiornamento: 17 Gennaio 2026*
