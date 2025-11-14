"""
Crea/aggiorna directory produzione separata da branch Git.

Questo script copia solo i file necessari per la produzione,
escludendo file di sviluppo, test, e documentazione.
"""

import shutil
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Set

# File e directory da copiare
ESSENTIAL_DIRS = [
    'peptide_manager',
    'scripts',  # CLI non essenziale se si usa solo GUI
]

ESSENTIAL_FILES = [
    'gui.py',
    'requirements.txt',
    'setup.py',
    'pytest.ini',  # Opzionale ma utile
]

# File e directory da escludere
EXCLUDE_PATTERNS = [
    '__pycache__',
    '*.pyc',
    '*.pyo',
    '.git',
    '.gitignore',
    'tests',
    'docs',
    '.cursor',
    '.cursorrules',
    'ARCHITECTURE.md',
    'DECISIONS.md',
    'REFACTORING_GUIDE.md',
    'REFACTORING_ISOLATION_PLAN.md',
    'WORKFLOW.md',
    'WORKFLOW_GIT_BRANCHES.md',
    'CONTRIBUTING.md',
    'CHANGELOG.md',
    'RELEASE_CHECKLIST.md',
    'GITHUB_TEMPLATES.md',
    'SESSION_LOG.md',
    '*.md',  # Escludi tutti i markdown (tranne README se vuoi)
    'migrations',  # Le migrazioni sono per sviluppo
    'peptide_manager.egg-info',
    'venv',
    'env',
    '.venv',
]

# File da includere anche se sono .md
INCLUDE_MD_FILES = [
    'README.md',
    'README_ENVIRONMENTS.md',
    'LICENSE',
]


def get_repo_root() -> Path:
    """Trova la root del repository Git."""
    current = Path(__file__).resolve().parent.parent
    
    # Cerca directory .git
    while current != current.parent:
        if (current / '.git').exists():
            return current
        current = current.parent
    
    raise RuntimeError("Repository Git non trovato. Assicurati di essere in un repo Git.")


def get_current_branch() -> str:
    """Ottiene il branch Git corrente."""
    try:
        result = subprocess.run(
            ['git', 'branch', '--show-current'],
            capture_output=True,
            text=True,
            check=True,
            cwd=get_repo_root()
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        raise RuntimeError("Impossibile determinare branch corrente. Verifica di essere in un repo Git.")


def checkout_branch(branch: str) -> None:
    """Cambia branch Git."""
    repo_root = get_repo_root()
    try:
        subprocess.run(
            ['git', 'checkout', branch],
            check=True,
            cwd=repo_root
        )
        print(f"[OK] Cambiato a branch: {branch}")
    except subprocess.CalledProcessError:
        raise RuntimeError(f"Impossibile cambiare a branch '{branch}'. Verifica che esista.")


def should_exclude(path: Path, repo_root: Path) -> bool:
    """Verifica se un path deve essere escluso."""
    rel_path = path.relative_to(repo_root)
    rel_str = str(rel_path)
    
    # Controlla pattern di esclusione
    for pattern in EXCLUDE_PATTERNS:
        if pattern in rel_str or path.name == pattern:
            # Eccezioni: file MD da includere
            if pattern == '*.md' and path.name in INCLUDE_MD_FILES:
                continue
            return True
    
    return False


def should_include(path: Path, repo_root: Path) -> bool:
    """Verifica se un path deve essere incluso."""
    rel_path = path.relative_to(repo_root)
    
    # File essenziali sempre inclusi
    if path.name in ESSENTIAL_FILES:
        return True
    
    # Directory essenziali sempre incluse
    for essential_dir in ESSENTIAL_DIRS:
        if essential_dir in rel_path.parts:
            return True
    
    # File MD da includere
    if path.name in INCLUDE_MD_FILES:
        return True
    
    # Altri file nella root (opzionale)
    if len(rel_path.parts) == 1 and path.is_file():
        # Includi file di configurazione comuni
        if path.suffix in ['.txt', '.ini', '.toml', '.yaml', '.yml']:
            return True
    
    return False


def copy_file(src: Path, dst: Path) -> None:
    """Copia un file mantenendo metadati."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def copy_directory(src: Path, dst: Path, repo_root: Path) -> None:
    """Copia una directory ricorsivamente, escludendo pattern."""
    if not src.exists():
        return
    
    for item in src.iterdir():
        if should_exclude(item, repo_root):
            continue
        
        dst_item = dst / item.name
        
        if item.is_dir():
            copy_directory(item, dst_item, repo_root)
        elif item.is_file():
            if should_include(item, repo_root) or not should_exclude(item, repo_root):
                copy_file(item, dst_item)


def create_backup(production_dir: Path) -> Path:
    """Crea backup della directory produzione esistente."""
    if not production_dir.exists():
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = production_dir.parent / f"{production_dir.name}.backup_{timestamp}"
    
    print(f"[BACKUP] Creo backup: {backup_dir}")
    shutil.copytree(production_dir, backup_dir, dirs_exist_ok=True)
    
    return backup_dir


def create_production_copy(
    production_dir: Path,
    source_branch: str = None,
    backup: bool = True
) -> bool:
    """
    Crea/aggiorna directory produzione da branch Git.
    
    Args:
        production_dir: Directory di destinazione produzione
        source_branch: Branch da cui copiare (default: current)
        backup: Se True, crea backup prima di sovrascrivere
    
    Returns:
        True se successo
    """
    repo_root = get_repo_root()
    
    print("="*60)
    print("CREAZIONE/AGGIORNAMENTO DIRECTORY PRODUZIONE")
    print("="*60)
    print(f"Repository: {repo_root}")
    print(f"Produzione: {production_dir}")
    
    # Determina branch sorgente
    if source_branch:
        current_branch = get_current_branch()
        print(f"Branch corrente: {current_branch}")
        print(f"Cambio a branch: {source_branch}")
        checkout_branch(source_branch)
        branch_to_restore = current_branch
    else:
        source_branch = get_current_branch()
        print(f"Usando branch corrente: {source_branch}")
        branch_to_restore = None
    
    try:
        # Backup se richiesto
        if backup and production_dir.exists():
            backup_path = create_backup(production_dir)
            if backup_path:
                print(f"[OK] Backup creato: {backup_path}")
        
        # Crea directory produzione
        production_dir.mkdir(parents=True, exist_ok=True)
        
        # Copia file essenziali
        print("\n[COPY] Copio file essenziali...")
        for file_name in ESSENTIAL_FILES:
            src_file = repo_root / file_name
            if src_file.exists():
                dst_file = production_dir / file_name
                copy_file(src_file, dst_file)
                print(f"   [OK] {file_name}")
        
        # Copia directory essenziali
        print("\n[COPY] Copio directory essenziali...")
        for dir_name in ESSENTIAL_DIRS:
            src_dir = repo_root / dir_name
            if src_dir.exists():
                dst_dir = production_dir / dir_name
                # Rimuovi directory esistente se presente
                if dst_dir.exists():
                    shutil.rmtree(dst_dir)
                copy_directory(src_dir, dst_dir, repo_root)
                print(f"   [OK] {dir_name}/")
        
        # Copia file MD da includere
        print("\n[COPY] Copio documentazione essenziale...")
        for md_file in INCLUDE_MD_FILES:
            src_file = repo_root / md_file
            if src_file.exists():
                dst_file = production_dir / md_file
                copy_file(src_file, dst_file)
                print(f"   [OK] {md_file}")
        
        # Crea link simbolico per database produzione (se possibile)
        # NOTA: Il database produzione rimane nel repo, la directory produzione
        # punta allo stesso file tramite link simbolico. Il database sviluppo
        # è separato e NON viene copiato.
        prod_db_src = repo_root / 'data' / 'production'
        prod_db_dst = production_dir / 'data' / 'production'
        
        if prod_db_src.exists():
            prod_db_dst.parent.mkdir(parents=True, exist_ok=True)
            
            # Prova a creare link simbolico (Windows richiede privilegi admin)
            try:
                if prod_db_dst.exists() or prod_db_dst.is_symlink():
                    if prod_db_dst.is_symlink():
                        prod_db_dst.unlink()
                    elif prod_db_dst.is_dir():
                        # Non rimuovere directory con database!
                        print(f"[WARN] Directory database già esistente: {prod_db_dst}")
                        print("   Mantenuta (non sovrascritta)")
                        print("   NOTA: Se è una copia, considera di rimuoverla e usare link simbolico")
                        return True
                
                # Usa mklink tramite cmd (funziona meglio su Windows anche senza admin se Developer Mode è abilitato)
                import subprocess
                try:
                    # Rimuovi se esiste già
                    if prod_db_dst.exists():
                        if prod_db_dst.is_symlink():
                            prod_db_dst.unlink()
                        else:
                            shutil.rmtree(prod_db_dst)
                    
                    # Crea link simbolico usando mklink
                    subprocess.run(
                        ['cmd', '/c', 'mklink', '/D', 
                         str(prod_db_dst), str(prod_db_src.resolve())],
                        check=True,
                        capture_output=True
                    )
                    print(f"\n[LINK] Link simbolico database produzione: {prod_db_dst} -> {prod_db_src}")
                    print("   [OK] Entrambe le directory usano lo stesso database")
                except subprocess.CalledProcessError:
                    # Fallback: prova symlink Python
                    prod_db_dst.symlink_to(prod_db_src.resolve(), target_is_directory=True)
                    print(f"\n[LINK] Link simbolico database produzione: {prod_db_dst} -> {prod_db_src}")
                    print("   [OK] Entrambe le directory usano lo stesso database")
            except (OSError, NotImplementedError) as e:
                # Fallback: copia directory (meno ideale ma funziona)
                print(f"\n[WARN] Link simbolico non disponibile (errore: {e})")
                print("   [COPY] Copio directory database (fallback)")
                print("   [WARN] NOTA: Avrai due copie del database. Usa solo quella nel repo!")
                if not prod_db_dst.exists():
                    shutil.copytree(prod_db_src, prod_db_dst, dirs_exist_ok=True)
                else:
                    print(f"   [WARN] Directory già esistente, mantenuta")
        
        # Crea .env.production se esiste
        env_prod_src = repo_root / '.env.production'
        if env_prod_src.exists():
            env_prod_dst = production_dir / '.env.production'
            copy_file(env_prod_src, env_prod_dst)
            print(f"   [OK] .env.production")
        
        print("\n" + "="*60)
        print("[OK] DIRECTORY PRODUZIONE CREATA/AGGIORNATA")
        print("="*60)
        print(f"\nPosizione: {production_dir}")
        print(f"Branch sorgente: {source_branch}")
        print(f"\nPer usare:")
        print(f"   cd {production_dir}")
        print(f"   python gui.py --env production")
        
        return True
        
    finally:
        # Ripristina branch originale se cambiato
        if branch_to_restore:
            print(f"\n[RESTORE] Ripristino branch: {branch_to_restore}")
            checkout_branch(branch_to_restore)


def main():
    """Entry point script."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Crea/aggiorna directory produzione separata da branch Git'
    )
    parser.add_argument(
        '--production-dir',
        type=str,
        default=r'C:\Users\ftaba\peptide-production',
        help='Directory di destinazione produzione (default: C:\\Users\\ftaba\\peptide-production)'
    )
    parser.add_argument(
        '--from-branch',
        type=str,
        default=None,
        help='Branch Git da cui copiare (default: branch corrente)'
    )
    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='Non creare backup prima di sovrascrivere'
    )
    
    args = parser.parse_args()
    
    production_dir = Path(args.production_dir).resolve()
    
    # Conferma se directory esiste
    if production_dir.exists():
        response = input(
            f"\n[WARN] La directory {production_dir} esiste già.\n"
            f"   Verrà creata una copia di backup e poi aggiornata.\n"
            f"   Continuare? (y/n): "
        )
        if response.lower() != 'y':
            print("Operazione annullata.")
            return
    
    try:
        success = create_production_copy(
            production_dir=production_dir,
            source_branch=args.from_branch,
            backup=not args.no_backup
        )
        
        if success:
            print("\n[OK] Completato con successo!")
        else:
            print("\n[ERROR] Errore durante la creazione.")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n[ERROR] Errore: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

