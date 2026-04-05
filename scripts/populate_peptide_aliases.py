"""
Applica la migration 019 e popola la tabella peptide_aliases
con tutti i sinonimi/nomi alternativi per ogni peptide.

Uso:
    python scripts/populate_peptide_aliases.py [--env development|production]
    python scripts/populate_peptide_aliases.py --dry-run
"""

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

# ---------------------------------------------------------------------------
# Alias per ogni peptide (nome canonico nel DB → lista di alias/sinonimi)
# ---------------------------------------------------------------------------
ALIASES: dict[str, list[str]] = {
    "BPC-157": [
        "BPC157", "BPC 157", "Pentadecapeptide BPC 157", "PL 14736",
        "Body Protection Compound 157",
    ],
    "TB-500": [
        "TB500", "TB 500", "Thymosin Beta-4", "Thymosin Beta4",
        "Thymosin B4", "Tβ4", "TB4", "Thymosin-Beta-4",
    ],
    "GHK-Cu": [
        "GHK", "GHK Cu", "Copper Peptide", "Iamin",
        "Glycyl-L-Histidyl-L-Lysine Copper", "GHK-Copper",
    ],
    "Ipamorelin": [
        "NNC 26-0161", "NNC26-0161",
    ],
    "CJC-1295": [
        "CJC1295", "CJC-1295 no DAC", "Modified GRF 1-29", "Mod GRF 1-29",
        "ModGRF", "CJC 1295",
    ],
    "CJC-1295 DAC": [
        "CJC1295 DAC", "CJC-1295DAC", "CJC 1295 DAC",
    ],
    "Sermorelin": [
        "GHRH 1-29", "GRF 1-29", "Geref", "Sermorelin acetate",
    ],
    "Tesamorelin": [
        "Egrifta", "TH9507", "GHRH 1-44",
    ],
    "IGF-1": [
        "IGF-1 LR3", "IGF1", "IGF 1", "Insulin-like Growth Factor 1",
        "Insulin-like Growth Factor-1", "LR3-IGF-1",
    ],
    "PEG-MGF": [
        "Pegylated MGF", "PEG MGF", "Mechano Growth Factor",
        "MGF", "IGF-1Ec",
    ],
    "Follistatin": [
        "Follistatin-344", "Follistatin 344", "FST-344",
        "Follistatin-315", "FST",
    ],
    "AOD-9604": [
        "AOD9604", "AOD 9604", "hGH Fragment 177-191",
        "Growth Hormone Fragment 176-191",
    ],
    "Melanotan-II": [
        "Melanotan 2", "Melanotan II", "MT-2", "MT-II", "MT2",
    ],
    "PT-141": [
        "Bremelanotide", "Vyleesi", "PT141", "PT 141",
    ],
    "Kisspeptin": [
        "KP-10", "KP-54", "KP-13", "Metastin",
    ],
    "Epithalon": [
        "Epitalon", "Epithalamion", "Ala-Glu-Asp-Gly",
        "Epithalamin",
    ],
    "DSIP": [
        "Delta Sleep-Inducing Peptide", "Delta Sleep Inducing Peptide",
    ],
    "MOTS-C": [
        "MOTS C", "Mitochondrial ORF of the 12S rRNA type-c",
    ],
    "Semax": [
        "ACTH 4-7 PGP", "ACTH(4-7)PGP",
    ],
    "Selank": [
        "TP-7", "Tuftsin analog",
    ],
    "Pe 22-28": [
        "PE 22-28", "PE22-28", "SPEF1 fragment 22-28",
    ],
    "Ara-290": [
        "Cibinetide", "ARA290", "ARA 290",
    ],
    "SS-31": [
        "Elamipretide", "MTP-131", "Bendavia", "SS31",
    ],
    "SNAP-8": [
        "SNAP8", "Argireline analog", "Leuphasyl",
    ],
    "PNC-27": [
        "PNC27",
    ],
    "SLU-PP-332": [
        "SLP-PP", "SLU PP 332", "ERR agonist SLU-PP-332",
    ],
    "NAD+": [
        "NAD", "Nicotinamide Adenine Dinucleotide",
        "β-NAD", "beta-NAD",
    ],
    "NMN": [
        "Nicotinamide Mononucleotide", "Beta-NMN", "β-NMN",
    ],
    "Glutathione": [
        "GSH", "L-Glutathione", "Glutatione", "γ-Glu-Cys-Gly",
    ],
    "5-Amino-1MQ": [
        "5-Amino-1-methylquinolinium", "5A1MQ", "NNMT inhibitor",
    ],
    "Tesofensine": [
        "NS2330", "Tesomet",
    ],
    "Semaglutide": [
        "Ozempic", "Wegovy", "Rybelsus",
    ],
    "Tirzepatide": [
        "Mounjaro", "Zepbound", "LY3298176",
    ],
    "Retatrutide": [
        "LY3437943",
    ],
    "Cagrilintide": [
        "AM833", "CagriSema",
    ],
    "Mazdutide": [
        "IBI362",
    ],
    "Survodutide": [
        "BI 456906",
    ],
    "Thymosin Alpha-1": [
        "Thymosin α1", "Thymosin alpha1", "Zadaxin", "Ta1", "Tα1",
        "Thymosin-Alpha-1",
    ],
    "Thymosin-Alpha-1": [
        "Zadaxin", "Thymosin alpha 1", "Ta1",
    ],
    "Thymulin": [
        "FTS", "Facteur Thymique Serique", "Thymic Factor",
    ],
    "HCG": [
        "Human Chorionic Gonadotropin", "hCG",
        "Pregnyl", "Profasi", "Ovidrel",
    ],
    "HGH": [
        "Human Growth Hormone", "Somatropin", "Somatropina",
        "Growth Hormone", "GH",
    ],
    "VIP": [
        "Vasoactive Intestinal Peptide", "VIP peptide",
    ],
    "KPV": [
        "Lys-Pro-Val", "Alpha-MSH fragment",
    ],
    "Testosterone": [
        "T", "Test", "Testosterone base", "Testosterone enanthate",
        "Testosterone cypionate", "Testosterone propionate",
        "Testosterone undecanoate", "Sustanon",
    ],
    "Nandrolone": [
        "Deca-Durabolin", "Deca", "Nandrolone Decanoate",
        "19-nortestosterone",
    ],
    "NPP": [
        "Nandrolone Phenylpropionate", "Nandrolone PP",
        "Durabolin",
    ],
    "Anavar": [
        "Oxandrolone", "Oxandrin",
    ],
    "Masteron": [
        "Drostanolone", "Drostanolone Propionate", "Masteron Propionate",
    ],
    "Masteron Enanthate": [
        "Drostanolone Enanthate",
    ],
    "Methenolone": [
        "Primobolan Acetate", "Primobolan oral",
    ],
    "Primobolan": [
        "Methenolone Enanthate", "Primobolan Depot",
    ],
    "Trenbolone": [
        "Tren", "Trenbolone Acetate", "Trenbolone Enanthate",
        "Finaplix",
    ],
    "Parabolan": [
        "Trenbolone Hexahydrobenzylcarbonate", "Trenbolone Hex",
        "Tren Hex",
    ],
    "Enclomiphene": [
        "trans-Clomiphene", "Androxal", "Enclomifene",
    ],
    "Exemestane": [
        "Aromasin",
    ],
    "Tramadol": [
        "Ultram", "Tramal",
    ],
    "GHK-Cu": [
        "GHK", "GHK Cu", "Copper Peptide", "Iamin",
        "Glycyl-L-Histidyl-L-Lysine Copper",
    ],
    "Cardiogen": [
        "Ala-Glu-Asp-Arg",
    ],
    "Cartalax": [
        "Ala-Glu-Asp-Gly cartilage",
    ],
    "Testagen": [
        "Lys-Glu-Asp-Gly",
    ],
    "Thymagen": [
        "Glu-Trp", "EW dipeptide",
    ],
    "PNC-27": [
        "PNC27",
    ],
    "Epithalon": [
        "Epitalon", "Ala-Glu-Asp-Gly pineal",
    ],
}


def apply_migration(conn: sqlite3.Connection):
    """Applies migration 019 SQL if peptide_aliases table doesn't exist yet."""
    exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='peptide_aliases'"
    ).fetchone()
    if exists:
        return

    migration_path = ROOT / "migrations" / "019_add_peptide_aliases.sql"
    sql = migration_path.read_text(encoding="utf-8")
    conn.executescript(sql)
    print("Migration 019 applicata.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", choices=["development", "production"],
                        default="development")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    db_path = ROOT / "data" / args.env / "peptide_management.db"
    if not db_path.exists():
        print(f"DB non trovato: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    # Apply migration (creates table, renames TB500, splits Semax/Selank, adds CJC DAC)
    if not args.dry_run:
        apply_migration(conn)

    # Build name → id mapping (include all peptides)
    peptides = conn.execute(
        "SELECT id, name FROM peptides WHERE deleted_at IS NULL"
    ).fetchall()
    name_to_id = {row["name"].strip(): row["id"] for row in peptides}

    inserted = 0
    skipped_no_peptide = []
    skipped_conflict = []

    for canonical_name, aliases in ALIASES.items():
        peptide_id = name_to_id.get(canonical_name)
        if peptide_id is None:
            skipped_no_peptide.append(canonical_name)
            continue

        for alias in aliases:
            alias = alias.strip()
            if args.dry_run:
                print(f"  [{canonical_name}] alias: {alias}")
                inserted += 1
                continue

            # Check if alias already registered for a DIFFERENT peptide
            existing = conn.execute(
                "SELECT peptide_id FROM peptide_aliases WHERE alias = ? COLLATE NOCASE",
                (alias,)
            ).fetchone()
            if existing:
                if existing["peptide_id"] != peptide_id:
                    skipped_conflict.append(
                        f"'{alias}' già assegnato a peptide_id={existing['peptide_id']}"
                    )
                continue  # Already correct → skip

            # Also skip if alias == canonical name of any peptide
            if alias.lower() in {n.lower() for n in name_to_id}:
                continue

            conn.execute(
                "INSERT OR IGNORE INTO peptide_aliases (peptide_id, alias) VALUES (?, ?)",
                (peptide_id, alias)
            )
            inserted += 1

    if not args.dry_run:
        conn.commit()

    conn.close()

    verb = "Da inserire" if args.dry_run else "Inseriti"
    print(f"\n{verb}: {inserted} alias")

    if skipped_no_peptide:
        print(f"\nPeptidi non trovati nel DB ({len(skipped_no_peptide)}):")
        for n in skipped_no_peptide:
            print(f"  - {n}")

    if skipped_conflict:
        print(f"\nConflitti alias ({len(skipped_conflict)}):")
        for c in skipped_conflict:
            print(f"  - {c}")


if __name__ == "__main__":
    main()
