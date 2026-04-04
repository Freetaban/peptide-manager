"""
Popola i campi 'description' e 'common_uses' per tutti i peptidi nel DB,
basandosi sui documenti COMPENDIO_PEPTIDI.md e COMPENDIO_AAS_FARMACI.md.

Uso:
    python scripts/populate_peptide_descriptions.py [--env development|production]
    python scripts/populate_peptide_descriptions.py --dry-run
"""

import argparse
import sqlite3
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Dati di riferimento — estratti e sintetizzati dai compendi
# Chiavi: nome normalizzato (minuscolo, strip spazi)
# Valori: (description, common_uses)
# ---------------------------------------------------------------------------
PEPTIDE_DATA: dict[str, tuple[str, str]] = {

    # ── Peptidi riparativi ──────────────────────────────────────────────
    "bpc-157": (
        "Pentadecapeptide citoprotettivo derivato dalla proteina di protezione gastrica "
        "umana (BPC). Attiva le vie di segnalazione NO, VEGFR2, EGF-R e FAK-paxillin; "
        "promuove migrazione fibroblastica e neovascolarizzazione.",
        "Riparazione di muscoli, tendini, legamenti e tessuto osseo; "
        "guarigione della mucosa gastrointestinale (ulcere, IBD); "
        "riduzione dell'infiammazione sistemica; "
        "neuroprotezione e recupero da lesioni al SNC; "
        "supporto post-chirurgico e cicatrizzazione."
    ),
    "tb-500": (
        "Frammento sintetico attivo della Thymosin Beta-4 (43 aa). Sequestra l'actina G "
        "limitando la polimerizzazione incontrollata; attiva vie anti-apoptotiche (Akt) "
        "e proangiogeniche (VEGF, HIF-1α).",
        "Guarigione e riparazione di muscoli, tendini, legamenti e articolazioni; "
        "potente azione antinfiammatoria; "
        "stimolazione dell'angiogenesi; "
        "cardioprotection e neuroprotezione; "
        "spesso combinato con BPC-157 in blend."
    ),
    "tb500": (
        "Frammento sintetico attivo della Thymosin Beta-4. Sequestra l'actina G, "
        "attiva vie anti-apoptotiche (Akt) e promuove angiogenesi (VEGF, HIF-1α). "
        "Identico a TB-500.",
        "Guarigione muscoli/tendini/legamenti; azione antinfiammatoria; "
        "angiogenesi; cardioprotection; neuroprotezione."
    ),
    "ghk-cu": (
        "Tripeptide rame (Gly-His-Lys + Cu²⁺) presente nel plasma umano. Attiva geni "
        "di riparazione tissutale, stimola la produzione di collagene ed elastina, "
        "modula più di 4000 geni umani.",
        "Guarigione ferite e ulcere cutanee; "
        "stimolazione produzione collagene ed elastina; "
        "azione anti-aging cutanea; "
        "riduzione dell'infiammazione; "
        "uso cosmetico topico (creme anti-rughe)."
    ),
    "kvp": (
        "Tripeptide (Lys-Pro-Val) frammento C-terminale di alpha-MSH con azione "
        "anti-infiammatoria selettiva sul tratto gastrointestinale.",
        "Riduzione infiammazione intestinale; malattia di Crohn e colite ulcerosa; "
        "guarigione della mucosa GI; uso topico antiinfiammatorio."
    ),
    "kpv": (
        "Tripeptide (Lys-Pro-Val) frammento C-terminale di alpha-MSH con azione "
        "anti-infiammatoria selettiva sul tratto gastrointestinale.",
        "Riduzione infiammazione intestinale; malattia di Crohn e colite ulcerosa; "
        "guarigione della mucosa GI; uso topico antiinfiammatorio."
    ),

    # ── Secretagoghi GH ────────────────────────────────────────────────
    "ipamorelin": (
        "Pentapeptide (Aib-His-D-2Nal-D-Phe-Lys-NH₂) secretagogo GH altamente "
        "selettivo, agonista GHSR. Non stimola cortisolo, prolattina o ACTH "
        "a dosi terapeutiche.",
        "Stimolazione fisiologica del GH; "
        "aumento della massa muscolare magra; "
        "riduzione del grasso corporeo; "
        "miglioramento della qualità del sonno; "
        "anti-aging; spesso combinato con CJC-1295."
    ),
    "cjc-1295": (
        "Analogo sintetico del GHRH (1-29) con emivita prolungata, disponibile "
        "con DAC (Drug Affinity Complex, t½ ~8 giorni) o senza DAC (t½ ~30 min). "
        "Stimola la secrezione pulsatile di GH dall'ipofisi.",
        "Aumento pulsatile di GH e IGF-1; "
        "crescita della massa muscolare magra; "
        "riduzione del grasso corporeo; "
        "recupero e rigenerazione; "
        "solitamente combinato con Ipamorelin."
    ),
    "sermorelin": (
        "Analogo sintetico del GHRH (frammento 1-29) approvato per uso clinico. "
        "Stimola la secrezione fisiologica di GH dall'ipofisi anteriore con "
        "meccanismo di feedback conservato.",
        "Deficit di GH in adulti e bambini (uso approvato pediatrico); "
        "anti-aging; miglioramento composizione corporea; "
        "qualità del sonno; recupero."
    ),
    "tesamorelin": (
        "Analogo del GHRH (1-44) approvato FDA (Egrifta) per la lipodistrofia nei "
        "pazienti HIV in terapia antiretrovirale. Stimola la produzione fisiologica "
        "di GH con t½ ~38 min.",
        "Riduzione del grasso viscerale in pazienti HIV (uso approvato); "
        "stimolazione GH; sindrome metabolica; "
        "composizione corporea."
    ),
    "igf-1": (
        "Insulin-like Growth Factor 1; mediatore principale degli effetti anabolici "
        "del GH. Attiva le vie PI3K/Akt e MAPK/ERK per la sintesi proteica e la "
        "proliferazione cellulare. IGF-1 LR3 è la variante a emivita prolungata.",
        "Crescita e ipertrofia muscolare; "
        "recupero da infortuni; "
        "sintesi proteica; "
        "rigenerazione tessutale; "
        "anti-aging; studi su longevità."
    ),
    "peg-mgf": (
        "Mechano Growth Factor (MGF) pegilato; variante del IGF-1 spliced prodotta "
        "in risposta a danno meccanico muscolare. La pegilazione prolunga l'emivita "
        "da minuti a ore.",
        "Riparazione e ipertrofia muscolare post-esercizio; "
        "recupero da infortuni muscolari; "
        "attivazione cellule satellite; "
        "uso in ricerca sportiva."
    ),
    "follistatin": (
        "Glicoproteina legante l'attivina che inibisce la miostatina e l'attivina A/B. "
        "Follistatin-344 e -315 differiscono per la sequenza di legame all'eparina. "
        "PM ~35-37 kDa.",
        "Inibizione della miostatina (aumento massa muscolare); "
        "crescita muscolare estrema in modelli animali; "
        "ricerca su distrofie muscolari; "
        "potenziale anti-aging."
    ),
    "aod-9604": (
        "Frammento sintetico del C-terminale dell'hGH (aa 177-191) con potente "
        "attività lipolitica. Non stimola IGF-1 né ha effetti mitogeni o "
        "diabetogeni del GH intero.",
        "Lipolisi e perdita di peso; "
        "riduzione del grasso corporeo senza effetti del GH intero; "
        "ricerca su osteoartrite (uso topico intra-articolare); "
        "biohacking metabolico."
    ),

    # ── Melanocortina ───────────────────────────────────────────────────
    "melanotan-ii": (
        "Analogo ciclico sintetico di alpha-MSH; agonista non selettivo di MC1R, "
        "MC3R, MC4R e MC5R. MW 1024.19 Da. Precede il Bremelanotide/PT-141 "
        "nello sviluppo farmacologico.",
        "Abbronzatura cutanea (melanogenesi via MC1R); "
        "effetti pro-sessuali (via MC4R); "
        "soppressione dell'appetito; "
        "riduzione del grasso corporeo; "
        "uso off-label e ricerca."
    ),
    "pt-141": (
        "Bremelanotide; eptapeptide ciclico sintetico (Ac-Nle-c[Asp-His-D-Phe-Arg-Trp-Lys]-OH), "
        "agonista selettivo MC3R/MC4R nel SNC. Approvato FDA 2019 (Vyleesi) per FSIAD. "
        "Non ha effetti diretti vascolari periferici.",
        "Disfunzione sessuale femminile — FSIAD (uso approvato Vyleesi); "
        "disfunzione erettile maschile psicogena; "
        "aumento della libido; "
        "uso SC o intranasale off-label."
    ),
    "kisspeptin": (
        "Neuropeptide derivato dalla proteina Kiss1 (isoforme KP-10, KP-13, KP-54). "
        "Attiva il recettore KISS1R nell'ipotalamo stimolando il rilascio pulsatile "
        "di GnRH e quindi LH/FSH.",
        "Stimolazione asse ipotalamo-ipofisi-gonadi; "
        "aumento testosterone/LH/FSH; "
        "infertilità maschile e femminile; "
        "libido; ricerca endocrinologica."
    ),

    # ── Anti-aging / epigenetica ────────────────────────────────────────
    "epithalon": (
        "Tetrapeptide pinealico sintetico (Ala-Glu-Asp-Gly) sviluppato dal Prof. "
        "Khavinson. Attiva la telomerasi (hTERT), prolunga i telomeri e regola "
        "la produzione di melatonina.",
        "Allungamento e protezione dei telomeri; "
        "anti-aging sistemico; "
        "miglioramento della qualità del sonno e della melatonina; "
        "immunomodulazione; "
        "approvato in Russia per uso clinico."
    ),
    "dsip": (
        "Delta Sleep-Inducing Peptide; nonapeptide (Trp-Ala-Gly-Gly-Asp-Ala-Ser-Gly-Glu) "
        "che induce il sonno delta (SWS). Modula il cortisolo, la melatonina e il "
        "sistema opioide.",
        "Miglioramento qualità e profondità del sonno; "
        "riduzione del cortisolo; "
        "azione ansiolitica; "
        "modulazione del sistema circadiano; "
        "ricerca su stress e ritmo sonno-veglia."
    ),
    "mots-c": (
        "Micropeptide di 16 aa codificato dal genoma mitocondriale (ORF nell'rRNA 12S). "
        "Attiva AMPK, aumenta l'uptake di glucosio e la biogenesi mitocondriale. "
        "PM 2174.6 Da.",
        "Sensibilità insulinica e metabolismo del glucosio; "
        "biogenesi mitocondriale; "
        "anti-aging metabolico; "
        "aumento della tolleranza allo sforzo; "
        "longevità (studi su C. elegans e topi)."
    ),
    "cartalax": (
        "Tetrapeptide bioregolatore sintetico di origine cartilaginea (Ala-Glu-Asp-Gly). "
        "Appartiene alla classe dei peptidi biostimolatori sviluppati dall'Istituto "
        "di Gerontologia di San Pietroburgo.",
        "Supporto alla rigenerazione cartilaginea; "
        "salute articolare; "
        "biohacking anti-aging; "
        "uso in combinazione con altri peptidi bioregolatori."
    ),
    "cardiogen": (
        "Tetrapeptide bioregolatore cardiaco (Ala-Glu-Asp-Arg). Sviluppato da "
        "Khavinson et al. come peptide cardioprotettivo per la regolazione "
        "delle funzioni del miocardio.",
        "Cardioprotection; supporto funzione cardiaca; "
        "regolazione metabolismo miocardico; "
        "anti-aging cardiovascolare; "
        "biohacking."
    ),
    "testagen": (
        "Tetrapeptide bioregolatore testicolare (Lys-Glu-Asp-Gly). Sviluppato "
        "dal gruppo di Khavinson per il supporto della funzione gonadica maschile. "
        "CAS 1026993-38-3.",
        "Supporto funzione testicolare e produzione di testosterone; "
        "anti-aging gonadico; "
        "ipogonadismo funzionale lieve; "
        "biohacking maschile."
    ),
    "thymagen": (
        "Dipeptide timico bioregolatore (Glu-Trp). Estratto e sintetizzato dal timo; "
        "appartiene alla classe dei peptidi timici di Khavinson. "
        "Induce differenziazione linfociti T.",
        "Immunomodulazione e supporto immunitario; "
        "anti-aging timico; "
        "stimolazione linfociti T; "
        "supporto in immunodeficienze lievi."
    ),
    "prostamax": (
        "Peptide bioregolatore di origine prostatica sviluppato da Khavinson. "
        "Azione organo-specifica sulla prostata con proprietà trofico-regolatorie. "
        "Composizione non universalmente pubblicata.",
        "Supporto funzionale della prostata; "
        "salute urinaria maschile; "
        "anti-aging prostatico; "
        "biohacking."
    ),

    # ── Metabolici / GLP-1 ─────────────────────────────────────────────
    "semaglutide": (
        "Agonista GLP-1 con omologia 94% con GLP-1 umano; t½ ~7 giorni. "
        "Approvato FDA per diabete T2 (Ozempic) e obesità (Wegovy). "
        "Riduce l'appetito e rallenta lo svuotamento gastrico.",
        "Perdita di peso (clinicamente significativa, 10-15%); "
        "controllo glicemico nel diabete T2; "
        "protezione cardiovascolare (riduzione eventi CV); "
        "riduzione della sazietà e dell'appetito."
    ),
    "tirzepatide": (
        "Agonista duale GLP-1/GIP (twincretin); approvato FDA come Mounjaro (diabete T2) "
        "e Zepbound (obesità). Emivita ~5 giorni. Superiore al semaglutide per "
        "perdita di peso (-15-21%).",
        "Perdita di peso marcata (superiore a semaglutide); "
        "controllo glicemico nel diabete T2; "
        "riduzione rischio cardiovascolare; "
        "sindrome metabolica."
    ),
    "retatrutide": (
        "Agonista triplo GLP-1/GIP/GCGR (recettore glucagone); in fase III per "
        "obesità grave. Perdita di peso fino al 24% in 48 settimane negli studi "
        "di fase II.",
        "Perdita di peso estrema (obesità grave); "
        "controllo glicemico; "
        "sindrome metabolica avanzata; "
        "studi su NASH e dislipidemia."
    ),
    "cagrilintide": (
        "Agonista del recettore dell'amilina a lunga durata d'azione (t½ ~7 giorni); "
        "in sviluppo in combinazione con semaglutide (CagriSema). "
        "Riduce l'appetito con meccanismo complementare al GLP-1.",
        "Perdita di peso (in combinazione con semaglutide); "
        "sazietà e controllo dell'appetito; "
        "controllo glicemico; "
        "obesità e sindrome metabolica."
    ),
    "mazdutide": (
        "Agonista duale GLP-1/GCGR (recettore glucagone); sviluppato da Innovent "
        "Biologics in Cina. In fase III per diabete T2 e obesità. "
        "CAS 2259884-03-0.",
        "Perdita di peso; controllo glicemico nel diabete T2; "
        "dislipidemia; sindrome metabolica."
    ),
    "survodutide": (
        "Agonista duale GLP-1/GCGR sviluppato da Boehringer Ingelheim. "
        "In fase II/III per NASH (steatoepatite non alcolica) e obesità. "
        "Mostra effetti anti-fibrotici epatici.",
        "Steatoepatite non alcolica (NASH/MASH); "
        "perdita di peso; "
        "fibrosi epatica; "
        "sindrome metabolica."
    ),
    "5-amino-1mq": (
        "Piccola molecola (non peptide) inibitrice di NNMT (nicotinamide "
        "N-metiltransferasi); aumenta SAM e NAD+ nelle cellule adipose, "
        "favorendo la lipolisi e la biogenesi mitocondriale.",
        "Perdita di peso e riduzione tessuto adiposo; "
        "incremento del metabolismo basale; "
        "sensibilità insulinica; "
        "anti-aging metabolico; "
        "ricerca su obesità e sindrome metabolica."
    ),
    "tesofensine": (
        "Piccola molecola inibitrice triplice della ricaptazione di serotonina, "
        "norepinefrina e dopamina (SNDRI). t½ ~220 ore. Sviluppato inizialmente "
        "per Alzheimer, riorientato su obesità (Tesomet con metoprololo).",
        "Soppressione dell'appetito e perdita di peso; "
        "aumento del dispendio energetico; "
        "uso off-label per dimagrimento; "
        "in sperimentazione come Tesomet (obesità)."
    ),

    # ── Immunomodulatori / timici ───────────────────────────────────────
    "thymosin alpha-1": (
        "Peptide timico di 28 aa (N-acetilato); approvato in oltre 35 paesi "
        "(Zadaxin). Attiva cellule dendritiche, NK e T-helper; "
        "potenzia la risposta immunitaria adattativa.",
        "Immunostimolazione in infezioni virali croniche (HBV, HCV, HIV); "
        "supporto oncologico (riduzione immunosoppressione da chemioterapia); "
        "COVID-19 (uso sperimentale); "
        "deficit immunitari; "
        "potenziamento risposta vaccinale."
    ),
    "thymosin-alpha-1": (
        "Peptide timico di 28 aa (N-acetilato); approvato in oltre 35 paesi "
        "(Zadaxin). Attiva cellule dendritiche, NK e T-helper; "
        "potenzia la risposta immunitaria adattativa.",
        "Immunostimolazione in infezioni virali croniche (HBV, HCV, HIV); "
        "supporto oncologico; COVID-19; deficit immunitari; "
        "potenziamento risposta vaccinale."
    ),
    "thymulin": (
        "Nonapeptide timico (FTS, fattore timico sierico) che richiede zinco "
        "per l'attività biologica. Induce la differenziazione e la maturazione "
        "dei linfociti T.",
        "Immunomodulazione e supporto timico; "
        "differenziazione linfociti T; "
        "anti-aging immunitario; "
        "deficit da involuzione timica."
    ),
    "hcg": (
        "Gonadotropina corionica umana; glicoproteina ~36.7 kDa composta da "
        "subunità α (comune con LH/FSH/TSH) e β specifica. Mima LH stimolando "
        "le cellule di Leydig alla produzione di testosterone.",
        "Stimolazione produzione endogena di testosterone; "
        "prevenzione atrofia testicolare durante cicli AAS; "
        "PCT (post-cycle therapy); "
        "ipogonadismo ipogonadotropo maschile; "
        "induzione ovulazione (uso approvato femminile)."
    ),

    # ── Neuroprotettivi / cognitivi ─────────────────────────────────────
    "selank": (
        "Esapeptide nootropico e anxiolitico (Thr-Lys-Pro-Arg-Pro-Gly-Pro) "
        "derivato dalla tuftina. Aumenta BDNF, modula serotonina e dopamina. "
        "Approvato in Russia come nootropico.",
        "Riduzione dell'ansia senza sedazione; "
        "miglioramento della memoria e concentrazione; "
        "neuroprotezione; supporto in stati di stress; "
        "stabilizzazione dell'umore."
    ),
    "semax": (
        "Analogo sintetico dell'ACTH(4-7) (Met-Glu-His-Phe-Pro-Gly-Pro). "
        "Aumenta la sintesi di BDNF e NGF; modula i recettori dopaminergici "
        "e serotoninergici. Approvato in Russia.",
        "Potenziamento cognitivo e mnemonico; "
        "neuroprotezione post-ictus; "
        "riduzione ansia e depressione; "
        "aumento BDNF/NGF; "
        "supporto in TBI e neurodegenerazione."
    ),
    "semax, selank": (
        "Combinazione di Semax e Selank; entrambi nootropici neuroprotettivi "
        "approvati in Russia. Azione sinergica su BDNF, ansia e cognizione.",
        "Potenziamento cognitivo; neuroprotezione; riduzione ansia; "
        "supporto umore e memoria."
    ),
    "pe 22-28": (
        "Frammento sintetico (aa 22-28) della proteina SPEF1. Agonista selettivo "
        "del canale potassico TREK-1 (famiglia K2P). PM 773.89 Da. "
        "CAS 1801959-12-5.",
        "Azione antidepressiva (meccanismo unico via TREK-1); "
        "riduzione dell'ansia; "
        "neuroprotezione; "
        "ricerca su depressione resistente ai trattamenti."
    ),
    "ara-290": (
        "Cibinetide; peptide di 11 aa analogo non eritropoietico dell'EPO "
        "(mima l'elica B dell'eritropoietina). Attiva recettori citoprotettivi "
        "senza stimolare l'eritropoiesi. PM 1257.3 Da.",
        "Neuroprotezione e riduzione del dolore neuropatico; "
        "protezione tessutale non eritropoietica; "
        "ricerca su sarcoidosi con neuropatia; "
        "diabete (neuropatia periferica); "
        "citoprotezione sistemica."
    ),
    "vip": (
        "Neuropeptide intestinale vasoattivo di 28 aa; potente vasodilatatore e "
        "immunomodulatore. Prodotto da neuroni e cellule immunitarie; "
        "agisce su recettori VPAC1 e VPAC2.",
        "Ipertensione arteriosa polmonare; "
        "malattie infiammatorie (Crohn, artrite reumatoide); "
        "immunomodulazione; "
        "neuroprotezione; "
        "BPCO e asma (broncodilatazione)."
    ),

    # ── Cardiovascolari / mitocondriali ────────────────────────────────
    "ss-31": (
        "Elamipretide; tetrapeptide mitocondriale (D-Arg-2'6'-Dmt-Lys-Phe-NH₂) "
        "che si localizza nella membrana interna mitocondriale legando la "
        "cardiolipina. Ripristina la funzione della catena respiratoria.",
        "Cardioprotection e insufficienza cardiaca; "
        "protezione mitocondriale; "
        "riduzione stress ossidativo mitocondriale; "
        "anti-aging cellulare; "
        "ricerca su miopatie mitocondriali."
    ),

    # ── Dermatologici / cosmetici ────────────────────────────────────────
    "snap-8": (
        "Ottapeptide sintetico (Ac-EEMQRRAD-NH₂) analogo dell'N-terminale della "
        "proteina SNAP-25. Compete con SNAP-25 inibendo la formazione del complesso "
        "SNARE e riducendo la contrazione muscolare facciale.",
        "Riduzione rughe da espressione (fronte, occhi, bocca); "
        "effetto botox-like non iniettivo; "
        "uso cosmetico topico in creme e sieri."
    ),

    # ── Antitumorali ───────────────────────────────────────────────────
    "pnc-27": (
        "Peptide ibrido antiproliferativo contenente un dominio simile a HDM-2 "
        "e un frammento transmembrana. Induce apoptosi selettiva nelle cellule "
        "tumorali (che sovraesprimo MDM-2) tramite necrosi membranosa. "
        "PM ~4032 Da.",
        "Ricerca oncologica (apoptosi selettiva cellule tumorali); "
        "tumori con overespressione MDM-2; "
        "uso esclusivamente sperimentale in vitro/vivo."
    ),

    # ── Supplementi non-peptidici ──────────────────────────────────────
    "slu-pp-332": (
        "Piccola molecola sintetica (non peptide) agonista pan-ERR "
        "(ERRα/β/γ — Estrogen Related Receptors). EC₅₀: 98/230/430 nM. "
        "Mima parzialmente gli effetti dell'esercizio fisico a livello "
        "muscolare e metabolico. CAS 303760-60-3.",
        "Esercizio-mimetico (aumento endurance muscolare); "
        "lipolisi e riduzione massa grassa; "
        "sensibilità insulinica; "
        "biogenesi mitocondriale; "
        "ricerca su sindrome metabolica."
    ),
    "slp-pp": (
        "Voce probabilmente errata nel database; il nome corretto è SLU-PP-332. "
        "Piccola molecola sintetica agonista pan-ERR, mimetico dell'esercizio fisico.",
        "Vedi SLU-PP-332: esercizio-mimetico, lipolisi, metabolismo muscolare."
    ),
    "nad+": (
        "Nicotinamide Adenine Dinucleotide; coenzima essenziale in oltre 500 "
        "reazioni cellulari, substrato delle sirtuine (SIRT1-7) e delle PARP. "
        "I livelli declinano con l'età.",
        "Metabolismo energetico cellulare (ATP); "
        "attivazione sirtuine (longevità, SIRT1/3); "
        "riparazione del DNA (PARP); "
        "anti-aging; "
        "supporto neurologico e cardiovascolare."
    ),
    "nmn": (
        "Nicotinamide Mononucleotide; precursore diretto di NAD+ che entra "
        "nelle cellule tramite il trasportatore Slc12a8. Più biodisponibile "
        "del NAD+ somministrato direttamente.",
        "Aumento dei livelli di NAD+ cellulare; "
        "anti-aging metabolico; "
        "miglioramento sensibilità insulinica; "
        "supporto cognitivo; "
        "longevità (studi su topi e primi trial umani)."
    ),
    "glutathione": (
        "Tripeptide endogeno (γ-Glu-Cys-Gly) e principale antiossidante "
        "intracellulare. Presente in alta concentrazione nel fegato; "
        "coinvolto in detossificazione di xenobiotici e metalli pesanti.",
        "Protezione antiossidante cellulare; "
        "detossificazione epatica; "
        "supporto sistema immunitario; "
        "anti-aging; "
        "uso IV in neuropatie e per uniformare il tono della pelle."
    ),

    # ── Ormoni peptidici ───────────────────────────────────────────────
    "hgh": (
        "Somatropina (Human Growth Hormone); proteina di 191 aa (~22 kDa) "
        "prodotta dall'ipofisi anteriore. Stimola IGF-1 epatico e promuove "
        "crescita, anabolismo e lipolisi. Approvato FDA per deficit di GH.",
        "Deficit di GH in adulti e bambini (uso approvato); "
        "composizione corporea (riduzione grasso, aumento massa magra); "
        "anti-aging; recupero; "
        "uso off-label in bodybuilding."
    ),

    # ── AAS — Testosterone e derivati ──────────────────────────────────
    "testosterone": (
        "Androgeno endogeno principale (C₁₉H₂₈O₂, CAS 58-22-0). Lega il "
        "recettore degli androgeni (AR) con alta affinità; in periferia viene "
        "convertito in DHT (5α-reduttasi) o estradiolo (aromatasi).",
        "TRT (terapia sostitutiva del testosterone); "
        "ipogonadismo maschile; "
        "aumento massa muscolare e forza; "
        "libido e funzione sessuale; "
        "eritropoiesi e densità ossea; "
        "bodybuilding (uso off-label)."
    ),
    "testosteron": (
        "Forma alternativa del nome Testosterone nel database. "
        "Androgeno endogeno principale; lega AR con alta affinità.",
        "TRT, ipogonadismo maschile, massa muscolare, libido, eritropoiesi."
    ),

    # ── AAS — Nandroloni ────────────────────────────────────────────────
    "nandrolone": (
        "Steroide anabolizzante 19-nor (C₁₈H₂₆O₂); forte anabolismo e bassa "
        "androgenicità. Aromatizza poco; il principale metabolita è il "
        "nandrolone stesso (deca, NPP). Approvato per anemia e osteoporosi.",
        "Aumento massa muscolare e forza; "
        "recupero articolare (aumento produzione collagene sinoviale); "
        "trattamento anemie aplastiche (approvato); "
        "osteoporosi; "
        "cachessia (HIV/cancro)."
    ),
    "npp": (
        "Nandrolone Fenilpropionato; estere a catena corta del nandrolone con "
        "emivita ~2-3 giorni. Profilo farmacologico identico al Deca-Durabolin "
        "ma con curva di rilascio più rapida.",
        "Aumento massa muscolare; "
        "recupero articolare; "
        "cicli di massa brevi; "
        "alternativa a breve durata al Deca."
    ),

    # ── AAS — DHT e derivati ────────────────────────────────────────────
    "anavar": (
        "Oxandrolone; steroide anabolizzante orale derivato del DHT "
        "(17α-metilato). Alta anabolizzazione, bassa androgenicità, "
        "non aromatizza. Approvato per cachessia e ustioni.",
        "Aumento forza e massa magra; "
        "preservazione muscolare durante cutting; "
        "recupero da cachessia e ustioni (approvato); "
        "TRT femminile low-dose; "
        "bodybuilding (cicli cutting)."
    ),
    "masteron": (
        "Drostanolone propionato; AAS derivato del DHT con moderata affinità "
        "per AR e proprietà anti-estrogeniche (inibisce parzialmente l'aromatasi). "
        "Non aromatizza.",
        "Definizione muscolare (cicli cutting); "
        "aumento forza senza ritenzione idrica; "
        "azione anti-estrogenica leggera; "
        "miglioramento hardness muscolare."
    ),
    "masteron enanthate": (
        "Drostanolone enantato; versione a rilascio prolungato (t½ ~7 giorni) "
        "del Masteron. Profilo farmacologico identico al propionato ma con "
        "iniezioni meno frequenti.",
        "Definizione muscolare; "
        "cicli cutting prolungati; "
        "anti-estrogenico; "
        "hardness muscolare."
    ),
    "methenolone": (
        "Primobolan base (acetato orale); AAS derivato del DHT con bassa "
        "androgenicità e buona anabolizzazione. Resistente al metabolismo "
        "di primo passaggio epatico.",
        "Aumento massa muscolare magra qualitativa; "
        "cutting con preservazione muscolare; "
        "HRT a basso impatto; "
        "cicli femminili (bassa virilizzazione)."
    ),
    "primobolan": (
        "Methenolone enantato; versione iniettabile a lunga durata (t½ ~10 gg) "
        "del Methenolone. Considerato uno degli AAS più 'puliti' per "
        "il basso profilo di effetti collaterali.",
        "Massa muscolare magra qualitativa; "
        "cicli cutting e recomp; "
        "preservazione muscolare; "
        "HRT; "
        "cicli femminili."
    ),
    "trenbolone": (
        "AAS 19-nor (C₁₈H₂₂O₂); 5× più potente del testosterone sul recettore "
        "AR. Non aromatizza. Forte attività glucocorticoide-antagonista. "
        "Esteri principali: Acetato (t½ 3 gg), Enantato (t½ 7 gg), Hex.",
        "Massa muscolare magra estrema; "
        "aumento forza marcato; "
        "lipolisi (anti-glucocorticoide); "
        "cutting avanzato; "
        "uso veterinario (Finaplix)."
    ),
    "parabolan": (
        "Trenbolone Hexaidrobenzilcarbonato; unico estere del trenbolone "
        "approvato per uso umano (Francia, ritirato 1997). "
        "t½ ~14 giorni.",
        "Massa muscolare magra; "
        "forza estrema; "
        "cutting avanzato; "
        "profilo simile al trenbolone enantato."
    ),

    # ── Modulatori ormonali — SERM / AI ─────────────────────────────────
    "enclomiphene": (
        "Isomero trans del clomifene; SERM puro (Selective Estrogen Receptor "
        "Modulator) che blocca gli ER ipotalamici stimolando LH/FSH. "
        "A differenza del clomifene, non ha il componente estrogenico.",
        "Stimolazione LH e FSH endogeni; "
        "aumento testosterone endogeno; "
        "ipogonadismo funzionale maschile; "
        "infertilità maschile; "
        "PCT alternativa al clomifene classico."
    ),
    "exemestane": (
        "Inibitore dell'aromatasi steroidale irreversibile ('suicida'); "
        "Aromasin. Si lega permanentemente all'aromatasi disattivandola. "
        "Approvato per carcinoma mammario ER+.",
        "Riduzione estrogeni (prevenzione ginecomastia); "
        "PCT e controllo estrogenico durante cicli AAS; "
        "carcinoma mammario (uso approvato); "
        "ottimizzazione testosterone/estrogeni in TRT."
    ),

    # ── Altro ──────────────────────────────────────────────────────────
    "tramadol": (
        "Oppioide sintetico debole + inibitore della ricaptazione di serotonina "
        "e norepinefrina (SNRI). Azione analgesica centrale e spinale. "
        "Rischio dipendenza e interazioni serotoninergiche.",
        "Analgesia per dolore moderato-severo (uso approvato); "
        "eiaculazione precoce (uso off-label, meccanismo SNRI); "
        "dolore neuropatico."
    ),
    "glow": (
        "Tetrapeptide bioregolatore (denominazione interna). Appartiene alla "
        "famiglia dei peptidi bioregolatori di Khavinson per il supporto di "
        "tessuti epiteliali e mucose.",
        "Supporto pelle e tessuti epiteliali; biohacking anti-aging (dati limitati)."
    ),
    "klow": (
        "Tetrapeptide bioregolatore (denominazione interna). Variante del GLOW; "
        "dati di ricerca limitati pubblicati.",
        "Supporto tessutale (dati limitati)."
    ),
    "tre": (
        "Tetrapeptide bioregolatore (denominazione interna). Dati di ricerca "
        "limitati disponibili nelle fonti pubbliche.",
        "Supporto tessutale (dati limitati)."
    ),
    "te": (
        "Voce incompleta nel database; probabilmente abbreviazione di Testosterone "
        "o di un peptide bioregolatore.",
        "Da verificare — nome insufficiente per identificare il composto."
    ),
}

# Nomi che non hanno una scheda reale (dati test/garbage da NON aggiornare)
SKIP_NAMES = {"sample", "vial", "human"}


def _normalize(name: str) -> str:
    return name.strip().lower()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", choices=["development", "production"],
                        default="development")
    parser.add_argument("--dry-run", action="store_true",
                        help="Mostra le modifiche senza applicarle")
    args = parser.parse_args()

    root = Path(__file__).parent.parent
    db_path = root / "data" / args.env / "peptide_management.db"

    if not db_path.exists():
        print(f"DB non trovato: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    peptides = conn.execute(
        "SELECT id, name, description, common_uses FROM peptides WHERE deleted_at IS NULL"
    ).fetchall()

    updated = 0
    skipped_no_data = []

    for p in peptides:
        name_norm = _normalize(p["name"])

        if name_norm in SKIP_NAMES:
            continue

        data = PEPTIDE_DATA.get(name_norm)
        if data is None:
            skipped_no_data.append(p["name"])
            continue

        description, common_uses = data

        if args.dry_run:
            print(f"\n[{p['id']}] {p['name']}")
            print(f"  DESC: {description[:80]}...")
            print(f"  USES: {common_uses[:80]}...")
        else:
            conn.execute(
                "UPDATE peptides SET description=?, common_uses=? WHERE id=?",
                (description, common_uses, p["id"])
            )
        updated += 1

    if not args.dry_run:
        conn.commit()
    conn.close()

    verb = "Da aggiornare" if args.dry_run else "Aggiornati"
    print(f"\n{verb}: {updated} peptidi")

    if skipped_no_data:
        print(f"\nSenza dati ({len(skipped_no_data)}) — non modificati:")
        for n in sorted(skipped_no_data):
            print(f"  - {n}")


if __name__ == "__main__":
    main()
