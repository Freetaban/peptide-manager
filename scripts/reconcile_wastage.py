"""
Script per riconciliare somministrazioni fittizie VOLUME MANCANTE con nuovo sistema wastage.

Converte le somministrazioni create come workaround per azzerare il volume residuo
in proper wastage tracking nelle preparazioni.

Steps:
1. Trova tutte le administrations con note contenenti "VOLUME MANCANTE" o varianti
2. Per ogni administration fittizia:
   - Elimina (soft delete) l'administration fittizia
   - Registra la sua dose come evento di spreco (migrazione 024)
   - Ricalcola il volume della preparazione dagli eventi
3. Report di conversione

Nota sull'ordine: la somministrazione fittizia va rimossa PRIMA di registrare
lo spreco. La sua dose_ml e' gia' scalata dal volume rimanente: registrarla
anche come spreco senza rimuovere la somministrazione conterebbe lo stesso
volume due volte.
"""

import sqlite3
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import List, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from peptide_manager import PeptideManager
from peptide_manager.models.preparation import PreparationRepository
from peptide_manager.models.preparation_event import PreparationEvent


def find_fake_administrations(conn: sqlite3.Connection) -> List[Tuple]:
    """
    Trova somministrazioni fittizie con VOLUME MANCANTE.
    
    Returns:
        Lista di tuple (id, preparation_id, dose_ml, notes, date)
    """
    cursor = conn.cursor()
    
    # Pattern comuni per identificare somministrazioni fittizie
    patterns = [
        "%VOLUME MANCANTE%",
        "%volume mancante%",
        "%Volume Mancante%",
        "%vol mancante%",
        "%residuo%",
        "%spreco%"
    ]
    
    query = f"""
        SELECT id, preparation_id, dose_ml, notes, administration_datetime
        FROM administrations 
        WHERE deleted_at IS NULL
        AND ({" OR ".join([f"notes LIKE ?" for _ in patterns])})
        ORDER BY administration_datetime ASC
    """
    
    cursor.execute(query, patterns)
    return cursor.fetchall()


def reconcile_administration(
    admin_id: int,
    prep_id: int,
    wastage_ml: float,
    notes: str,
    admin_date: str,
    prep_repo: PreparationRepository,
    conn: sqlite3.Connection,
    dry_run: bool = True
) -> Tuple[bool, str]:
    """
    Converti una somministrazione fittizia in wastage tracking.
    
    Args:
        admin_id: ID somministrazione fittizia
        prep_id: ID preparazione
        wastage_ml: Volume spreco (da dose_ml)
        notes: Note originali
        admin_date: Data somministrazione fittizia
        prep_repo: Repository preparazioni
        conn: Connessione database
        dry_run: Se True, simula senza modificare
    
    Returns:
        Tuple (successo, messaggio)
    """
    # Verifica preparazione esiste
    prep = prep_repo.get_by_id(prep_id)
    if not prep:
        return False, f"❌ Prep #{prep_id} non trovata"

    # 'expired' e 'discarded' sono decisioni esplicite: non le riscriviamo
    if prep.status not in ('active', 'depleted'):
        return False, f"⚠️ Prep #{prep_id} status={prep.status}, skip admin #{admin_id}"

    # Già convertita: esiste già un evento di spreco per questa preparazione
    if prep_repo.events.total_wastage(prep_id) > 0:
        if dry_run:
            return True, (
                f"⚠️ Prep #{prep_id} già convertita "
                f"(spreco={prep_repo.events.total_wastage(prep_id)}ml) "
                f"→ elimina solo admin #{admin_id}"
            )

        _soft_delete_administration(conn, admin_id)
        prep_repo._apply_event_delta(prep_id, Decimal('0'))
        return True, f"✅ Prep #{prep_id} già ok, admin #{admin_id} eliminata"

    if dry_run:
        return True, (
            f"📋 DRY RUN: Prep #{prep_id} (status={prep.status}) → "
            f"spreco {wastage_ml}ml, delete admin #{admin_id}"
        )

    # Ordine obbligatorio: prima si rimuove la somministrazione fittizia, poi
    # si registra lo spreco. La dose fittizia E' lo spreco, quindi tenerle
    # entrambe conterebbe lo stesso volume due volte.
    _soft_delete_administration(conn, admin_id)

    prep_repo.events.create(PreparationEvent(
        preparation_id=prep_id,
        event_type='wastage',
        volume_ml=wastage_ml,
        event_date=(admin_date or '')[:10] or None,
        reason='measurement_error',
        notes=(
            f"Convertito da somministrazione fittizia #{admin_id} "
            f"del {admin_date}" + (f"\n{notes}" if notes else "")
        ),
    ))

    # La dose fittizia viene riclassificata come spreco: lo stesso volume
    # esce dalle somministrazioni ed entra negli sprechi, quindi il rimanente
    # non cambia. Delta 0 aggiorna solo cache dello spreco e status.
    prep_repo._apply_event_delta(prep_id, Decimal('0'))

    return True, f"✅ Prep #{prep_id}: {wastage_ml}ml spreco, admin #{admin_id} eliminata"


def _soft_delete_administration(conn: sqlite3.Connection, admin_id: int) -> None:
    """Marca come eliminata una somministrazione fittizia."""
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE administrations SET deleted_at = ? WHERE id = ?",
        (datetime.now().isoformat(), admin_id)
    )
    conn.commit()


def reconcile_all_wastage(db_path: str, dry_run: bool = True) -> None:
    """
    Riconcilia tutte le somministrazioni fittizie.
    
    Args:
        db_path: Path al database
        dry_run: Se True, simula senza modificare
    """
    print("=" * 70)
    print("RICONCILIAZIONE WASTAGE - Conversione somministrazioni fittizie")
    print("=" * 70)
    print(f"Database: {db_path}")
    print(f"Modalità: {'DRY RUN (simulazione)' if dry_run else 'LIVE (modifiche reali)'}")
    print()
    
    pm = PeptideManager(db_path)
    conn = pm.db.conn
    prep_repo = PreparationRepository(conn)
    
    # Trova somministrazioni fittizie
    fake_admins = find_fake_administrations(conn)
    
    print(f"📊 Somministrazioni fittizie trovate: {len(fake_admins)}")
    
    if not fake_admins:
        print("✅ Nessuna somministrazione fittizia da convertire!")
        return
    
    print("-" * 70)
    print("ANALISI SOMMINISTRAZIONI FITTIZIE")
    print("-" * 70)
    
    for admin_id, prep_id, dose_ml, notes, admin_date in fake_admins:
        note_preview = notes[:60] + "..." if notes and len(notes) > 60 else notes
        print(f"\nAdmin #{admin_id} → Prep #{prep_id}")
        print(f"  Dose: {dose_ml}ml")
        print(f"  Data: {admin_date}")
        print(f"  Note: {note_preview}")
    
    print("\n" + "-" * 70)
    print("CONVERSIONE")
    print("-" * 70)
    
    success_count = 0
    skip_count = 0
    error_count = 0
    
    for admin_id, prep_id, dose_ml, notes, admin_date in fake_admins:
        success, msg = reconcile_administration(
            admin_id=admin_id,
            prep_id=prep_id,
            wastage_ml=dose_ml,
            notes=notes or "",
            admin_date=admin_date,
            prep_repo=prep_repo,
            conn=conn,
            dry_run=dry_run
        )
        
        print(msg)
        
        if success:
            if msg.startswith("⚠️"):
                skip_count += 1
            else:
                success_count += 1
        else:
            error_count += 1
    
    # Summary
    print("\n" + "=" * 70)
    print("RIEPILOGO")
    print("=" * 70)
    print(f"✅ Convertite con successo: {success_count}")
    print(f"⚠️ Già convertite (skip): {skip_count}")
    print(f"❌ Errori: {error_count}")
    print(f"📊 Totale: {len(fake_admins)}")
    
    if dry_run:
        print("\n⚠️ QUESTO ERA UN DRY RUN - Nessuna modifica effettuata")
        print("💡 Esegui con --live per applicare le modifiche reali")
    else:
        print("\n✅ MODIFICHE APPLICATE AL DATABASE")
        print("💡 Verifica i risultati nella GUI")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Riconcilia somministrazioni fittizie VOLUME MANCANTE con wastage tracking"
    )
    parser.add_argument(
        "--db",
        default="data/development/peptide_management.db",
        help="Path al database (default: development)"
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Applica modifiche reali (default: dry run)"
    )
    
    args = parser.parse_args()
    
    reconcile_all_wastage(
        db_path=args.db,
        dry_run=not args.live
    )


if __name__ == "__main__":
    main()
