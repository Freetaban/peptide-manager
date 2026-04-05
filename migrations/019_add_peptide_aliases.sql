-- Migration 019: tabella alias peptidi + split Semax/Selank + fix naming
-- Aggiunge supporto per sinonimi/nomi alternativi per ogni peptide.

-- 1. Tabella alias
CREATE TABLE IF NOT EXISTS peptide_aliases (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    peptide_id INTEGER NOT NULL REFERENCES peptides(id) ON DELETE CASCADE,
    alias      TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(alias COLLATE NOCASE)
);

CREATE INDEX IF NOT EXISTS idx_peptide_aliases_alias
    ON peptide_aliases(alias COLLATE NOCASE);

-- 2. Rinomina TB500 → TB-500
UPDATE peptides SET name = 'TB-500' WHERE name = 'TB500' AND deleted_at IS NULL;

-- 3. Split "Semax, Selank" → "Semax" (esistente) + "Selank" (nuovo)
UPDATE peptides
SET name = 'Semax',
    description = 'Analogo sintetico dell''ACTH(4-7) (Met-Glu-His-Phe-Pro-Gly-Pro). Aumenta la sintesi di BDNF e NGF; modula i recettori dopaminergici e serotoninergici. Approvato in Russia.',
    common_uses = 'Potenziamento cognitivo e mnemonico; neuroprotezione post-ictus; riduzione ansia e depressione; aumento BDNF/NGF; supporto in TBI e neurodegenerazione.'
WHERE name = 'Semax, Selank' AND deleted_at IS NULL;

INSERT INTO peptides (name, description, common_uses, notes)
SELECT
    'Selank',
    'Esapeptide nootropico e anxiolitico (Thr-Lys-Pro-Arg-Pro-Gly-Pro) derivato dalla tuftina. Aumenta BDNF, modula serotonina e dopamina. Approvato in Russia come nootropico.',
    'Riduzione dell''ansia senza sedazione; miglioramento della memoria e concentrazione; neuroprotezione; supporto in stati di stress; stabilizzazione dell''umore.',
    NULL
WHERE NOT EXISTS (SELECT 1 FROM peptides WHERE name = 'Selank' AND deleted_at IS NULL);

-- 4. Aggiunge CJC-1295 DAC come peptide separato (composto distinto da CJC-1295 no DAC)
INSERT INTO peptides (name, description, common_uses, notes)
SELECT
    'CJC-1295 DAC',
    'Analogo GHRH (1-29) coniugato con Drug Affinity Complex (DAC) che lo lega all''albumina plasmatica prolungando la t½ a ~8 giorni. Stimola la secrezione prolungata e pulsatile di GH.',
    'Aumento sostenuto di GH e IGF-1; crescita massa muscolare magra; riduzione grasso corporeo; recupero; cicli settimanali (1-2 iniezioni/settimana).',
    NULL
WHERE NOT EXISTS (SELECT 1 FROM peptides WHERE name = 'CJC-1295 DAC' AND deleted_at IS NULL);
