"""
Janoshik Market View
Visualizzazione e gestione dati Janoshik: classifiche supplier, trends peptidi, ricerca vendor
"""

import flet as ft
from datetime import datetime
import time
import threading

# Import Janoshik components
try:
    from peptide_manager.janoshik.views_logic import JanoshikViewsLogic, TimeWindow
    from peptide_manager.janoshik import JanoshikManager, LLMProvider
    from peptide_manager.janoshik.repositories import JanoshikCertificateRepository, SupplierRankingRepository
    from peptide_manager.janoshik.models import JanoshikCertificate, SupplierRanking
    HAS_JANOSHIK = True
except ImportError:
    HAS_JANOSHIK = False


class JanoshikView(ft.Container):
    """Vista mercato Janoshik con 4 tab: classifica fornitori, trends peptidi, ricerca vendor, dettagli vendor"""
    
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.expand = True
        self.padding = 20
        
        if not HAS_JANOSHIK:
            self.content = self._build_error_view("Modulo Janoshik non disponibile")
            return
        
        try:
            # Inizializza logic layer
            self.janoshik_logic = JanoshikViewsLogic(app.db_path)
            self.content = self._build_main_view()
        except Exception as e:
            self.content = self._build_error_view(f"Errore caricamento: {str(e)}")
    
    def _build_error_view(self, message):
        """Vista errore"""
        return ft.Column([
            ft.Icon(ft.Icons.ERROR_OUTLINE, size=64, color=ft.Colors.RED_400),
            ft.Text(message, size=16, color=ft.Colors.RED_400),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20)
    
    def _get_janoshik_url(self) -> str:
        """Recupera URL Janoshik dalle preferenze"""
        cursor = self.app.manager.db.conn.cursor()
        cursor.execute(
            "SELECT preference_value FROM user_preferences WHERE preference_key = 'janoshik_base_url'"
        )
        row = cursor.fetchone()
        return row[0] if row else "https://public.janoshik.com/"
    
    def _set_janoshik_url(self, url: str):
        """Salva URL Janoshik nelle preferenze"""
        cursor = self.app.manager.db.conn.cursor()
        cursor.execute("""
            INSERT INTO user_preferences (preference_key, preference_value, value_type, category, description)
            VALUES ('janoshik_base_url', ?, 'string', 'janoshik', 'URL base per scraping certificati Janoshik')
            ON CONFLICT(preference_key) DO UPDATE SET 
                preference_value = excluded.preference_value,
                updated_at = CURRENT_TIMESTAMP
        """, (url,))
        self.app.manager.db.conn.commit()
    
    def _build_main_view(self):
        """Vista principale con tab"""
        # Tab per le quattro viste
        tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[
                ft.Tab(
                    text="Classifica Fornitori",
                    icon=ft.Icons.LEADERBOARD,
                    content=self._build_supplier_rankings_tab(),
                ),
                ft.Tab(
                    text="Peptidi Trend",
                    icon=ft.Icons.TRENDING_UP,
                    content=self._build_peptide_rankings_tab(),
                ),
                ft.Tab(
                    text="Cerca Vendor",
                    icon=ft.Icons.SEARCH,
                    content=self._build_vendor_search_tab(),
                ),
                ft.Tab(
                    text="Dettagli Vendor",
                    icon=ft.Icons.STORE,
                    content=self._build_vendor_details_tab(),
                ),
            ],
            expand=True,
        )
        
        # URL info e settings
        current_url = self._get_janoshik_url()
        url_info = ft.Row([
            ft.Icon(ft.Icons.LINK, size=16, color=ft.Colors.BLUE_400),
            ft.Text(f"URL Janoshik: ", size=12, color=ft.Colors.GREY_400),
            ft.Text(current_url, size=12, color=ft.Colors.BLUE_300, weight=ft.FontWeight.BOLD),
            ft.IconButton(
                icon=ft.Icons.SETTINGS,
                icon_size=16,
                tooltip="Modifica URL Janoshik",
                on_click=lambda e: self._show_url_settings_dialog(),
            ),
        ], spacing=5)
        
        # Pulsante aggiornamento database
        update_db_button = ft.ElevatedButton(
            "🔄 Aggiorna Database Janoshik",
            icon=ft.Icons.CLOUD_DOWNLOAD,
            tooltip="Scarica nuovi certificati da janoshik.com",
            on_click=lambda e: self._show_update_dialog(),
            bgcolor=ft.Colors.BLUE_700,
            color=ft.Colors.WHITE,
        )
        
        return ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.ANALYTICS, size=32),
                ft.Text(
                    "Mercato Janoshik - Analisi Qualità Fornitori",
                    size=24,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Container(expand=True),
                update_db_button,
            ], spacing=10, alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            url_info,
            ft.Divider(),
            tabs,
        ], spacing=10, expand=True)
    
    def _build_supplier_rankings_tab(self):
        """Tab classifica fornitori"""
        import sqlite3
        from datetime import datetime, timedelta
        import statistics
        
        time_window_dropdown = ft.Dropdown(
            label="Periodo",
            width=200,
            value="ALL",
            options=[
                ft.dropdown.Option(key="MONTH", text="Ultimo Mese"),
                ft.dropdown.Option(key="QUARTER", text="Ultimo Trimestre"),
                ft.dropdown.Option(key="YEAR", text="Ultimo Anno"),
                ft.dropdown.Option(key="ALL", text="Tutti i Tempi"),
            ],
        )
        
        last_update_text = ft.Text("", size=11, color=ft.Colors.GREY_500, italic=True)
        table_container = ft.Container(expand=True)
        
        def calculate_score(avg_purity, std_purity, total_certs):
            """Calcola score (60% purezza + 30% consistenza + 10% volume)"""
            purity_score = avg_purity
            
            if std_purity <= 1.0:
                consistency_score = 100
            elif std_purity <= 2.0:
                consistency_score = 90
            elif std_purity <= 3.0:
                consistency_score = 80
            elif std_purity <= 5.0:
                consistency_score = 70
            else:
                consistency_score = max(0, 60 - (std_purity - 5) * 5)
            
            if total_certs >= 20:
                volume_score = 100
            elif total_certs >= 15:
                volume_score = 90
            elif total_certs >= 10:
                volume_score = 80
            elif total_certs >= 5:
                volume_score = 70
            else:
                volume_score = 50
            
            return round(purity_score * 0.6 + consistency_score * 0.3 + volume_score * 0.1, 1)
        
        def load_rankings(time_window_key):
            try:
                conn = sqlite3.connect(self.app.db_path)
                cur = conn.cursor()
                
                # Calcola data cutoff per filtro temporale
                date_filter = ""
                if time_window_key != "ALL":
                    days_map = {"MONTH": 30, "QUARTER": 90, "YEAR": 365}
                    cutoff = (datetime.now() - timedelta(days=days_map[time_window_key])).strftime('%Y-%m-%d')
                    date_filter = f"AND test_date >= '{cutoff}'"
                
                # Se "Tutti i Tempi", usa score pre-calcolato
                if time_window_key == "ALL":
                    cur.execute("""
                        SELECT 
                            name,
                            janoshik_quality_score,
                            janoshik_certificates,
                            reliability_rating
                        FROM suppliers
                        WHERE deleted_at IS NULL 
                          AND janoshik_certificates >= 3
                          AND janoshik_quality_score IS NOT NULL
                        ORDER BY janoshik_quality_score DESC
                        LIMIT 50
                    """)
                    
                    suppliers_data = []
                    for row in cur.fetchall():
                        name, quality_score, total_certs, rating = row
                        
                        # Statistiche purezza
                        cur.execute("""
                            SELECT 
                                AVG(purity_percentage),
                                MIN(purity_percentage),
                                MAX(purity_percentage)
                            FROM janoshik_certificates
                            WHERE supplier_name = ?
                              AND purity_percentage > 0
                        """, (name,))
                        
                        purity_stats = cur.fetchone()
                        avg_purity = purity_stats[0] if purity_stats[0] else 0
                        min_purity = purity_stats[1] if purity_stats[1] else 0
                        max_purity = purity_stats[2] if purity_stats[2] else 0
                        
                        if quality_score >= 95:
                            quality_badge = "🏆 Eccellente"
                        elif quality_score >= 90:
                            quality_badge = "⭐ Ottimo"
                        elif quality_score >= 85:
                            quality_badge = "✓ Buono"
                        elif quality_score >= 80:
                            quality_badge = "○ Discreto"
                        else:
                            quality_badge = "- Base"
                        
                        suppliers_data.append({
                            'name': name,
                            'score': quality_score,
                            'certificates': total_certs,
                            'avg_purity': avg_purity,
                            'min_purity': min_purity,
                            'max_purity': max_purity,
                            'quality_badge': quality_badge,
                            'rating': rating or 0
                        })
                
                else:
                    # Per altri periodi, calcola score al volo
                    cur.execute(f"""
                        SELECT supplier_name, purity_percentage
                        FROM janoshik_certificates
                        WHERE purity_percentage > 0
                          {date_filter}
                    """)
                    
                    # Raggruppa per supplier
                    supplier_certs = {}
                    for supplier_name, purity in cur.fetchall():
                        if supplier_name not in supplier_certs:
                            supplier_certs[supplier_name] = []
                        supplier_certs[supplier_name].append(purity)
                    
                    suppliers_data = []
                    for supplier_name, purities in supplier_certs.items():
                        if len(purities) < 3:  # Min 3 certificati
                            continue
                        
                        avg_purity = statistics.mean(purities)
                        min_purity = min(purities)
                        max_purity = max(purities)
                        std_purity = statistics.stdev(purities) if len(purities) > 1 else 0
                        total_certs = len(purities)
                        
                        score = calculate_score(avg_purity, std_purity, total_certs)
                        
                        if score >= 95:
                            quality_badge = "🏆 Eccellente"
                        elif score >= 90:
                            quality_badge = "⭐ Ottimo"
                        elif score >= 85:
                            quality_badge = "✓ Buono"
                        elif score >= 80:
                            quality_badge = "○ Discreto"
                        else:
                            quality_badge = "- Base"
                        
                        rating = 5 if score >= 90 else (4 if score >= 80 else (3 if score >= 70 else (2 if score >= 60 else 1)))
                        
                        suppliers_data.append({
                            'name': supplier_name,
                            'score': score,
                            'certificates': total_certs,
                            'avg_purity': avg_purity,
                            'min_purity': min_purity,
                            'max_purity': max_purity,
                            'quality_badge': quality_badge,
                            'rating': rating
                        })
                    
                    # Ordina per score
                    suppliers_data = sorted(suppliers_data, key=lambda x: x['score'], reverse=True)[:50]
                
                conn.close()
                
                rows = []
                for rank, item in enumerate(suppliers_data, 1):
                    rows.append(ft.DataRow(cells=[
                        ft.DataCell(ft.Text(f"#{rank}", weight=ft.FontWeight.BOLD)),
                        ft.DataCell(ft.Text(item['name'], size=14)),
                        ft.DataCell(ft.Text(f"{item['score']:.1f}", color=ft.Colors.PURPLE_400, weight=ft.FontWeight.BOLD)),
                        ft.DataCell(ft.Text(f"{item['certificates']}", color=ft.Colors.BLUE_400)),
                        ft.DataCell(ft.Text(f"{item['avg_purity']:.2f}%", weight=ft.FontWeight.BOLD)),
                        ft.DataCell(ft.Text(f"{item['min_purity']:.2f}%", color=ft.Colors.ORANGE_300)),
                        ft.DataCell(ft.Text(f"{item['max_purity']:.2f}%", color=ft.Colors.GREEN_300)),
                        ft.DataCell(ft.Text(item['quality_badge'], size=12)),
                        ft.DataCell(ft.Text("⭐" * item['rating'], size=11)),
                    ]))
                
                table_container.content = ft.Column([
                    ft.DataTable(
                        columns=[
                            ft.DataColumn(ft.Text("#", weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Fornitore", weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Score", weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Certificati", weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Purezza Media", weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Min", weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Max", weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Qualità", weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Rating", weight=ft.FontWeight.BOLD)),
                        ],
                        rows=rows,
                        border=ft.border.all(1, ft.Colors.GREY_800),
                        border_radius=10,
                        vertical_lines=ft.BorderSide(1, ft.Colors.GREY_800),
                        horizontal_lines=ft.BorderSide(1, ft.Colors.GREY_900),
                    ),
                ], scroll=ft.ScrollMode.AUTO, expand=True)
                
                last_update_text.value = f"Ultimo aggiornamento: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
                
                if self.page:
                    table_container.update()
                    last_update_text.update()
            except Exception as e:
                import traceback
                table_container.content = ft.Text(f"Errore: {str(e)}\n{traceback.format_exc()}", color=ft.Colors.RED_400)
                if self.page:
                    table_container.update()
        
        time_window_dropdown.on_change = lambda e: load_rankings(e.control.value)
        
        container = ft.Container(
            content=ft.Column([
                ft.Row([
                    time_window_dropdown,
                    ft.ElevatedButton("Aggiorna", icon=ft.Icons.REFRESH, 
                                     on_click=lambda e: load_rankings(time_window_dropdown.value)),
                    ft.Text("Top 50 fornitori - Score: 60% purezza + 30% consistenza + 10% volume (min 3 certificati)",
                           color=ft.Colors.GREY_400, italic=True, size=12),
                    ft.Container(expand=True),
                    last_update_text,
                ], alignment=ft.MainAxisAlignment.START, spacing=10),
                ft.Divider(),
                table_container,
            ], spacing=10, expand=True),
            padding=20,
            expand=True,
        )
        
        # Auto-load
        threading.Thread(target=lambda: (time.sleep(0.1), load_rankings(time_window_dropdown.value)), daemon=True).start()
        
        return container
    
    def _build_peptide_rankings_tab(self):
        """Tab peptidi più testati."""
        from datetime import datetime
        from peptide_manager.janoshik.views_logic import JanoshikViewsLogic, TimeWindow
        
        janoshik_logic = JanoshikViewsLogic(self.app.db_path)
        
        # Dropdown periodo
        time_window_dropdown = ft.Dropdown(
            label="Periodo",
            width=200,
            value="QUARTER",
            options=[
                ft.dropdown.Option(key="MONTH", text="Ultimo Mese"),
                ft.dropdown.Option(key="QUARTER", text="Ultimo Trimestre"),
                ft.dropdown.Option(key="YEAR", text="Ultimo Anno"),
                ft.dropdown.Option(key="ALL", text="Tutti i Tempi"),
            ],
        )
        
        last_update_text = ft.Text("", size=11, color=ft.Colors.GREY_500, italic=True)
        table_container = ft.Container(expand=True)
        
        def load_peptide_rankings(time_window_key):
            try:
                time_window = TimeWindow[time_window_key]
                rankings = janoshik_logic.get_peptide_rankings(time_window, limit=30)
                
                rows = []
                for item in rankings:
                    rows.append(ft.DataRow(cells=[
                        ft.DataCell(ft.Text(f"#{item.rank}", weight=ft.FontWeight.BOLD)),
                        ft.DataCell(ft.Text(item.peptide_name, size=14)),
                        ft.DataCell(ft.Text(f"{item.test_count}", color=ft.Colors.BLUE_400, weight=ft.FontWeight.BOLD)),
                        ft.DataCell(ft.Text(f"{item.vendor_count}", color=ft.Colors.PURPLE_300)),
                        ft.DataCell(ft.Text(item.popularity_badge, size=11, color=ft.Colors.ORANGE_400 if "🔥" in item.popularity_badge else ft.Colors.GREY_400)),
                    ]))
                
                table_container.content = ft.Column([
                    ft.DataTable(
                        columns=[
                            ft.DataColumn(ft.Text("#", weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Peptide", weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Test Effettuati", weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Fornitori", weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Trend", weight=ft.FontWeight.BOLD)),
                        ],
                        rows=rows,
                        border=ft.border.all(1, ft.Colors.GREY_800),
                        border_radius=10,
                    ),
                ], scroll=ft.ScrollMode.AUTO, expand=True)
                
                last_update_text.value = f"Ultimo aggiornamento: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
                self.page.update()
                
            except Exception as e:
                table_container.content = ft.Text(f"Errore: {str(e)}", color=ft.Colors.RED_400)
                self.page.update()
        
        time_window_dropdown.on_change = lambda e: load_peptide_rankings(e.control.value)
        
        container = ft.Container(
            content=ft.Column([
                ft.Row([
                    time_window_dropdown,
                    ft.ElevatedButton("Aggiorna", icon=ft.Icons.REFRESH, on_click=lambda e: load_peptide_rankings(time_window_dropdown.value)),
                    ft.Container(expand=True),
                    last_update_text,
                ], spacing=10),
                ft.Divider(),
                table_container,
            ], spacing=10, expand=True),
            padding=20,
            expand=True,
        )
        
        # Auto-load
        import threading
        threading.Thread(target=lambda: (time.sleep(0.1), load_peptide_rankings(time_window_dropdown.value)), daemon=True).start()
        
        return container
    
    def _build_vendor_search_tab(self):
        """Tab ricerca vendor per peptide."""
        from peptide_manager.janoshik.views_logic import JanoshikViewsLogic
        
        janoshik_logic = JanoshikViewsLogic(self.app.db_path)
        
        try:
            all_peptides = sorted(janoshik_logic.get_peptide_suggestions("", limit=200))
        except:
            all_peptides = []
        
        search_field = ft.TextField(label="Cerca Peptide", hint_text="Filtra peptidi...", width=400, autofocus=True)
        filtered_dropdown = ft.Dropdown(label="Seleziona Peptide", width=400, options=[ft.dropdown.Option(p) for p in all_peptides])
        results_container = ft.Container(expand=True)
        
        def filter_peptides(e):
            query = search_field.value.lower() if search_field.value else ""
            filtered = [p for p in all_peptides if not query or query in p.lower()]
            filtered_dropdown.options = [ft.dropdown.Option(p) for p in filtered]
            filtered_dropdown.value = None
            filtered_dropdown.update()
        
        search_field.on_change = filter_peptides
        
        def search_vendors(e):
            peptide_name = filtered_dropdown.value
            if not peptide_name:
                results_container.content = ft.Text("Seleziona un peptide", color=ft.Colors.GREY_400, italic=True)
                results_container.update()
                return
            
            try:
                result = janoshik_logic.search_vendors_for_peptide(peptide_name)
                
                if not result['all_vendors']:
                    results_container.content = ft.Text(f"Nessun vendor trovato per '{peptide_name}'", color=ft.Colors.GREY_400)
                    results_container.update()
                    return
                
                best = result['best_vendor']
                best_card = ft.Container(
                    content=ft.Column([
                        ft.Row([ft.Icon(ft.Icons.STAR, color=ft.Colors.AMBER_400), ft.Text("MIGLIOR FORNITORE", weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_400)]),
                        ft.Text(best.supplier_name, size=18, weight=ft.FontWeight.BOLD),
                        ft.Text(f"Purezza: {best.avg_purity:.2f}% | Certificati: {best.certificates} | Score: {best.recommendation_score:.0f}/100"),
                    ]),
                    bgcolor=ft.Colors.GREY_900,
                    padding=12,
                    border_radius=8,
                    border=ft.border.all(2, ft.Colors.AMBER_700),
                )
                
                rows = []
                for v in result['all_vendors']:
                    rows.append(ft.DataRow(cells=[
                        ft.DataCell(ft.Text(v.supplier_name)),
                        ft.DataCell(ft.Text(f"{v.certificates}")),
                        ft.DataCell(ft.Text(f"{v.avg_purity:.2f}%", weight=ft.FontWeight.BOLD)),
                        ft.DataCell(ft.Text(f"{v.recommendation_score:.0f}/100", color=ft.Colors.PURPLE_400)),
                    ]))
                
                results_container.content = ft.Column([
                    best_card,
                    ft.Text(f"Tutti i fornitori ({len(result['all_vendors'])})", size=16, weight=ft.FontWeight.BOLD),
                    ft.DataTable(
                        columns=[
                            ft.DataColumn(ft.Text("Fornitore", weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Certificati", weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Purezza Media", weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Score", weight=ft.FontWeight.BOLD)),
                        ],
                        rows=rows,
                    ),
                ], spacing=15, scroll=ft.ScrollMode.AUTO, expand=True)
                results_container.update()
                
            except Exception as ex:
                results_container.content = ft.Text(f"Errore: {str(ex)}", color=ft.Colors.RED_400)
                results_container.update()
        
        filtered_dropdown.on_change = search_vendors
        
        results_container.content = ft.Column([
            ft.Icon(ft.Icons.INFO_OUTLINE, size=48, color=ft.Colors.BLUE_400),
            ft.Text("Cerca il miglior fornitore per un peptide", size=16, color=ft.Colors.GREY_400),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        
        return ft.Container(
            content=ft.Column([
                ft.Row([search_field, filtered_dropdown, ft.ElevatedButton("Cerca", icon=ft.Icons.SEARCH, on_click=search_vendors)]),
                ft.Divider(),
                results_container,
            ], expand=True),
            padding=20,
            expand=True,
        )
    
    def _build_vendor_details_tab(self):
        """Tab dettagli certificati vendor."""
        from datetime import datetime
        from peptide_manager.janoshik.views_logic import JanoshikViewsLogic
        
        janoshik_logic = JanoshikViewsLogic(self.app.db_path)
        
        try:
            all_vendors = janoshik_logic.get_all_vendor_names()
        except:
            all_vendors = []
        
        vendor_dropdown = ft.Dropdown(label="Seleziona Vendor", width=400, options=[ft.dropdown.Option(v) for v in all_vendors])
        table_container = ft.Container(expand=True)
        stats_container = ft.Container(visible=False)
        
        def load_vendor_certificates(e):
            vendor_name = vendor_dropdown.value
            if not vendor_name:
                table_container.content = ft.Text("Seleziona un vendor", color=ft.Colors.GREY_400)
                stats_container.visible = False
                self.page.update()
                return
            
            try:
                certificates = janoshik_logic.get_vendor_certificates(vendor_name)
                
                if not certificates:
                    table_container.content = ft.Text(f"Nessun certificato per '{vendor_name}'", color=ft.Colors.GREY_400)
                    stats_container.visible = False
                    self.page.update()
                    return
                
                # Stats (escludi purity=0 o NULL dai calcoli)
                purities = [c['purity_percent'] for c in certificates if c['purity_percent'] > 0]
                
                # Get supplier website from first certificate
                supplier_website = certificates[0].get('supplier_website') if certificates else None
                
                stats_items = [
                    ft.Text(f"Certificati: {len(certificates)}", weight=ft.FontWeight.BOLD),
                ]
                
                if purities:
                    avg_purity = sum(purities) / len(purities)
                    stats_items.extend([
                        ft.Text(f"Purezza media: {avg_purity:.2f}%", color=ft.Colors.GREEN_400),
                        ft.Text(f"Range: {min(purities):.2f}% - {max(purities):.2f}%"),
                    ])
                else:
                    stats_items.append(ft.Text("(Nessun test di purezza disponibile)", color=ft.Colors.GREY_500))
                
                if supplier_website:
                    stats_items.append(ft.Text("|", color=ft.Colors.GREY_600))
                    stats_items.append(ft.TextButton(
                        supplier_website,
                        icon=ft.Icons.LINK,
                        on_click=lambda _: self.page.launch_url(supplier_website),
                        style=ft.ButtonStyle(color=ft.Colors.BLUE_400),
                        tooltip="Apri sito web",
                    ))
                
                stats_container.content = ft.Row(stats_items, spacing=10)
                stats_container.visible = True
                
                rows = []
                for cert in certificates:
                    test_date = datetime.fromisoformat(cert['test_date']).strftime("%d/%m/%Y") if cert['test_date'] else "N/A"
                    purity = cert['purity_percent']
                    
                    # Mostra "NA" per purity=0 o NULL (test su miscele/quantità)
                    if purity == 0 or purity is None:
                        purity_text = "NA"
                        purity_color = ft.Colors.GREY_500
                    else:
                        purity_text = f"{purity:.2f}%"
                        purity_color = ft.Colors.GREEN_400 if purity >= 99.0 else ft.Colors.YELLOW_400 if purity >= 98.0 else ft.Colors.ORANGE_400
                    
                    # Certificate link button
                    local_image_path = cert.get('local_image_path')
                    cert_link = None
                    if local_image_path:
                        import os
                        full_path = os.path.abspath(local_image_path)
                        cert_link = ft.IconButton(
                            icon=ft.Icons.IMAGE,
                            icon_size=18,
                            tooltip=f"Visualizza certificato: {os.path.basename(local_image_path)}",
                            on_click=lambda _, path=full_path: self.page.launch_url(f"file:///{path.replace(chr(92), '/')}"),
                            icon_color=ft.Colors.BLUE_400,
                        )
                    else:
                        cert_link = ft.Icon(ft.Icons.IMAGE_NOT_SUPPORTED, size=18, color=ft.Colors.GREY_600, tooltip="Immagine non disponibile")
                    
                    rows.append(ft.DataRow(cells=[
                        ft.DataCell(ft.Text(f"#{cert['certificate_id']}", size=12)),
                        ft.DataCell(ft.Text(test_date, size=12)),
                        ft.DataCell(ft.Text(cert['peptide_name'], size=12)),
                        ft.DataCell(ft.Text(purity_text, size=12, weight=ft.FontWeight.BOLD, color=purity_color)),
                        ft.DataCell(cert_link),
                    ]))
                
                table_container.content = ft.Column([
                    ft.DataTable(
                        columns=[
                            ft.DataColumn(ft.Text("ID", weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Data Test", weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Peptide", weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Purezza", weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Certificato", weight=ft.FontWeight.BOLD)),
                        ],
                        rows=rows,
                    ),
                ], scroll=ft.ScrollMode.AUTO, expand=True)
                
                self.page.update()
                
            except Exception as ex:
                table_container.content = ft.Text(f"Errore: {str(ex)}", color=ft.Colors.RED_400)
                self.page.update()
        
        vendor_dropdown.on_change = load_vendor_certificates
        
        table_container.content = ft.Column([
            ft.Icon(ft.Icons.INFO_OUTLINE, size=48, color=ft.Colors.GREY_600),
            ft.Text("Seleziona un vendor per vedere tutti i certificati", size=16, color=ft.Colors.GREY_400),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        
        return ft.Container(
            content=ft.Column([
                ft.Row([vendor_dropdown, ft.ElevatedButton("Carica", icon=ft.Icons.SEARCH, on_click=load_vendor_certificates)]),
                stats_container,
                ft.Divider(),
                table_container,
            ], expand=True),
            padding=20,
            expand=True,
        )
    
    def _show_update_dialog(self):
        """Dialog progresso aggiornamento database Janoshik"""
        try:
            cert_repo = JanoshikCertificateRepository(self.app.db_path)
            existing_count = cert_repo.count()
        except:
            existing_count = 0
        
        # Container progresso
        progress_container = ft.Container(
            visible=True,
            content=ft.Column([
                ft.Row([
                    ft.ProgressRing(width=20, height=20, stroke_width=2),
                    ft.Text("Aggiornamento in corso...", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_400),
                ], spacing=10),
            ], spacing=5),
            padding=20,
        )
        
        # Container risultati
        results_container = ft.Container(
            visible=False,
            content=ft.Column([
                ft.Text("", size=14, weight=ft.FontWeight.BOLD),
                ft.Text("", size=12, color=ft.Colors.GREY_400),
            ], spacing=5),
            padding=15,
            bgcolor=ft.Colors.SURFACE,
            border_radius=10,
        )
        
        # Dialog
        dialog = ft.AlertDialog(
            title=ft.Text("🔄 Aggiornamento Database Janoshik"),
            content=ft.Column([
                ft.Text(f"Database attuale: {existing_count} certificati", size=12, color=ft.Colors.GREY_400),
                ft.Divider(),
                progress_container,
                results_container,
            ], tight=True, scroll=ft.ScrollMode.AUTO, height=400, width=600),
            actions=[
                ft.ElevatedButton("Chiudi", on_click=lambda e: (setattr(dialog, 'open', False), self.page.update()), disabled=True),
            ],
        )
        
        def update_progress(stage: str, message: str):
            """Aggiorna indicatore progresso - callback per manager."""
            # Aggiungi nuovo step
            progress_container.content.controls.append(
                ft.Row([
                    ft.Icon(ft.Icons.ARROW_RIGHT, color=ft.Colors.BLUE_400, size=16),
                    ft.Text(message, size=12),
                ], spacing=5)
            )
            self.page.update()
        
        def show_results(stats: dict):
            """Mostra risultati finali."""
            # Rimuovi working indicator
            if progress_container.content.controls:
                progress_container.content.controls[0] = ft.Row([
                    ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN_400, size=20),
                    ft.Text("Completato!", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400),
                ], spacing=10)
            
            progress_container.visible = False
            results_container.visible = True
            results_container.content = ft.Column([
                ft.Text("✅ Aggiornamento completato!", weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400, size=16),
                ft.Divider(),
                ft.Text(f"📥 Certificati scaricati: {stats.get('certificates_scraped', 0)}", size=13),
                ft.Text(f"🆕 Nuovi certificati: {stats.get('certificates_new', 0)}", size=13),
                ft.Text(f"✨ Processati: {stats.get('certificates_extracted', 0)}", size=13),
                ft.Text(f"📊 Rankings calcolati: {stats.get('rankings_calculated', 0)}", size=13),
            ], spacing=8)
            dialog.actions[0].disabled = False
            self.page.update()
        
        def run_update():
            """Esegue aggiornamento in background."""
            try:
                # Inizializza manager con provider GPT-4o
                from peptide_manager.janoshik.manager import JanoshikManager
                from peptide_manager.janoshik.llm_providers import LLMProvider
                
                manager = JanoshikManager(
                    self.app.db_path, 
                    llm_provider=LLMProvider.GPT4O
                )
                
                # Esegui aggiornamento completo
                stats = manager.run_full_update(
                    max_certificates=None,
                    progress_callback=update_progress
                )
                
                show_results(stats)
                
            except Exception as ex:
                import traceback
                traceback.print_exc()
                progress_container.visible = False
                results_container.visible = True
                results_container.content = ft.Column([
                    ft.Text("❌ Errore durante aggiornamento", color=ft.Colors.RED_400, weight=ft.FontWeight.BOLD),
                    ft.Text(str(ex), size=11, color=ft.Colors.RED_300),
                ])
                dialog.actions[0].disabled = False
                self.page.update()
        
        # Mostra dialog e avvia aggiornamento
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
        
        # Avvia in thread separato
        import threading
        threading.Thread(target=run_update, daemon=True).start()
    
    def _show_url_settings_dialog(self):
        """Dialog per modificare URL Janoshik"""
        current_url = self._get_janoshik_url()
        
        url_field = ft.TextField(
            label="URL Base Janoshik",
            value=current_url,
            hint_text="es: https://public.janoshik.com/",
            width=500,
            prefix_icon=ft.Icons.LINK,
        )
        
        status_text = ft.Text("", size=12)
        
        def save_url(e):
            """Salva nuovo URL"""
            new_url = url_field.value.strip()
            
            # Validazione base
            if not new_url:
                status_text.value = "❌ URL non può essere vuoto"
                status_text.color = ft.Colors.RED_400
                self.page.update()
                return
            
            if not new_url.startswith(('http://', 'https://')):
                status_text.value = "❌ URL deve iniziare con http:// o https://"
                status_text.color = ft.Colors.RED_400
                self.page.update()
                return
            
            # Rimuovi trailing slash se presente
            new_url = new_url.rstrip('/')
            
            try:
                self._set_janoshik_url(new_url)
                status_text.value = "✅ URL salvato con successo"
                status_text.color = ft.Colors.GREEN_400
                
                # Aggiorna anche l'URL nel scraper se esiste
                if hasattr(self, 'janoshik_logic'):
                    from peptide_manager.janoshik.scraper import JanoshikScraper
                    JanoshikScraper.BASE_URL = new_url + "/"
                
                self.page.update()
                
                # Chiudi dialog dopo 1 secondo
                import time, threading
                def close_after_delay():
                    time.sleep(1)
                    dialog.open = False
                    self.page.update()
                    # Ricarica la vista per mostrare nuovo URL
                    self.content = self._build_main_view()
                    self.update()
                
                threading.Thread(target=close_after_delay, daemon=True).start()
                
            except Exception as ex:
                status_text.value = f"❌ Errore: {ex}"
                status_text.color = ft.Colors.RED_400
                self.page.update()
        
        dialog = ft.AlertDialog(
            title=ft.Text("⚙️ Impostazioni URL Janoshik"),
            content=ft.Column([
                ft.Text(
                    "Modifica l'URL base per lo scraping dei certificati Janoshik.",
                    size=13,
                    color=ft.Colors.GREY_400,
                ),
                ft.Text(
                    "⚠️ Usa questa funzione solo se il sito Janoshik cambia dominio.",
                    size=12,
                    color=ft.Colors.ORANGE_400,
                    italic=True,
                ),
                ft.Divider(),
                url_field,
                status_text,
                ft.Divider(),
                ft.Container(
                    content=ft.Column([
                        ft.Text("💡 Suggerimenti:", size=12, weight=ft.FontWeight.BOLD),
                        ft.Text("• L'URL deve terminare con lo slash finale", size=11),
                        ft.Text("• URL default: https://public.janoshik.com/", size=11),
                        ft.Text("• Le modifiche sono permanenti", size=11),
                    ], spacing=4),
                    bgcolor=ft.Colors.BLUE_900,
                    padding=10,
                    border_radius=5,
                ),
            ], tight=True, width=550),
            actions=[
                ft.TextButton("Annulla", on_click=lambda e: (setattr(dialog, 'open', False), self.page.update())),
                ft.ElevatedButton(
                    "Salva",
                    icon=ft.Icons.SAVE,
                    on_click=save_url,
                    bgcolor=ft.Colors.GREEN_700,
                    color=ft.Colors.WHITE,
                ),
            ],
        )
        
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
