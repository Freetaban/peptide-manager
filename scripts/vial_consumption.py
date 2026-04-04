"""
Consumo fiale peptidi in un determinato periodo.

Uso:
  python scripts/vial_consumption.py
  python scripts/vial_consumption.py --start 2025-11-01 --end 2025-12-31
  python scripts/vial_consumption.py --start 2026-01-01 --grafico
  python scripts/vial_consumption.py --db data/development/peptide_management.db
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from peptide_manager import PeptideManager
from rich.console import Console
from rich.table import Table
from rich import box

DB_DEFAULT = "data/production/peptide_management.db"

console = Console()


def parse_args():
    p = argparse.ArgumentParser(description="Consumo fiale peptidi per periodo")
    p.add_argument("--start", metavar="YYYY-MM-DD", help="Data inizio (default: inizio storico)")
    p.add_argument("--end",   metavar="YYYY-MM-DD", help="Data fine   (default: oggi)")
    p.add_argument("--db",    default=DB_DEFAULT,   help=f"Path database (default: {DB_DEFAULT})")
    p.add_argument("--grafico", action="store_true", help="Mostra grafico matplotlib mensile")
    return p.parse_args()


def print_period_header(start, end):
    start_label = start or "inizio storico"
    end_label   = end   or "oggi"
    console.print(f"\n[bold cyan]Consumo peptidi[/bold cyan]  [dim]{start_label} -> {end_label}[/dim]\n")


def print_by_peptide(by_peptide):
    t = Table(
        title="mg consumati per peptide",
        box=box.SIMPLE_HEAVY,
        show_footer=True,
    )
    t.add_column("Peptide",       style="bold white")
    t.add_column("mg totali",     justify="right", style="green",  footer=f"{sum(r['total_mg'] for r in by_peptide):.1f}")
    t.add_column("Preparazioni",  justify="right", style="cyan",   footer=str(sum(r['preparations_count'] for r in by_peptide)))
    t.add_column("Tipo",          style="dim")

    for r in by_peptide:
        tipo = "[yellow]blend[/yellow]" if r["is_blend_component"] else "singolo"
        t.add_row(
            r["peptide_name"],
            f"{r['total_mg']:.1f}",
            str(r["preparations_count"]),
            tipo,
        )

    console.print(t)


def print_by_batch(by_batch):
    t = Table(
        title="fiale fisiche per batch",
        box=box.SIMPLE_HEAVY,
        show_footer=True,
    )
    t.add_column("Prodotto",     style="bold white")
    t.add_column("Fiale usate",  justify="right", style="magenta", footer=str(sum(r["vials_used"] for r in by_batch)))
    t.add_column("Composizione", style="dim")

    for r in by_batch:
        comp = "  +  ".join(
            f"{c['peptide_name']} {c['mg_per_vial']:.0f}mg"
            for c in r["components"]
        )
        blend_tag = " [yellow][blend][/yellow]" if r["is_blend"] else ""
        t.add_row(
            r["product_name"] + blend_tag,
            str(r["vials_used"]),
            comp,
        )

    console.print(t)


def show_monthly_chart(pm, start, end):
    """Grafico a barre: mg per peptide per mese."""
    import sqlite3
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker
    from collections import defaultdict

    date_filter = "pr.deleted_at IS NULL"
    params = []
    if start:
        date_filter += " AND pr.preparation_date >= ?"
        params.append(start)
    if end:
        date_filter += " AND pr.preparation_date <= ?"
        params.append(end)

    cursor = pm.conn.cursor()
    cursor.execute(f"""
        SELECT
            strftime('%Y-%m', pr.preparation_date) AS mese,
            p.name                                  AS peptide,
            SUM(pr.vials_used * bc.mg_per_vial)    AS mg
        FROM preparations pr
        JOIN batches b ON b.id = pr.batch_id
        JOIN batch_composition bc ON bc.batch_id = b.id
        JOIN peptides p ON p.id = bc.peptide_id
        WHERE {date_filter}
        GROUP BY mese, p.id
        ORDER BY mese, p.name
    """, params)
    rows = cursor.fetchall()

    if not rows:
        console.print("[yellow]Nessun dato per il grafico.[/yellow]")
        return

    # Struttura: {peptide: {mese: mg}}
    data = defaultdict(dict)
    mesi = sorted({r[0] for r in rows})
    peptidi = sorted({r[1] for r in rows})
    for mese, peptide, mg in rows:
        data[peptide][mese] = mg

    import numpy as np
    x = np.arange(len(mesi))
    width = 0.8 / max(len(peptidi), 1)

    fig, ax = plt.subplots(figsize=(max(8, len(mesi) * 1.5), 5))
    colors = plt.cm.tab10.colors

    for i, peptide in enumerate(peptidi):
        valori = [data[peptide].get(m, 0) for m in mesi]
        offset = (i - len(peptidi) / 2 + 0.5) * width
        ax.bar(x + offset, valori, width, label=peptide, color=colors[i % len(colors)])

    ax.set_title("Consumo peptidi per mese (mg)")
    ax.set_xlabel("Mese")
    ax.set_ylabel("mg")
    ax.set_xticks(x)
    ax.set_xticklabels(mesi, rotation=45, ha="right")
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    plt.show()


def main():
    args = parse_args()

    try:
        pm = PeptideManager(args.db)
    except Exception as e:
        console.print(f"[red]Errore apertura database:[/red] {e}")
        sys.exit(1)

    result = pm.get_vial_consumption(start_date=args.start, end_date=args.end)

    if not result["by_peptide"]:
        console.print("[yellow]Nessuna preparazione trovata nel periodo indicato.[/yellow]")
        sys.exit(0)

    print_period_header(args.start, args.end)
    print_by_peptide(result["by_peptide"])
    print_by_batch(result["by_batch"])

    if args.grafico:
        show_monthly_chart(pm, args.start, args.end)


if __name__ == "__main__":
    main()
