"""CyclesView - Enhanced dashboard for treatment cycles management (Flet GUI).

Step 1 Implementation: Tabs, progress bars, status indicators, quick actions,
and mini-calendar integration for comprehensive cycle tracking.
"""
import flet as ft
from gui_modular.components.data_table import DataTable, Column, Action
from gui_modular.components.dialogs import DialogBuilder
from gui_modular.components.forms import FormBuilder, Field, FieldType
from datetime import datetime, timedelta, date


def format_stock_report(report: dict) -> str:
    """Formatta il report di suggest_doses_from_inventory in testo semplice.

    Questa funzione è utile per i test unitari e per costruire il contenuto
    di dialog semplici nella UI.
    """
    lines = []
    per = report.get('per_peptide', {})
    mixes = report.get('mixes', [])

    lines.append('Disponibilità per peptide:')
    for pid, info in per.items():
        lines.append(f"- {info.get('name')} (id={pid}): {int(info.get('available_mcg', 0))} mcg disponibili; pianificato {int(info.get('planned_mcg', 0))} mcg")
        if info.get('mix_dependencies'):
            lines.append('  Dipendenze mix:')
            for m in info.get('mix_dependencies'):
                comp = ', '.join([f"{c['peptide_id']}:{c.get('mg_per_vial')}mg" for c in m.get('composition', [])])
                lines.append(f"   * {m.get('product_name')} (batch {m.get('batch_id')}) - fiale: {m.get('vials_remaining')} - comp: {comp} - supporta admin: {m.get('supported_admins_for_cycle')}")

    if mixes:
        lines.append('\nMix individuali (sintesi):')
        for m in mixes:
            comp = ', '.join([f"{c['peptide_id']}:{c.get('mg_per_vial')}mg" for c in m.get('composition', [])])
            lines.append(f"- {m.get('product_name')} (batch {m.get('batch_id')}): {m.get('vials_remaining')} fiale rimaste; comp: {comp}; supporta admin: {m.get('supported_admins_for_cycle')}")

    return '\n'.join(lines)


class CyclesView(ft.Container):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.expand = True
        self.padding = 20
        self.selected_tab = 0  # 0=Attivi, 1=Pianificati, 2=Completati
        self.content = self._build_content()

    def _build_content(self):
        """Build enhanced cycles dashboard with tabs, progress bars, and quick actions."""
        # Auto-complete expired cycles on load
        try:
            completed_count = self.app.manager.check_and_complete_expired_cycles()
            if completed_count > 0:
                self.app.show_snackbar(f'🔄 {completed_count} ciclo/i scaduto/i completato/i automaticamente')
        except Exception:
            pass  # Silent fail for auto-complete
        
        # Header with quick actions
        header = ft.Row([
            ft.Text("Cicli di Trattamento", size=28, weight=ft.FontWeight.BOLD),
            ft.Container(expand=True),
            ft.ElevatedButton(
                "➕ Nuovo Ciclo",
                icon=ft.Icons.ADD_CIRCLE_OUTLINE,
                on_click=self._show_start_dialog,
                bgcolor=ft.Colors.BLUE_700,
            ),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        # Tabs for different cycle statuses
        tabs = ft.Tabs(
            selected_index=self.selected_tab,
            on_change=self._on_tab_change,
            tabs=[
                ft.Tab(text="🟢 Attivi", icon=ft.Icons.PLAY_CIRCLE_OUTLINE),
                ft.Tab(text="📅 Pianificati", icon=ft.Icons.CALENDAR_TODAY),
                ft.Tab(text="✅ Completati", icon=ft.Icons.CHECK_CIRCLE_OUTLINE),
            ],
            expand=1,
        )

        # Build content based on selected tab
        tab_content = self._build_tab_content()

        # Mini calendar widget for today's cycle tasks
        today_widget = self._build_today_widget()

        return ft.Column([
            header,
            ft.Divider(height=2),
            today_widget,
            ft.Container(height=10),
            tabs,
            ft.Container(height=10),
            tab_content,
        ], scroll=ft.ScrollMode.AUTO, spacing=0)

    def _on_tab_change(self, e):
        """Handle tab selection change."""
        self.selected_tab = e.control.selected_index
        self.refresh()

    def _build_today_widget(self):
        """Build mini-calendar widget showing today's scheduled administrations."""
        try:
            today_admins = self.app.manager.get_scheduled_administrations()
            # Filter only those linked to cycles
            cycle_admins = []
            for a in today_admins:
                # Check if this admin is linked to a cycle
                admin_id = a.get('id')
                if admin_id:
                    cursor = self.app.manager.conn.cursor()
                    cursor.execute('SELECT cycle_id FROM administrations WHERE id = ?', (admin_id,))
                    row = cursor.fetchone()
                    if row and row[0]:
                        cycle_admins.append(a)

            if not cycle_admins:
                return ft.Container()

            admin_items = []
            for a in cycle_admins[:5]:  # Limit to 5
                time_str = a.get('time', '??:??')
                peptides = a.get('peptide_names', 'N/A')
                prep_id = a.get('preparation_id')
                
                admin_items.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.SCHEDULE, size=16, color=ft.Colors.BLUE_400),
                            ft.Text(time_str, size=13, weight=ft.FontWeight.BOLD),
                            ft.Text(f"- {peptides[:30]}", size=12),
                            ft.Container(expand=True),
                            ft.IconButton(
                                icon=ft.Icons.INFO_OUTLINE,
                                icon_size=16,
                                tooltip="Dettagli",
                                on_click=lambda e, pid=prep_id: self.app.show_preparation_details(pid) if pid else None,
                            ),
                        ], spacing=5),
                        padding=5,
                        border=ft.border.all(1, ft.Colors.BLUE_900),
                        border_radius=5,
                        bgcolor=ft.Colors.BLUE_900 if len(admin_items) % 2 == 0 else None,
                    )
                )

            return ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.TODAY, color=ft.Colors.BLUE_400),
                            ft.Text("Somministrazioni Ciclo Oggi", size=16, weight=ft.FontWeight.BOLD),
                            ft.Container(expand=True),
                            ft.Text(f"{len(cycle_admins)} totali", size=12, color=ft.Colors.GREY_400),
                        ]),
                        ft.Divider(height=1),
                        ft.Column(admin_items, spacing=3),
                    ], spacing=8),
                    padding=15,
                ),
                elevation=2,
            )
        except Exception as ex:
            # Silent fail - widget is optional
            return ft.Container()

    def _build_tab_content(self):
        """Build content for the currently selected tab."""
        all_cycles = self.app.manager.get_cycles(active_only=False)
        
        # Filter by status based on tab
        if self.selected_tab == 0:  # Attivi
            cycles = [c for c in all_cycles if c.get('status') == 'active']
            empty_msg = "Nessun ciclo attivo. Avviane uno nuovo!"
        elif self.selected_tab == 1:  # Pianificati
            cycles = [c for c in all_cycles if c.get('status') == 'planned']
            empty_msg = "Nessun ciclo pianificato."
        else:  # Completati
            cycles = [c for c in all_cycles if c.get('status') in ['completed', 'paused', 'abandoned']]
            empty_msg = "Nessun ciclo completato."

        if not cycles:
            return ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.INBOX, size=64, color=ft.Colors.GREY_600),
                    ft.Text(empty_msg, size=16, color=ft.Colors.GREY_500),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                alignment=ft.alignment.center,
                height=200,
            )

        # Build cycle cards with progress bars
        cards = []
        for c in cycles:
            card = self._build_cycle_card(c)
            cards.append(card)

        return ft.Column(cards, spacing=10)

    def _build_cycle_card(self, cycle: dict):
        """Build rich cycle card with progress bar, status badge, and quick actions."""
        cycle_id = cycle.get('id')
        name = cycle.get('name', f'Ciclo #{cycle_id}')
        status = cycle.get('status', 'active')
        start_date = cycle.get('start_date')
        
        # Get protocol info
        proto_name = "N/A"
        if cycle.get('protocol_id'):
            try:
                proto = self.app.manager.get_protocol_details(cycle['protocol_id'])
                proto_name = proto.get('name') if proto else "N/A"
            except Exception:
                pass

        # Calculate progress (mock for now - can be enhanced with actual administration count)
        # Progress = days_elapsed / planned_duration or administrations_done / expected
        progress = 0.0
        progress_text = "0%"
        progress_color = ft.Colors.BLUE_400
        
        try:
            if start_date:
                start = datetime.fromisoformat(start_date).date() if isinstance(start_date, str) else start_date
                today = date.today()
                days_elapsed = (today - start).days
                
                # Estimate total duration from cycle_duration_weeks
                duration_weeks = cycle.get('cycle_duration_weeks')
                
                if duration_weeks and duration_weeks > 0:
                    total_days = duration_weeks * 7
                    # Ensure progress is never negative (for future-dated cycles)
                    progress = max(0.0, min(1.0, days_elapsed / total_days))
                    progress_text = f"{int(progress * 100)}%"
                    
                    # Color based on progress (Ocean Blue gradient)
                    if progress < 0.33:
                        progress_color = ft.Colors.CYAN_400
                    elif progress < 0.66:
                        progress_color = ft.Colors.BLUE_400
                    else:
                        progress_color = ft.Colors.INDIGO_400
        except Exception:
            pass

        # Status badge
        status_colors = {
            'active': (ft.Colors.GREEN_400, "🟢 Attivo"),
            'planned': (ft.Colors.BLUE_400, "📅 Pianificato"),
            'completed': (ft.Colors.GREY_400, "✅ Completato"),
            'paused': (ft.Colors.ORANGE_400, "⏸ In Pausa"),
            'abandoned': (ft.Colors.RED_400, "❌ Abbandonato"),
        }
        status_color, status_label = status_colors.get(status, (ft.Colors.GREY_400, status))

        # Check inventory status (quick check)
        inventory_icon = ft.Icons.INVENTORY_2
        inventory_color = ft.Colors.GREEN_400
        inventory_tooltip = "Stock sufficiente"
        
        try:
            # Quick check without full suggest_doses call (expensive)
            # This is a placeholder - real implementation would cache or do lightweight check
            pass
        except Exception:
            pass

        # Build card
        card_content = ft.Container(
            content=ft.Column([
                # Header row with name, status, and actions
                ft.Row([
                    ft.Text(name, size=18, weight=ft.FontWeight.BOLD),
                    ft.Container(expand=True),
                    ft.Container(
                        content=ft.Text(status_label, size=11, weight=ft.FontWeight.BOLD),
                        padding=ft.padding.symmetric(horizontal=8, vertical=4),
                        bgcolor=status_color,
                        border_radius=5,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.EDIT,
                        tooltip="Modifica",
                        on_click=lambda e, cid=cycle_id: self._show_edit_dialog(cid),
                    ),
                    ft.IconButton(
                        icon=ft.Icons.VISIBILITY,
                        tooltip="Dettagli",
                        on_click=lambda e, cid=cycle_id: self._show_details(cid),
                    ),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                
                ft.Divider(height=1),
                
                # Info row
                ft.Row([
                    ft.Icon(ft.Icons.SCIENCE, size=16, color=ft.Colors.GREY_400),
                    ft.Text(f"Protocollo: {proto_name}", size=13, color=ft.Colors.GREY_300),
                    ft.Container(width=20),
                    ft.Icon(ft.Icons.CALENDAR_TODAY, size=16, color=ft.Colors.GREY_400),
                    ft.Text(f"Inizio: {start_date or 'N/A'}", size=13, color=ft.Colors.GREY_300),
                    ft.Container(expand=True),
                    ft.Icon(inventory_icon, size=16, color=inventory_color, tooltip=inventory_tooltip),
                ], spacing=5),
                
                # Progress bar
                ft.Column([
                    ft.Row([
                        ft.Text("Progresso", size=11, color=ft.Colors.GREY_500),
                        ft.Container(expand=True),
                        ft.Text(progress_text, size=11, weight=ft.FontWeight.BOLD),
                        ft.Text(f" ({duration_weeks}w)", size=9, color=ft.Colors.GREY_600) if duration_weeks else ft.Container(),
                    ]),
                    ft.ProgressBar(
                        value=progress, 
                        color=progress_color, 
                        bgcolor=ft.Colors.GREY_800, 
                        height=8,
                        key=f"progress_{cycle_id}_{progress_text}"  # Force rebuild on value change
                    ),
                ], spacing=3),
                
                # Quick actions row
                ft.Row([
                    ft.ElevatedButton(
                        "▶️ Attiva" if status == 'planned' else "⏸️ Pausa" if status == 'active' else "▶️ Riprendi",
                        icon=ft.Icons.PLAY_ARROW if status == 'planned' else ft.Icons.PAUSE if status == 'active' else ft.Icons.PLAY_ARROW,
                        on_click=self._make_status_toggle_handler(cycle_id, status),
                        height=32,
                        bgcolor=ft.Colors.GREEN_700 if status == 'planned' else ft.Colors.ORANGE_700 if status == 'active' else ft.Colors.BLUE_700,
                        style=ft.ButtonStyle(
                            padding=ft.padding.symmetric(horizontal=12, vertical=4),
                        ),
                    ),
                    ft.ElevatedButton(
                        "✓ Completa" if status == 'active' else "Verifica Stock",
                        icon=ft.Icons.CHECK_CIRCLE if status == 'active' else ft.Icons.INVENTORY,
                        on_click=self._make_complete_or_stock_handler(cycle_id, status),
                        height=32,
                        bgcolor=ft.Colors.PURPLE_700 if status == 'active' else None,
                        style=ft.ButtonStyle(
                            padding=ft.padding.symmetric(horizontal=12, vertical=4),
                        ),
                    ),
                    ft.ElevatedButton(
                        "Assegna Somministrazioni",
                        icon=ft.Icons.LINK,
                        on_click=self._make_assign_handler(cycle_id),
                        height=32,
                        style=ft.ButtonStyle(
                            padding=ft.padding.symmetric(horizontal=12, vertical=4),
                        ),
                    ),
                    ft.Container(expand=True),
                    ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE,
                        icon_color=ft.Colors.RED_400,
                        tooltip="Elimina ciclo",
                        on_click=self._make_delete_handler(cycle_id),
                    ),
                ], spacing=8),
            ], spacing=8),
            padding=15,
        )

        return ft.Card(content=card_content, elevation=2)

    def _make_delete_handler(self, cycle_id: int):
        """Factory per creare handler di eliminazione con closure corretta."""
        def handler(e):
            self._delete_cycle(cycle_id)
        return handler
    
    def _make_assign_handler(self, cycle_id: int):
        """Factory per creare handler di assegnazione con closure corretta."""
        def handler(e):
            self._assign_retro(cycle_id)
        return handler
    
    def _make_status_toggle_handler(self, cycle_id: int, current_status: str):
        """Factory per creare handler di toggle status (attiva/pausa/riprendi)."""
        def handler(e):
            if current_status == 'planned':
                self._activate_cycle(cycle_id)
            elif current_status == 'active':
                self._pause_cycle(cycle_id)
            elif current_status == 'paused':
                self._resume_cycle(cycle_id)
        return handler
    
    def _make_complete_or_stock_handler(self, cycle_id: int, current_status: str):
        """Factory per creare handler di completamento o verifica stock."""
        def handler(e):
            if current_status == 'active':
                self._complete_cycle_with_confirm(cycle_id)
            else:
                self._verify_stock(cycle_id)
        return handler
    
    def _make_activate_or_stock_handler(self, cycle_id: int, status: str):
        """Factory per creare handler di attivazione/verifica stock con closure corretta."""
        def handler(e):
            if status == 'planned':
                self._activate_cycle(cycle_id)
            else:
                self._verify_stock(cycle_id)
        return handler
    
    def _delete_cycle(self, cycle_id: int):
        """Elimina un ciclo con conferma."""
        cycle = self.app.manager.get_cycle_details(cycle_id)
        if not cycle:
            return
        
        cycle_name = cycle.get('name', f'Ciclo #{cycle_id}')
        
        def on_confirm(e):
            try:
                # Prima scollega eventuali somministrazioni
                cursor = self.app.manager.conn.cursor()
                cursor.execute('UPDATE administrations SET cycle_id = NULL WHERE cycle_id = ?', (cycle_id,))
                
                # Poi elimina il ciclo
                cursor.execute('DELETE FROM cycles WHERE id = ?', (cycle_id,))
                self.app.manager.conn.commit()
                
                dialog.open = False
                self.app.page.update()
                self.refresh()
                self.app.show_snackbar(f'✅ Ciclo "{cycle_name}" eliminato')
            except Exception as ex:
                self.app.show_snackbar(f'❌ Errore eliminazione: {ex}', error=True)
        
        def on_cancel(e):
            dialog.open = False
            self.app.page.update()
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("⚠️ Conferma eliminazione"),
            content=ft.Column([
                ft.Text(f'Vuoi eliminare il ciclo "{cycle_name}"?', size=14),
                ft.Text('Le somministrazioni collegate verranno scollegate ma NON eliminate.', size=12, color=ft.Colors.GREY_400, italic=True),
            ], tight=True, spacing=8),
            actions=[
                ft.TextButton("Annulla", on_click=on_cancel),
                ft.TextButton("Elimina", on_click=on_confirm, style=ft.ButtonStyle(color=ft.Colors.RED_400)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.app.page.overlay.append(dialog)
        dialog.open = True
        self.app.page.update()

    def _activate_cycle(self, cycle_id: int):
        """Attiva un ciclo pianificato, impostando start_date a oggi se mancante."""
        try:
            cycle = self.app.manager.get_cycle_details(cycle_id)
            if not cycle:
                return
            
            # Se non ha start_date, usa oggi
            start_date = cycle.get('start_date')
            if not start_date:
                start_date = date.today().isoformat()
            
            # Aggiorna status e start_date
            cursor = self.app.manager.conn.cursor()
            cursor.execute(
                'UPDATE cycles SET status = ?, start_date = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                ('active', start_date, cycle_id)
            )
            self.app.manager.conn.commit()
            
            self.refresh()
            self.app.show_snackbar(f'✅ Ciclo #{cycle_id} attivato con inizio {start_date}')
        except Exception as ex:
            self.app.show_snackbar(f'❌ Errore attivazione: {ex}', error=True)
    
    def _pause_cycle(self, cycle_id: int):
        """Metti in pausa un ciclo attivo."""
        try:
            if self.app.manager.update_cycle_status(cycle_id, 'paused'):
                self.refresh()
                self.app.show_snackbar(f'⏸️ Ciclo #{cycle_id} messo in pausa')
            else:
                self.app.show_snackbar(f'❌ Errore cambio status', error=True)
        except Exception as ex:
            self.app.show_snackbar(f'❌ Errore: {ex}', error=True)
    
    def _resume_cycle(self, cycle_id: int):
        """Riprendi un ciclo in pausa."""
        try:
            if self.app.manager.update_cycle_status(cycle_id, 'active'):
                self.refresh()
                self.app.show_snackbar(f'▶️ Ciclo #{cycle_id} ripreso')
            else:
                self.app.show_snackbar(f'❌ Errore cambio status', error=True)
        except Exception as ex:
            self.app.show_snackbar(f'❌ Errore: {ex}', error=True)
    
    def _complete_cycle_with_confirm(self, cycle_id: int):
        """Completa un ciclo con conferma."""
        cycle = self.app.manager.get_cycle_details(cycle_id)
        if not cycle:
            return
        
        cycle_name = cycle.get('name', f'Ciclo #{cycle_id}')
        
        def on_confirm(e):
            try:
                if self.app.manager.complete_cycle(cycle_id):
                    dialog.open = False
                    self.app.page.update()
                    self.refresh()
                    self.app.show_snackbar(f'✅ Ciclo "{cycle_name}" completato!')
                else:
                    self.app.show_snackbar(f'❌ Errore completamento', error=True)
            except Exception as ex:
                self.app.show_snackbar(f'❌ Errore: {ex}', error=True)
        
        def on_cancel(e):
            dialog.open = False
            self.app.page.update()
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("✓ Conferma Completamento"),
            content=ft.Column([
                ft.Text(f'Vuoi marcare il ciclo "{cycle_name}" come completato?', size=14),
                ft.Text('La data di fine effettiva sarà impostata a oggi.', size=12, color=ft.Colors.GREY_400, italic=True),
            ], tight=True, spacing=8),
            actions=[
                ft.TextButton("Annulla", on_click=on_cancel),
                ft.ElevatedButton("Completa", icon=ft.Icons.CHECK_CIRCLE, on_click=on_confirm, bgcolor=ft.Colors.PURPLE_700),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.app.page.overlay.append(dialog)
        dialog.open = True
        self.app.page.update()

    def _verify_stock(self, cycle_id: int):
        """Quick action: verify stock for cycle."""
        try:
            report = self.app.manager.suggest_doses_from_inventory(cycle_id)

            # Build a richer dialog: per-peptide table and mixes summary
            rows = []
            per = report.get('per_peptide', {})
            for pid, info in per.items():
                planned = int(info.get('planned_mcg', 0))
                avail = int(info.get('available_mcg', 0))
                shortage = max(0, planned - avail)
                
                # Status icon
                if shortage == 0:
                    icon = ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN_400, size=16)
                elif shortage < planned * 0.3:
                    icon = ft.Icon(ft.Icons.WARNING, color=ft.Colors.ORANGE_400, size=16)
                else:
                    icon = ft.Icon(ft.Icons.ERROR, color=ft.Colors.RED_400, size=16)
                
                rows.append(ft.Container(
                    content=ft.Row([
                        icon,
                        ft.Text(str(info.get('name')), size=13, weight=ft.FontWeight.BOLD, width=120),
                        ft.Text(f"{planned} mcg", size=12, width=80),
                        ft.Text(f"{avail} mcg", size=12, width=80, color=ft.Colors.GREEN_400 if avail >= planned else ft.Colors.ORANGE_400),
                        ft.Text(f"-{shortage} mcg" if shortage > 0 else "OK", size=12, width=80, color=ft.Colors.RED_400 if shortage > 0 else ft.Colors.GREEN_400),
                    ], spacing=10),
                    padding=5,
                    border=ft.border.all(1, ft.Colors.GREY_800),
                    border_radius=5,
                ))

            # Purchase suggestions
            def on_suggest_purchase(ev=None):
                suggestions = []
                for pid, info in per.items():
                    planned = int(info.get('planned_mcg', 0))
                    avail = int(info.get('available_mcg', 0))
                    shortage = max(0, planned - avail)
                    if shortage > 0:
                        suggestions.append((info.get('name'), pid, shortage))

                if not suggestions:
                    DialogBuilder.show_info_dialog(self.app.page, 'Suggerimenti Acquisto', 
                        ft.Text('✅ Nessuna carenza rilevata! Stock sufficiente.', size=14))
                    return

                lines = [
                    ft.Text("📋 Peptidi da ordinare:", size=14, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                ]
                for name, pid, short in suggestions:
                    lines.append(ft.Row([
                        ft.Icon(ft.Icons.SHOPPING_CART, size=16, color=ft.Colors.ORANGE_400),
                        ft.Text(f"{name} (ID:{pid})", size=13, weight=ft.FontWeight.BOLD, width=150),
                        ft.Text(f"Necessari: {short} mcg", size=12, color=ft.Colors.RED_400),
                    ], spacing=5))
                
                DialogBuilder.show_info_dialog(self.app.page, 'Suggerimenti Acquisto', ft.Column(lines, spacing=5))

            content = ft.Column([
                ft.Text('📊 Verifica Stock Ciclo', size=16, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Row([
                    ft.Text('Peptide', size=12, weight=ft.FontWeight.BOLD, width=140),
                    ft.Text('Pianificato', size=12, weight=ft.FontWeight.BOLD, width=80),
                    ft.Text('Disponibile', size=12, weight=ft.FontWeight.BOLD, width=80),
                    ft.Text('Mancante', size=12, weight=ft.FontWeight.BOLD, width=80),
                ], spacing=10),
            ] + rows + [
                ft.Divider(),
                ft.Row([
                    ft.ElevatedButton('📝 Suggerisci Acquisto', on_click=on_suggest_purchase, icon=ft.Icons.SHOPPING_CART),
                    ft.Container(expand=True),
                    ft.TextButton('Chiudi', on_click=lambda e: DialogBuilder.close_dialog(self.app.page)),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ], spacing=8)

            DialogBuilder.show_info_dialog(self.app.page, f"Stock Ciclo #{cycle_id}", content)
        except Exception as ex:
            self.app.show_snackbar(f"❌ Errore verifica stock: {ex}", error=True)

    def _assign_retro(self, cycle_id: int):
        """Quick action: assign retroactive administrations to cycle."""
        try:
            admins = self.app.manager.get_administrations(days_back=180)
        except Exception:
            admins = self.app.manager.get_administrations()

        # Filter out administrations already assigned to a cycle
        admins = [a for a in admins if not a.get('cycle_id')]

        if not admins:
            DialogBuilder.show_info_dialog(self.app.page, 'Assegna Somministrazioni', 
                ft.Text('Nessuna somministrazione non assegnata trovata.', size=13))
            return

        # Time filter controls
        default_end = datetime.now()
        default_start = default_end - timedelta(days=30)
        start_field = ft.TextField(
            label='Data dal (YYYY-MM-DD)', 
            value=default_start.strftime('%Y-%m-%d'), 
            width=200, 
            text_style=ft.TextStyle(color=ft.Colors.WHITE), 
            bgcolor=ft.Colors.GREY_800,
            height=45,
        )
        end_field = ft.TextField(
            label='Data al (YYYY-MM-DD)', 
            value=default_end.strftime('%Y-%m-%d'), 
            width=200, 
            text_style=ft.TextStyle(color=ft.Colors.WHITE), 
            bgcolor=ft.Colors.GREY_800,
            height=45,
        )
        
        # Estrai opzioni per dropdown filtri
        all_preps = sorted(set([a.get('batch_product') or a.get('preparation_name') or f"prep#{a.get('preparation_id')}" 
                                for a in admins]))
        all_peptides = []
        for a in admins:
            prep_name = a.get('batch_product') or a.get('preparation_name') or ''
            # Estrai peptidi dal nome (es: "BPC+TB Blend" -> ["BPC-157", "TB500"])
            if prep_name:
                all_peptides.append(prep_name)
        all_peptides = sorted(set(all_peptides))
        
        prep_filter = ft.Dropdown(
            label='Filtra per Preparazione',
            options=[ft.dropdown.Option('Tutte')] + [ft.dropdown.Option(p) for p in all_preps],
            value='Tutte',
            width=250,
            bgcolor=ft.Colors.GREY_800,
        )
        
        peptide_filter = ft.Dropdown(
            label='Filtra per Peptide',
            options=[ft.dropdown.Option('Tutti')] + [ft.dropdown.Option(p) for p in all_peptides],
            value='Tutti',
            width=250,
            bgcolor=ft.Colors.GREY_800,
        )

        cb_map = {}
        select_all_cb = ft.Checkbox(label='Seleziona Tutti', value=False)

        def toggle_select_all(e):
            for cb in cb_map.values():
                cb.value = select_all_cb.value
            self.app.page.update()
        
        select_all_cb.on_change = toggle_select_all

        def build_checkboxes(filtered_admins):
            cb_map.clear()
            controls = []
            for a in filtered_admins:
                adm_dt = a.get('administration_datetime') or a.get('date') or ''
                prep = a.get('batch_product') or a.get('preparation_name') or f"prep#{a.get('preparation_id')}"
                proto = a.get('protocol_name') or a.get('protocol_id') or ''
                label = f"#{a.get('id')} {adm_dt} - {prep} - {proto}"
                cb = ft.Checkbox(label=label, value=False)
                cb_map[a.get('id')] = cb
                controls.append(cb)
            # Reset select_all quando si ricostruisce la lista
            select_all_cb.value = False
            return controls

        def parse_admin_dt(a):
            s = a.get('administration_datetime') or a.get('date') or ''
            if not s:
                return None
            try:
                if ' ' in s:
                    return datetime.strptime(s.split('.', 1)[0], '%Y-%m-%d %H:%M:%S')
                return datetime.strptime(s, '%Y-%m-%d')
            except Exception:
                return None

        def filter_admins(start_s: str, end_s: str, prep_filter_val: str = 'Tutte', peptide_filter_val: str = 'Tutti'):
            try:
                start_dt = datetime.strptime(start_s, '%Y-%m-%d')
            except Exception:
                start_dt = default_start
            try:
                end_dt = datetime.strptime(end_s, '%Y-%m-%d')
            except Exception:
                end_dt = default_end

            filtered = []
            for a in admins:
                # Filtro data
                adt = parse_admin_dt(a)
                if adt is not None:
                    if not (start_dt <= adt <= (end_dt + timedelta(days=1))):
                        continue
                
                # Filtro preparazione
                if prep_filter_val and prep_filter_val != 'Tutte':
                    prep_name = a.get('batch_product') or a.get('preparation_name') or f"prep#{a.get('preparation_id')}"
                    if prep_name != prep_filter_val:
                        continue
                
                # Filtro peptide (cerca nel nome preparazione)
                if peptide_filter_val and peptide_filter_val != 'Tutti':
                    prep_name = a.get('batch_product') or a.get('preparation_name') or ''
                    if peptide_filter_val.lower() not in prep_name.lower():
                        continue
                
                filtered.append(a)
            return filtered

        # Initial list
        filtered = filter_admins(start_field.value, end_field.value, prep_filter.value, peptide_filter.value)
        cb_controls = build_checkboxes(filtered)

        def do_filter(ev=None):
            new_filtered = filter_admins(start_field.value, end_field.value, prep_filter.value, peptide_filter.value)
            new_controls = build_checkboxes(new_filtered)
            content_container.content = ft.Column([
                ft.Text(f"Somministrazioni trovate: {len(new_filtered)}", size=12, color=ft.Colors.GREY_400),
                ft.Row([start_field, end_field], wrap=True), 
                ft.Row([prep_filter, peptide_filter], wrap=True),
                ft.Row([
                    ft.ElevatedButton('Filtra', on_click=do_filter, icon=ft.Icons.FILTER_ALT),
                    select_all_cb,
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(),
            ] + new_controls, scroll=ft.ScrollMode.AUTO, tight=True)
            self.app.page.update()

        def do_assign(ev=None):
            selected = [aid for aid, cb in cb_map.items() if cb.value]
            if not selected:
                self.app.show_snackbar('Nessuna somministrazione selezionata', error=True)
                return
            try:
                count = self.app.manager.assign_administrations_to_cycle(selected, cycle_id)
                
                # Calcola automaticamente start_date se il ciclo non ce l'ha
                cursor = self.app.manager.conn.cursor()
                cursor.execute('SELECT start_date, status FROM cycles WHERE id = ?', (cycle_id,))
                row = cursor.fetchone()
                if row and not row[0]:  # start_date è NULL
                    # Trova la data più vecchia tra le somministrazioni assegnate
                    cursor.execute('''
                        SELECT MIN(DATE(administration_datetime))
                        FROM administrations
                        WHERE id IN ({}) AND cycle_id = ?
                    '''.format(','.join('?' * len(selected))), selected + [cycle_id])
                    min_date = cursor.fetchone()[0]
                    if min_date:
                        cursor.execute(
                            'UPDATE cycles SET start_date = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                            (min_date, cycle_id)
                        )
                        self.app.manager.conn.commit()
                        self.app.show_snackbar(f'✅ {count} somministrazioni assegnate. Data inizio ciclo impostata: {min_date}')
                    else:
                        self.app.show_snackbar(f'✅ {count} somministrazioni assegnate al ciclo #{cycle_id}')
                else:
                    self.app.show_snackbar(f'✅ {count} somministrazioni assegnate al ciclo #{cycle_id}')
                
                DialogBuilder.close_dialog(self.app.page)
                self.refresh()
            except Exception as ex:
                self.app.show_snackbar(f'❌ Errore assegnazione: {ex}', error=True)

        content_container = ft.Container(
            content=ft.Column([
                ft.Text(f"Somministrazioni trovate: {len(filtered)}", size=12, color=ft.Colors.GREY_400),
                ft.Row([start_field, end_field], wrap=True), 
                ft.Row([prep_filter, peptide_filter], wrap=True),
                ft.Row([
                    ft.ElevatedButton('Filtra', on_click=do_filter, icon=ft.Icons.FILTER_ALT),
                    select_all_cb,
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(),
            ] + cb_controls, scroll=ft.ScrollMode.AUTO, tight=True),
            width=700,
            height=420,
        )

        dialog = ft.AlertDialog(
            title=ft.Text('Assegna Somministrazioni Retroattive'),
            content=content_container,
            actions=[
                ft.TextButton('Annulla', on_click=lambda e: DialogBuilder.close_dialog(self.app.page)),
                ft.ElevatedButton('Assegna Selezionate', icon=ft.Icons.LINK, on_click=do_assign),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        try:
            if hasattr(self.app.page, 'overlay') and dialog not in list(self.app.page.overlay):
                self.app.page.overlay.append(dialog)
        except Exception:
            pass

        self.app.page.dialog = dialog
        dialog.open = True
        self.app.page.update()

    def refresh(self):
        self.content = self._build_content()
        self.update()

    def _show_start_dialog(self, e):
        """Show improved start cycle dialog with protocol selection and dose customization."""
        protocols = self.app.manager.get_protocols(active_only=True)
        options = [(str(p['id']), f"#{p['id']} - {p['name']}") for p in protocols]

        fields = [
            Field('protocol_id', 'Protocollo Template', FieldType.DROPDOWN, required=True, options=options, width=400),
        ]

        form_controls = FormBuilder.build_fields(fields)

        def on_select_protocol(ev=None):
            """Step 2: Show dose customization dialog."""
            try:
                values = FormBuilder.get_values(form_controls)
                is_valid, err = FormBuilder.validate_required(form_controls, ['protocol_id'])
                if not is_valid:
                    self.app.show_snackbar(err, error=True)
                    return

                protocol_id = int(values['protocol_id'])
                # Chiudi dialog corrente
                dialog.open = False
                self.app.page.update()
                # Apri dialog personalizzazione
                self._show_dose_customization_dialog(protocol_id)
            except Exception as ex:
                self.app.show_snackbar(f"❌ Errore: {ex}", error=True)
        
        def on_cancel_protocol(ev=None):
            """Chiudi dialog selezione protocollo."""
            dialog.open = False
            self.app.page.update()
        
        # Build custom dialog con Annulla
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text('Seleziona Protocollo Template'),
            content=ft.Container(
                content=ft.Column(list(form_controls.values()), tight=True, spacing=10),
                width=450,
                height=200,
            ),
            actions=[
                ft.TextButton("Annulla", on_click=on_cancel_protocol),
                ft.ElevatedButton("Avanti", icon=ft.Icons.ARROW_FORWARD, on_click=on_select_protocol),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.app.page.overlay.append(dialog)
        dialog.open = True
        self.app.page.update()

    def _show_dose_customization_dialog(self, protocol_id: int):
        """Step 2: Customize peptide doses before creating cycle."""
        # Recupera protocollo e peptidi
        proto = self.app.manager.get_protocol_details(protocol_id)
        if not proto:
            self.app.show_snackbar('Protocollo non trovato', error=True)
            return
        
        # Recupera composizione peptidi
        cursor = self.app.manager.conn.cursor()
        cursor.execute('''
            SELECT pp.peptide_id, p.name, pp.target_dose_mcg
            FROM protocol_peptides pp
            JOIN peptides p ON pp.peptide_id = p.id
            WHERE pp.protocol_id = ?
            ORDER BY p.name
        ''', (protocol_id,))
        peptides = cursor.fetchall()
        
        if not peptides:
            self.app.show_snackbar('Protocollo senza peptidi configurati', error=True)
            return
        
        # Build dose input fields
        dose_fields = {}
        dose_rows = []
        
        for peptide_id, peptide_name, template_dose in peptides:
            dose_field = ft.TextField(
                label=f"{peptide_name} (mcg/giorno)",
                value=str(int(template_dose)),
                width=150,
                keyboard_type=ft.KeyboardType.NUMBER,
                hint_text=f"Template: {int(template_dose)}",
            )
            dose_fields[peptide_id] = dose_field
            
            dose_rows.append(
                ft.Row([
                    ft.Container(
                        content=ft.Text(peptide_name, size=14, weight=ft.FontWeight.BOLD),
                        width=120,
                    ),
                    ft.Container(
                        content=ft.Text(f"{int(template_dose)} mcg", size=13, color=ft.Colors.GREY_400),
                        width=100,
                    ),
                    ft.Icon(ft.Icons.ARROW_FORWARD, size=16, color=ft.Colors.GREY_600),
                    dose_field,
                ], spacing=10)
            )
        
        # Additional fields
        name_field = ft.TextField(
            label='Nome ciclo (opzionale)',
            hint_text=f'Es: {proto["name"]} - Personalizzato',
            width=400,
        )
        
        start_date_field = ft.TextField(
            label='Data inizio (opzionale)',
            hint_text='YYYY-MM-DD (lascia vuoto per pianificare)',
            width=200,
        )
        
        # Stock verification result container
        stock_result_container = ft.Container(
            content=ft.Text("Clicca 'Verifica Stock' per controllare disponibilità", size=12, italic=True, color=ft.Colors.GREY_500),
            padding=10,
            border=ft.border.all(1, ft.Colors.GREY_800),
            border_radius=5,
        )
        
        # Placeholder per dialog (sarà assegnato dopo)
        dialog_ref = {'dialog': None}
        
        def on_verify_stock(ev=None):
            """Verify stock and preparations for all peptides."""
            try:
                # Crea un ciclo temporaneo per usare suggest_doses_from_inventory
                # (lo faremo manualmente senza creare il ciclo)
                stock_rows = []
                all_ok = True
                
                cursor = self.app.manager.conn.cursor()
                for peptide_id, field in dose_fields.items():
                    try:
                        dose_mcg = float(field.value)
                    except:
                        continue
                    
                    # Trova peptide name
                    cursor.execute('SELECT name FROM peptides WHERE id = ?', (peptide_id,))
                    pep_name = cursor.fetchone()[0]
                    
                    # Verifica batch disponibili (mg_per_vial * 1000 = mcg)
                    cursor.execute('''
                        SELECT SUM(bc.mg_per_vial * 1000 * b.vials_remaining) as total_mcg
                        FROM batches b
                        JOIN batch_composition bc ON b.id = bc.batch_id
                        WHERE bc.peptide_id = ? AND b.vials_remaining > 0 AND b.deleted_at IS NULL
                    ''', (peptide_id,))
                    row = cursor.fetchone()
                    total_batch_mcg = row[0] if row and row[0] else 0
                    
                    # Verifica preparazioni attive e calcola mcg disponibili
                    cursor.execute('''
                        SELECT COUNT(DISTINCT prep.id) as prep_count,
                               SUM(prep.volume_remaining_ml) as total_ml,
                               b.id as batch_id,
                               prep.volume_ml as original_volume,
                               bc.mg_per_vial
                        FROM preparations prep
                        JOIN batches b ON prep.batch_id = b.id
                        JOIN batch_composition bc ON b.id = bc.batch_id
                        WHERE bc.peptide_id = ? 
                          AND prep.status = 'active' 
                          AND prep.deleted_at IS NULL
                        GROUP BY b.id, bc.peptide_id
                    ''', (peptide_id,))
                    prep_rows = cursor.fetchall()
                    
                    prep_count = 0
                    prep_ml = 0
                    prep_mcg = 0
                    
                    for prep_row in prep_rows:
                        if prep_row and prep_row[0]:
                            prep_count += prep_row[0]
                            ml = prep_row[1] if prep_row[1] else 0
                            prep_ml += ml
                            # Calcola mcg: (mg_per_vial * 1000) / original_volume * remaining_ml
                            mg = prep_row[4] if prep_row[4] else 0
                            orig_vol = prep_row[3] if prep_row[3] else 1
                            if orig_vol > 0:
                                prep_mcg += (mg * 1000 / orig_vol) * ml
                    
                    # Status icon - considera ENTRAMBI batch e preparazioni
                    total_available_mcg = total_batch_mcg + prep_mcg
                    
                    if total_available_mcg >= dose_mcg and prep_count > 0:
                        icon = ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN_400, size=16)
                        status_text = f"✓ Batch: {int(total_batch_mcg)} mcg, Prep: {prep_count} attive ({prep_ml:.2f} ml ≈ {int(prep_mcg)} mcg)"
                        icon_color = ft.Colors.GREEN_400
                    elif total_batch_mcg > 0 and prep_count > 0:
                        icon = ft.Icon(ft.Icons.WARNING, color=ft.Colors.ORANGE_400, size=16)
                        shortage = dose_mcg - total_available_mcg
                        status_text = f"⚠ Disponibile: {int(total_available_mcg)} mcg (batch {int(total_batch_mcg)} + prep {int(prep_mcg)}), mancano {int(shortage)} mcg"
                        icon_color = ft.Colors.ORANGE_400
                        all_ok = False
                    elif total_batch_mcg > 0:
                        icon = ft.Icon(ft.Icons.INFO, color=ft.Colors.BLUE_400, size=16)
                        status_text = f"ℹ Batch OK ({int(total_batch_mcg)} mcg), ma NESSUNA preparazione ricostituita"
                        icon_color = ft.Colors.BLUE_400
                        all_ok = False
                    else:
                        icon = ft.Icon(ft.Icons.ERROR, color=ft.Colors.RED_400, size=16)
                        status_text = f"❌ STOCK INSUFFICIENTE - Batch: 0 mcg"
                        icon_color = ft.Colors.RED_400
                        all_ok = False
                    
                    stock_rows.append(
                        ft.Container(
                            content=ft.Row([
                                icon,
                                ft.Text(pep_name, size=13, weight=ft.FontWeight.BOLD, width=100),
                                ft.Text(f"{int(dose_mcg)} mcg/d", size=12, width=80),
                                ft.Text(status_text, size=11, color=icon_color),
                            ], spacing=10),
                            padding=5,
                        )
                    )
                
                if stock_rows:
                    stock_result_container.content = ft.Column(stock_rows, spacing=3, tight=True)
                else:
                    stock_result_container.content = ft.Text("Nessun peptide da verificare", size=12, color=ft.Colors.GREY_500)
                
                self.app.page.update()
            except Exception as ex:
                import traceback
                traceback.print_exc()
                stock_result_container.content = ft.Text(f"Errore verifica: {ex}", size=12, color=ft.Colors.RED_400)
                self.app.page.update()
        
        # Ramp schedule configuration - NEW FORMAT: exact doses per peptide
        ramp_entries = []  # List of (week_field, peptide_dropdown, dose_field)
        ramp_container = ft.Column([], spacing=5)
        
        # Prepare peptide options for dropdown
        peptide_options = [ft.dropdown.Option(str(p_id), p_name) for p_id, p_name, _ in peptides]
        
        def add_ramp_entry(week=None, peptide_id=None, dose_mcg=None, peptide_name=None):
            """Add a ramp schedule entry row for exact doses."""
            week_field = ft.TextField(
                label="Settimana",
                value=str(week) if week else "",
                width=100,
                text_size=13,
                keyboard_type=ft.KeyboardType.NUMBER,
            )
            peptide_dropdown = ft.Dropdown(
                label="Peptide",
                options=peptide_options,
                value=str(peptide_id) if peptide_id else None,
                width=180,
                text_size=13,
            )
            # Show peptide name in dose field hint if available
            dose_hint = f"{peptide_name}" if peptide_name else "Dose in mcg"
            dose_field = ft.TextField(
                label="Dose (mcg)",
                hint_text=dose_hint,
                value=str(int(dose_mcg)) if dose_mcg else "",
                width=120,
                text_size=13,
                keyboard_type=ft.KeyboardType.NUMBER,
                suffix_text="mcg",
            )
            
            def remove_entry(e):
                ramp_container.controls.remove(entry_row)
                ramp_entries.remove((week_field, peptide_dropdown, dose_field))
                self.app.page.update()
            
            entry_row = ft.Row([
                week_field,
                peptide_dropdown,
                dose_field,
                ft.IconButton(
                    icon=ft.Icons.DELETE,
                    icon_size=16,
                    tooltip="Rimuovi",
                    on_click=remove_entry,
                ),
            ], spacing=10)
            
            ramp_entries.append((week_field, peptide_dropdown, dose_field))
            ramp_container.controls.append(entry_row)
            self.app.page.update()
        
        def on_add_ramp(e):
            add_ramp_entry()
        
        # Suggerimenti preimpostati con dosi esatte
        def apply_ramp_preset(preset_name):
            """Apply preset ramp schedule with exact doses."""
            # Clear existing
            ramp_container.controls.clear()
            ramp_entries.clear()
            
            if preset_name == "conservative":
                # Conservativo: 4 settimane di ramp per ogni peptide
                for p_id, p_name, template_dose in peptides:
                    add_ramp_entry(1, p_id, int(template_dose * 0.25), p_name)
                    add_ramp_entry(2, p_id, int(template_dose * 0.50), p_name)
                    add_ramp_entry(3, p_id, int(template_dose * 0.75), p_name)
                    add_ramp_entry(4, p_id, int(template_dose), p_name)
            elif preset_name == "moderate":
                # Moderato: 2 settimane per ogni peptide
                for p_id, p_name, template_dose in peptides:
                    add_ramp_entry(1, p_id, int(template_dose * 0.50), p_name)
                    add_ramp_entry(2, p_id, int(template_dose), p_name)
            elif preset_name == "aggressive":
                # Aggressivo: 1 settimana per ogni peptide
                for p_id, p_name, template_dose in peptides:
                    add_ramp_entry(1, p_id, int(template_dose * 0.75), p_name)
                    add_ramp_entry(2, p_id, int(template_dose), p_name)
            
            self.app.page.update()
        
        ramp_section = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("Ramp-Up Schedule (opzionale):", size=13, weight=ft.FontWeight.BOLD),
                    ft.IconButton(
                        icon=ft.Icons.HELP_OUTLINE,
                        icon_size=16,
                        tooltip="Configura aumento graduale dose nelle prime settimane.\nI peptidi disponibili sono quelli configurati nel protocollo.",
                    ),
                ]),
                ft.Text(
                    f"Peptidi nel protocollo: {', '.join([p_name for _, p_name, _ in peptides])}",
                    size=11,
                    color=ft.Colors.BLUE_400,
                    italic=True,
                ),
                ft.Row([
                    ft.TextButton("Preset: Conservativo (4w)", on_click=lambda e: apply_ramp_preset("conservative")),
                    ft.TextButton("Moderato (2w)", on_click=lambda e: apply_ramp_preset("moderate")),
                    ft.TextButton("Aggressivo (1w)", on_click=lambda e: apply_ramp_preset("aggressive")),
                ], spacing=5),
                ramp_container,
                ft.ElevatedButton(
                    "+ Aggiungi Settimana",
                    icon=ft.Icons.ADD,
                    on_click=on_add_ramp,
                ),
            ], spacing=5),
            padding=10,
            border=ft.border.all(1, ft.Colors.GREY_800),
            border_radius=5,
        )
        
        def on_create(ev=None):
            try:
                # Raccogli dosi personalizzate
                custom_doses = {}
                for peptide_id, field in dose_fields.items():
                    try:
                        dose = float(field.value)
                        if dose <= 0:
                            raise ValueError(f"Dose per {peptide_id} deve essere > 0")
                        custom_doses[peptide_id] = dose
                    except ValueError as ve:
                        self.app.show_snackbar(f"❌ Dose non valida: {ve}", error=True)
                        return
                
                # Raccogli ramp schedule - NEW FORMAT: exact doses per peptide
                week_doses = {}  # {week: [{'peptide_id': X, 'dose_mcg': Y}, ...]}
                for week_field, peptide_dropdown, dose_field in ramp_entries:
                    try:
                        week = int(week_field.value)
                        peptide_id = int(peptide_dropdown.value) if peptide_dropdown.value else None
                        dose_mcg = float(dose_field.value)
                        
                        if week < 1 or dose_mcg < 0 or not peptide_id:
                            raise ValueError("Valori non validi")
                        
                        if week not in week_doses:
                            week_doses[week] = []
                        week_doses[week].append({
                            'peptide_id': peptide_id,
                            'dose_mcg': dose_mcg
                        })
                    except (ValueError, AttributeError):
                        self.app.show_snackbar("❌ Ramp schedule non valido", error=True)
                        return
                
                # Convert to list format
                ramp_schedule = []
                for week in sorted(week_doses.keys()):
                    ramp_schedule.append({
                        'week': week,
                        'doses': week_doses[week]
                    })
                
                name = name_field.value.strip() or None
                start_date_str = start_date_field.value.strip()
                start_date = start_date_str if start_date_str else None
                status = 'active' if start_date else 'planned'
                
                # Helper per convertire Decimal in float ricorsivamente
                def convert_decimals(obj):
                    """Convert Decimal objects to float for JSON serialization."""
                    from decimal import Decimal
                    if isinstance(obj, Decimal):
                        return float(obj)
                    elif isinstance(obj, dict):
                        return {k: convert_decimals(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [convert_decimals(item) for item in obj]
                    return obj
                
                # Crea snapshot personalizzato
                protocol_snapshot = convert_decimals(dict(proto))
                # Converti Decimal in float per JSON serialization
                custom_doses_serializable = {int(k): float(v) for k, v in custom_doses.items()}
                protocol_snapshot['custom_doses'] = custom_doses_serializable
                
                # Crea ciclo con ramp schedule (eredita days_on/off/duration dal protocollo)
                cid = self.app.manager.start_cycle(
                    protocol_id=protocol_id,
                    name=name,
                    start_date=start_date,
                    status=status,
                    days_on=proto.get('days_on'),
                    days_off=proto.get('days_off', 0),
                    cycle_duration_weeks=proto.get('cycle_duration_weeks'),
                    ramp_schedule=ramp_schedule if ramp_schedule else None,
                )
                
                # Aggiorna snapshot con dosi personalizzate
                import json
                cursor = self.app.manager.conn.cursor()
                cursor.execute(
                    'UPDATE cycles SET protocol_snapshot = ? WHERE id = ?',
                    (json.dumps(protocol_snapshot), cid)
                )
                self.app.manager.conn.commit()
                
                # Chiudi dialog manualmente
                if dialog_ref['dialog']:
                    dialog_ref['dialog'].open = False
                self.app.page.update()
                
                # Cambia tab in base allo status del ciclo creato
                if status == 'planned':
                    self.selected_tab = 1  # Pianificati
                elif status == 'active':
                    self.selected_tab = 0  # Attivi
                
                self.refresh()
                
                status_msg = "attivo" if start_date else "pianificato"
                self.app.show_snackbar(f"✓ Ciclo #{cid} {status_msg} creato con dosi personalizzate")
            except Exception as ex:
                import traceback
                traceback.print_exc()
                self.app.show_snackbar(f"❌ Errore creazione: {ex}", error=True)
        
        content = ft.Column([
            ft.Text(f"Protocollo: {proto['name']}", size=16, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            ft.Text("Personalizza dosaggi giornalieri:", size=13, color=ft.Colors.GREY_400),
            *dose_rows,
            ft.Divider(),
            ramp_section,
            ft.Divider(),
            ft.Row([
                ft.ElevatedButton(
                    "🔍 Verifica Stock & Preparazioni",
                    icon=ft.Icons.INVENTORY,
                    on_click=on_verify_stock,
                ),
            ]),
            stock_result_container,
            ft.Divider(),
            name_field,
            start_date_field,
        ], spacing=10, scroll=ft.ScrollMode.AUTO, tight=True)
        
        def on_cancel(e):
            if dialog_ref['dialog']:
                dialog_ref['dialog'].open = False
                self.app.page.update()
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Personalizza Dosi Ciclo"),
            content=ft.Container(content=content, width=700, height=600),
            actions=[
                ft.TextButton("Annulla", on_click=on_cancel),
                ft.ElevatedButton("Crea Ciclo", icon=ft.Icons.CHECK, on_click=on_create),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        # Salva riferimento per on_create
        dialog_ref['dialog'] = dialog
        
        self.app.page.overlay.append(dialog)
        dialog.open = True
        self.app.page.update()

    def _show_edit_dialog(self, cycle_id):
        """Show dialog to edit cycle details."""
        cycle = self.app.manager.get_cycle_details(cycle_id)
        if not cycle:
            self.app.show_snackbar('Ciclo non trovato', ft.Colors.RED_400)
            return

        # Form fields
        name_field = ft.TextField(
            label="Nome Ciclo",
            value=cycle.get('name', ''),
            hint_text="Es. Ciclo BPC-157 Ottobre",
            width=400,
        )
        
        description_field = ft.TextField(
            label="Descrizione (opzionale)",
            value=cycle.get('description', ''),
            multiline=True,
            min_lines=2,
            max_lines=3,
            width=400,
        )
        
        start_date_field = ft.TextField(
            label="Data Inizio",
            value=cycle.get('start_date', ''),
            hint_text="YYYY-MM-DD",
            width=180,
        )
        
        planned_end_date_field = ft.TextField(
            label="Data Fine Pianificata",
            value=cycle.get('planned_end_date', ''),
            hint_text="YYYY-MM-DD (opzionale)",
            width=180,
        )
        
        days_on_field = ft.TextField(
            label="Giorni ON",
            value=str(cycle.get('days_on', '')),
            hint_text="Es. 5",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=100,
        )
        
        days_off_field = ft.TextField(
            label="Giorni OFF",
            value=str(cycle.get('days_off', 0)),
            keyboard_type=ft.KeyboardType.NUMBER,
            width=100,
        )
        
        duration_weeks_field = ft.TextField(
            label="Durata (settimane)",
            value=str(cycle.get('cycle_duration_weeks', '')),
            hint_text="Es. 8",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=120,
        )
        
        # Status dropdown
        status_dropdown = ft.Dropdown(
            label="Stato",
            value=cycle.get('status', 'active'),
            options=[
                ft.dropdown.Option('planned', '📅 Pianificato'),
                ft.dropdown.Option('active', '🟢 Attivo'),
                ft.dropdown.Option('paused', '⏸ In Pausa'),
                ft.dropdown.Option('completed', '✅ Completato'),
                ft.dropdown.Option('cancelled', '❌ Annullato'),
            ],
            width=180,
        )
        
        # Get peptides from protocol for dropdown
        protocol_id = cycle.get('protocol_id')
        peptides = []
        peptide_options = []
        peptide_map = {}  # {id: name}
        
        if protocol_id:
            try:
                cursor = self.app.manager.conn.cursor()
                cursor.execute('''
                    SELECT pp.peptide_id, p.name
                    FROM protocol_peptides pp
                    JOIN peptides p ON pp.peptide_id = p.id
                    WHERE pp.protocol_id = ?
                    ORDER BY p.name
                ''', (protocol_id,))
                peptides = cursor.fetchall()
                peptide_options = [ft.dropdown.Option(str(p[0]), p[1]) for p in peptides]
                peptide_map = {p[0]: p[1] for p in peptides}
            except Exception:
                pass
        
        # Ramp schedule editor with dynamic rows
        ramp_schedule = cycle.get('ramp_schedule', [])
        ramp_entries = []  # List of (week_field, peptide_dropdown, dose_field)
        ramp_container = ft.Column([], spacing=5)
        
        def add_ramp_row(week=None, peptide_id=None, dose_mcg=None):
            """Add a ramp schedule entry row."""
            week_field = ft.TextField(
                label="Settimana",
                value=str(week) if week else "",
                width=100,
                text_size=13,
                keyboard_type=ft.KeyboardType.NUMBER,
            )
            
            peptide_dropdown = ft.Dropdown(
                label="Peptide",
                options=peptide_options,
                value=str(peptide_id) if peptide_id else None,
                width=180,
                text_size=13,
            )
            
            # Show peptide name in hint
            peptide_name = peptide_map.get(peptide_id, "") if peptide_id else ""
            dose_field = ft.TextField(
                label="Dose (mcg)",
                hint_text=peptide_name,
                value=str(int(dose_mcg)) if dose_mcg else "",
                width=120,
                text_size=13,
                keyboard_type=ft.KeyboardType.NUMBER,
                suffix_text="mcg",
            )
            
            def remove_entry(e):
                ramp_container.controls.remove(entry_row)
                ramp_entries.remove((week_field, peptide_dropdown, dose_field))
                self.app.page.update()
            
            entry_row = ft.Row([
                week_field,
                peptide_dropdown,
                dose_field,
                ft.IconButton(
                    icon=ft.Icons.DELETE,
                    icon_size=16,
                    tooltip="Rimuovi",
                    on_click=remove_entry,
                ),
            ], spacing=10)
            
            ramp_entries.append((week_field, peptide_dropdown, dose_field))
            ramp_container.controls.append(entry_row)
            return entry_row
        
        # Pre-populate existing ramp schedule
        if ramp_schedule:
            if ramp_schedule and 'doses' in ramp_schedule[0]:
                # New format: exact doses
                for entry in ramp_schedule:
                    week = entry.get('week')
                    for dose_entry in entry.get('doses', []):
                        pid = dose_entry.get('peptide_id')
                        dose = dose_entry.get('dose_mcg')
                        add_ramp_row(week, pid, dose)
            else:
                # Legacy format: percentages - convert to text warning
                pass
        
        def on_add_ramp(e):
            add_ramp_row()
            self.app.page.update()
        
        ramp_section = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("Ramp-Up Schedule:", weight=ft.FontWeight.BOLD, size=13),
                    ft.IconButton(
                        icon=ft.Icons.HELP_OUTLINE,
                        icon_size=16,
                        tooltip="Configura aumento graduale dose per settimana e peptide",
                    ),
                ]),
                ft.Text(
                    f"Peptidi disponibili: {', '.join([p[1] for p in peptides])}",
                    size=11,
                    color=ft.Colors.BLUE_400,
                    italic=True,
                ) if peptides else ft.Text("Nessun peptide nel protocollo", size=11, color=ft.Colors.GREY_500),
                ramp_container,
                ft.ElevatedButton(
                    "+ Aggiungi Riga",
                    icon=ft.Icons.ADD,
                    on_click=on_add_ramp,
                    height=32,
                ),
            ], spacing=8),
            padding=10,
            border=ft.border.all(1, ft.Colors.GREY_700),
            border_radius=5,
        )

        def save_changes(e):
            try:
                # Validate and prepare data
                updates = {}
                
                if name_field.value:
                    updates['name'] = name_field.value
                
                if description_field.value:
                    updates['description'] = description_field.value
                
                if start_date_field.value:
                    updates['start_date'] = start_date_field.value
                
                if planned_end_date_field.value:
                    updates['planned_end_date'] = planned_end_date_field.value
                
                if days_on_field.value:
                    updates['days_on'] = int(days_on_field.value)
                
                if days_off_field.value:
                    updates['days_off'] = int(days_off_field.value)
                
                if duration_weeks_field.value:
                    updates['cycle_duration_weeks'] = int(duration_weeks_field.value)
                
                if status_dropdown.value:
                    updates['status'] = status_dropdown.value
                
                # Parse ramp schedule from dynamic rows
                week_doses = {}  # {week: [{'peptide_id': X, 'dose_mcg': Y}, ...]}
                for week_field, peptide_dropdown, dose_field in ramp_entries:
                    try:
                        week = int(week_field.value)
                        peptide_id = int(peptide_dropdown.value) if peptide_dropdown.value else None
                        dose_mcg = float(dose_field.value)
                        
                        if week < 1 or dose_mcg < 0 or not peptide_id:
                            continue  # Skip invalid entries
                        
                        if week not in week_doses:
                            week_doses[week] = []
                        week_doses[week].append({
                            'peptide_id': peptide_id,
                            'dose_mcg': dose_mcg
                        })
                    except (ValueError, AttributeError):
                        continue  # Skip invalid entries
                
                # Convert to list format
                if week_doses:
                    parsed_ramp = []
                    for week in sorted(week_doses.keys()):
                        parsed_ramp.append({
                            'week': week,
                            'doses': week_doses[week]
                        })
                    updates['ramp_schedule'] = parsed_ramp
                else:
                    # Clear ramp schedule if no entries
                    updates['ramp_schedule'] = None
                
                # Update cycle
                success = self.app.manager.update_cycle(cycle_id, **updates)
                
                if success:
                    self.app.show_snackbar(f'✅ Ciclo "{name_field.value}" aggiornato!', ft.Colors.GREEN_400)
                    self.app.page.close(dlg)
                    self._refresh()
                else:
                    self.app.show_snackbar('Errore durante aggiornamento', ft.Colors.RED_400)
            
            except ValueError as ve:
                self.app.show_snackbar(f'Errore nei dati: {str(ve)}', ft.Colors.RED_400)
            except Exception as ex:
                self.app.show_snackbar(f'Errore: {str(ex)}', ft.Colors.RED_400)

        def cancel(e):
            self.app.page.close(dlg)

        dlg = ft.AlertDialog(
            title=ft.Text(f"✏️ Modifica Ciclo #{cycle_id}"),
            content=ft.Container(
                content=ft.Column([
                    name_field,
                    description_field,
                    ft.Row([start_date_field, planned_end_date_field], spacing=10),
                    ft.Row([days_on_field, days_off_field, duration_weeks_field], spacing=10),
                    status_dropdown,
                    ft.Divider(),
                    ramp_section,
                ], spacing=10, scroll=ft.ScrollMode.AUTO),
                width=500,
                height=600,
            ),
            actions=[
                ft.TextButton("Annulla", on_click=cancel),
                ft.ElevatedButton("💾 Salva", on_click=save_changes, bgcolor=ft.Colors.GREEN_700),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self.app.page.open(dlg)

    def _show_details(self, cycle_id):
        """Show detailed cycle information dialog."""
        details = self.app.manager.get_cycle_details(cycle_id)
        if not details:
            return

        # Build basic info
        info_lines = [
            ft.Text(f"Nome: {details.get('name')}", size=16, weight=ft.FontWeight.BOLD),
            ft.Text(f"Protocol ID: {details.get('protocol_id')}", size=13),
            ft.Text(f"Inizio: {details.get('start_date')}", size=13),
            ft.Text(f"Stato: {details.get('status')}", size=13),
        ]

        # Ramp schedule display
        ramp_schedule = details.get('ramp_schedule')
        if ramp_schedule:
            from peptide_manager.models.cycle import Cycle
            from datetime import date
            
            # Calcola settimana corrente
            cycle_obj = Cycle(
                start_date=date.fromisoformat(details['start_date']) if details.get('start_date') and isinstance(details['start_date'], str) else details.get('start_date'),
                ramp_schedule=ramp_schedule
            )
            current_week = cycle_obj.get_current_week()
            
            ramp_rows = []
            for entry in sorted(ramp_schedule, key=lambda x: x.get('week', 0)):
                week_num = entry.get('week')
                is_current = (week_num == current_week)
                
                # Check format: new (doses) or legacy (percentage)
                if 'doses' in entry:
                    # New format: show exact doses per peptide
                    for dose_entry in entry.get('doses', []):
                        peptide_id = dose_entry.get('peptide_id')
                        dose_mcg = dose_entry.get('dose_mcg')
                        
                        # Try to get peptide name
                        peptide_name = f"Peptide #{peptide_id}"
                        try:
                            peptide = self.app.manager.get_peptide_by_id(peptide_id)
                            if peptide:
                                peptide_name = peptide.get('name', peptide_name)
                        except Exception:
                            pass
                        
                        ramp_rows.append(
                            ft.Row([
                                ft.Icon(ft.Icons.ARROW_RIGHT if is_current else ft.Icons.CIRCLE, 
                                       size=12, 
                                       color=ft.Colors.GREEN_400 if is_current else ft.Colors.GREY_500),
                                ft.Text(f"Settimana {week_num} - {peptide_name}: {dose_mcg} mcg", 
                                       size=12,
                                       weight=ft.FontWeight.BOLD if is_current else ft.FontWeight.NORMAL,
                                       color=ft.Colors.GREEN_700 if is_current else ft.Colors.GREY_700),
                            ], spacing=5)
                        )
                else:
                    # Legacy format: percentage
                    percentage = entry.get('percentage')
                    ramp_rows.append(
                        ft.Row([
                            ft.Icon(ft.Icons.ARROW_RIGHT if is_current else ft.Icons.CIRCLE, 
                                   size=12, 
                                   color=ft.Colors.GREEN_400 if is_current else ft.Colors.GREY_500),
                            ft.Text(f"Settimana {week_num}: {percentage}%", 
                                   size=12,
                                   weight=ft.FontWeight.BOLD if is_current else ft.FontWeight.NORMAL,
                                   color=ft.Colors.GREEN_700 if is_current else ft.Colors.GREY_700),
                        ], spacing=5)
                    )
            
            ramp_section = ft.Container(
                content=ft.Column([
                    ft.Text('Ramp-Up Schedule:', weight=ft.FontWeight.BOLD, size=13),
                    ft.Text(f'Settimana corrente: {current_week}', size=12, color=ft.Colors.BLUE_600),
                    ft.Divider(height=1),
                    *ramp_rows,
                ], spacing=3),
                padding=10,
                border=ft.border.all(1, ft.Colors.GREY_700),
                border_radius=5,
                bgcolor=ft.Colors.GREY_900,
            )
            info_lines.append(ft.Container(height=10))  # Spacer
            info_lines.append(ramp_section)

        snapshot_block = ft.Column([
            ft.Text('Protocol snapshot:', weight=ft.FontWeight.BOLD, size=12),
            ft.Text(str(details.get('protocol_snapshot') or {})[:200] + '...', size=11, color=ft.Colors.GREY_500),
        ], tight=True)

        content = ft.Column(info_lines + [ft.Divider(), snapshot_block], tight=True)

        DialogBuilder.show_info_dialog(self.app.page, f"Dettagli Ciclo #{cycle_id}", content)
