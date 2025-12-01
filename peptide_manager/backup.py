"""
Backup automatico database con gestione retention policy.

Funzionalità:
- Backup automatico alla chiusura dell'app
- Cleanup automatico backup vecchi
- Retention policy configurabile (giornalieri, settimanali, mensili)
"""

import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple


class DatabaseBackupManager:
    """Gestisce backup e cleanup del database."""
    
    def __init__(
        self,
        db_path: str,
        backup_dir: str = "data/backups/production",
        daily_retention_days: int = 30,
        weekly_retention_weeks: int = 12,
        monthly_retention_months: int = 12
    ):
        """
        Inizializza backup manager.
        
        Args:
            db_path: Path del database da backuppare
            backup_dir: Directory dove salvare i backup
            daily_retention_days: Giorni di retention per backup giornalieri
            weekly_retention_weeks: Settimane di retention per backup settimanali
            monthly_retention_months: Mesi di retention per backup mensili
        """
        self.db_path = Path(db_path)
        self.backup_dir = Path(backup_dir)
        self.daily_retention_days = daily_retention_days
        self.weekly_retention_weeks = weekly_retention_weeks
        self.monthly_retention_months = monthly_retention_months
        
        # Crea directory backup se non esiste
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def create_backup(self, label: str = "auto") -> str:
        """
        Crea backup del database.
        
        Args:
            label: Etichetta per il backup (auto, manual, etc.)
        
        Returns:
            Path del backup creato
        
        Raises:
            FileNotFoundError: Se il database non esiste
            IOError: Se il backup fallisce
        """
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database non trovato: {self.db_path}")
        
        # Timestamp per nome file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"peptide_management_backup_{timestamp}_{label}.db"
        backup_path = self.backup_dir / backup_name
        
        try:
            # Copia database
            shutil.copy2(self.db_path, backup_path)
            print(f"✅ Backup creato: {backup_path}")
            return str(backup_path)
        except Exception as e:
            raise IOError(f"Errore durante backup: {str(e)}")
    
    def get_all_backups(self) -> List[Tuple[Path, datetime]]:
        """
        Recupera lista di tutti i backup con timestamp.
        
        Returns:
            Lista di tuple (path, datetime)
        """
        backups = []
        
        for backup_file in self.backup_dir.glob("peptide_management_backup_*.db"):
            try:
                # Estrai timestamp dal nome file
                # Formato: peptide_management_backup_YYYYMMDD_HHMMSS_label.db
                parts = backup_file.stem.split("_")
                if len(parts) >= 4:
                    date_str = parts[3]  # YYYYMMDD
                    time_str = parts[4]  # HHMMSS
                    timestamp = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
                    backups.append((backup_file, timestamp))
            except (ValueError, IndexError):
                # Skip file con formato non valido
                continue
        
        # Ordina per timestamp (più recente prima)
        backups.sort(key=lambda x: x[1], reverse=True)
        return backups
    
    def cleanup_old_backups(self, dry_run: bool = False) -> dict:
        """
        Elimina backup vecchi secondo retention policy.
        
        Policy:
        - Giornalieri: mantiene 1 backup al giorno per N giorni
        - Settimanali: mantiene 1 backup a settimana per N settimane
        - Mensili: mantiene 1 backup al mese per N mesi
        
        Args:
            dry_run: Se True, non elimina ma mostra cosa verrebbe eliminato
        
        Returns:
            Dict con statistiche: {kept, deleted, total_size_freed}
        """
        backups = self.get_all_backups()
        
        if not backups:
            return {"kept": 0, "deleted": 0, "total_size_freed": 0}
        
        now = datetime.now()
        to_keep = set()
        
        # 1. Mantieni backup giornalieri (ultimi N giorni)
        daily_cutoff = now - timedelta(days=self.daily_retention_days)
        daily_dates = set()
        
        for backup_path, backup_time in backups:
            if backup_time >= daily_cutoff:
                # Mantieni un backup per giorno
                date_key = backup_time.date()
                if date_key not in daily_dates:
                    to_keep.add(backup_path)
                    daily_dates.add(date_key)
        
        # 2. Mantieni backup settimanali (oltre i giorni giornalieri)
        weekly_cutoff = now - timedelta(weeks=self.weekly_retention_weeks)
        weekly_dates = set()
        
        for backup_path, backup_time in backups:
            if daily_cutoff > backup_time >= weekly_cutoff:
                # Mantieni un backup per settimana (numero settimana dell'anno)
                week_key = (backup_time.year, backup_time.isocalendar()[1])
                if week_key not in weekly_dates:
                    to_keep.add(backup_path)
                    weekly_dates.add(week_key)
        
        # 3. Mantieni backup mensili (oltre le settimane settimanali)
        monthly_cutoff = now - timedelta(days=self.monthly_retention_months * 30)
        monthly_dates = set()
        
        for backup_path, backup_time in backups:
            if weekly_cutoff > backup_time >= monthly_cutoff:
                # Mantieni un backup per mese
                month_key = (backup_time.year, backup_time.month)
                if month_key not in monthly_dates:
                    to_keep.add(backup_path)
                    monthly_dates.add(month_key)
        
        # 4. Elimina backup non mantenuti
        deleted_count = 0
        total_size_freed = 0
        
        for backup_path, backup_time in backups:
            if backup_path not in to_keep:
                size = backup_path.stat().st_size
                
                if dry_run:
                    print(f"[DRY RUN] Eliminerebbe: {backup_path.name} ({backup_time}) - {size / 1024 / 1024:.2f} MB")
                else:
                    try:
                        backup_path.unlink()
                        print(f"🗑️  Eliminato backup vecchio: {backup_path.name} ({backup_time})")
                        deleted_count += 1
                        total_size_freed += size
                    except Exception as e:
                        print(f"⚠️  Errore eliminazione {backup_path.name}: {e}")
        
        return {
            "kept": len(to_keep),
            "deleted": deleted_count,
            "total_size_freed": total_size_freed
        }
    
    def restore_backup(self, backup_path: str, target_path: str = None) -> bool:
        """
        Ripristina database da backup.
        
        Args:
            backup_path: Path del backup da ripristinare
            target_path: Path destinazione (default: sovrascrivi db corrente)
        
        Returns:
            True se successo
        """
        backup_path = Path(backup_path)
        
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup non trovato: {backup_path}")
        
        target = Path(target_path) if target_path else self.db_path
        
        try:
            # Backup del database corrente prima di sovrascrivere
            if target.exists():
                safety_backup = target.parent / f"{target.stem}_before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                shutil.copy2(target, safety_backup)
                print(f"📦 Backup di sicurezza creato: {safety_backup}")
            
            # Ripristina
            shutil.copy2(backup_path, target)
            print(f"✅ Database ripristinato da: {backup_path}")
            return True
        except Exception as e:
            print(f"❌ Errore durante ripristino: {e}")
            return False
    
    def get_backup_stats(self) -> dict:
        """
        Ottieni statistiche sui backup.
        
        Returns:
            Dict con: total_count, total_size_mb, oldest, newest
        """
        backups = self.get_all_backups()
        
        if not backups:
            return {
                "total_count": 0,
                "total_size_mb": 0.0,
                "oldest": None,
                "newest": None
            }
        
        total_size = sum(b[0].stat().st_size for b in backups)
        
        return {
            "total_count": len(backups),
            "total_size_mb": total_size / 1024 / 1024,
            "oldest": backups[-1][1],
            "newest": backups[0][1]
        }


def create_backup_on_exit(db_path: str = "data/production/peptide_management.db") -> str:
    """
    Crea backup automatico alla chiusura dell'app.
    
    Args:
        db_path: Path del database
    
    Returns:
        Path del backup creato
    """
    manager = DatabaseBackupManager(db_path)
    backup_path = manager.create_backup(label="auto_exit")
    
    # Cleanup automatico
    stats = manager.cleanup_old_backups(dry_run=False)
    
    if stats["deleted"] > 0:
        print(f"🧹 Cleanup completato: {stats['deleted']} backup eliminati, "
              f"{stats['total_size_freed'] / 1024 / 1024:.2f} MB liberati")
    
    return backup_path


if __name__ == "__main__":
    # Test
    import argparse
    
    parser = argparse.ArgumentParser(description="Gestione backup database")
    parser.add_argument("--db", default="data/production/peptide_management.db", help="Path database")
    parser.add_argument("--backup", action="store_true", help="Crea backup")
    parser.add_argument("--cleanup", action="store_true", help="Cleanup backup vecchi")
    parser.add_argument("--dry-run", action="store_true", help="Dry run per cleanup")
    parser.add_argument("--stats", action="store_true", help="Mostra statistiche")
    
    args = parser.parse_args()
    
    manager = DatabaseBackupManager(args.db)
    
    if args.backup:
        backup_path = manager.create_backup(label="manual")
        print(f"Backup creato: {backup_path}")
    
    if args.cleanup:
        stats = manager.cleanup_old_backups(dry_run=args.dry_run)
        print(f"Cleanup completato: {stats}")
    
    if args.stats:
        stats = manager.get_backup_stats()
        print(f"Statistiche backup:")
        print(f"  Totale: {stats['total_count']} backup")
        print(f"  Dimensione: {stats['total_size_mb']:.2f} MB")
        print(f"  Più vecchio: {stats['oldest']}")
        print(f"  Più recente: {stats['newest']}")
