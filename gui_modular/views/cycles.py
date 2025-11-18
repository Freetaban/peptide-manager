"""CyclesView - view to manage treatment cycles (Flet GUI).

Minimal initial implementation: list cycles and show basic details. This
is a scaffold to integrate start_cycle and assignment flows.
"""
import flet as ft
from gui_modular.components.data_table import DataTable, Column, Action
from gui_modular.components.dialogs import DialogBuilder
from gui_modular.components.forms import FormBuilder, Field, FieldType
from datetime import datetime, timedelta


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
        self.content = self._build_content()

    def _build_content(self):
        cycles = self.app.manager.get_cycles(active_only=False)

        data_table = DataTable(
            columns=[
                Column('id', 'ID', width=60),
                Column('name', 'Nome', width=250),
                Column('protocol', 'Protocollo', width=200),
                Column('start_date', 'Inizio', width=120),
                Column('status', 'Stato', width=100),
            ],
            actions=[
                Action('visibility', lambda cid: self._show_details(cid), 'Dettagli'),
            ],
            app=self.app,
        )

        table_data = []
        for c in cycles:
            proto_name = None
            if c.get('protocol_id'):
                try:
                    proto = self.app.manager.get_protocol_details(c['protocol_id'])
                    proto_name = proto.get('name') if proto else None
                except Exception:
                    proto_name = None

            table_data.append({
                'id': f"#{c['id']}",
                'name': c.get('name')[:40],
                'protocol': proto_name or str(c.get('protocol_id') or ''),
                'start_date': c.get('start_date') or '',
                'status': c.get('status') or '',
                '_id': c.get('id'),
            })

        toolbar = data_table.build_toolbar('Cicli di trattamento', on_add=self._show_start_dialog)
        table = data_table.build(table_data)

        return ft.Column([
            toolbar,
            ft.Divider(),
            ft.Container(content=table, border=ft.border.all(1, ft.Colors.GREY_800), border_radius=10, padding=10),
        ], scroll=ft.ScrollMode.AUTO)

    def refresh(self):
        self.content = self._build_content()
        self.update()

    def _show_start_dialog(self, e):
        # Improved start dialog: protocol dropdown, optional name and start date
        # Debug: notify that handler was invoked (helps confirm clicks are received)
        # no debug snackbar
        protocols = self.app.manager.get_protocols(active_only=True)
        options = [(str(p['id']), f"#{p['id']} - {p['name']}") for p in protocols]

        fields = [
            Field('protocol_id', 'Protocollo', FieldType.DROPDOWN, required=True, options=options, width=400),
            Field('start_date', 'Data inizio', FieldType.DATE, value=datetime.now().strftime('%Y-%m-%d'), width=200),
            Field('name', 'Nome ciclo (opzionale)', FieldType.TEXT, required=False, width=400),
        ]

        form_controls = FormBuilder.build_fields(fields)

        def on_submit(ev=None):
            values = FormBuilder.get_values(form_controls)
            is_valid, err = FormBuilder.validate_required(form_controls, ['protocol_id'])
            if not is_valid:
                self.app.show_snackbar(err, error=True)
                return

            try:
                protocol_id = int(values['protocol_id'])
                name = values.get('name') or None
                # Optional: parse start_date but repository will set start if omitted
                start_date = values.get('start_date') or None
                cid = self.app.manager.start_cycle(protocol_id=protocol_id, name=name, start_date=start_date)
                DialogBuilder.close_dialog(self.app.page)
                self.refresh()
                self.app.show_snackbar(f"✓ Ciclo #{cid} creato")
            except Exception as ex:
                self.app.show_snackbar(f"❌ Errore: {ex}", error=True)

        DialogBuilder.show_form_dialog(
            self.app.page,
            'Avvia nuovo ciclo',
            list(form_controls.values()),
            on_submit,
            height=360,
        )

    def _show_details(self, cycle_id):
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

        snapshot_block = ft.Column([
            ft.Text('Protocol snapshot:', weight=ft.FontWeight.BOLD),
            ft.Text(str(details.get('protocol_snapshot') or {}), size=12),
        ], tight=True)

        # Button to verify stock
        def on_verify_stock(e=None):
            try:
                report = self.app.manager.suggest_doses_from_inventory(cycle_id)

                # Build a richer dialog: per-peptide table and mixes summary
                rows = []
                per = report.get('per_peptide', {})
                for pid, info in per.items():
                    planned = int(info.get('planned_mcg', 0))
                    avail = int(info.get('available_mcg', 0))
                    shortage = max(0, planned - avail)
                    mix_flag = 'Sì' if info.get('mix_dependencies') else 'No'
                    rows.append(ft.Row([
                        ft.Text(str(info.get('name'))),
                        ft.Text(str(pid)),
                        ft.Text(str(planned)),
                        ft.Text(str(avail)),
                        ft.Text(str(shortage)),
                        ft.Text(mix_flag),
                    ], alignment='spaceBetween'))

                mix_lines = []
                for m in report.get('mixes', []):
                    comp = ', '.join([f"{c['peptide_id']}:{c.get('mg_per_vial')}mg" for c in m.get('composition', [])])
                    mix_lines.append(ft.Text(f"{m.get('product_name')} (batch {m.get('batch_id')}): {m.get('vials_remaining')} fiale; comp: {comp}; supporta admin: {m.get('supported_admins_for_cycle')}"))

                content = ft.Column([
                    ft.Text('Riepilogo disponibilità', weight=ft.FontWeight.BOLD),
                    ft.Row([ft.Text('Peptide'), ft.Text('ID'), ft.Text('Pianificato (mcg)'), ft.Text('Disponibile (mcg)'), ft.Text('Mancante (mcg)'), ft.Text('Mix?')], alignment='spaceBetween'),
                ] + rows + [ft.Divider(), ft.Text('Mix rilevati', weight=ft.FontWeight.BOLD)] + mix_lines)

                def on_suggest_purchase(ev=None):
                    # Build purchase suggestion: peptides with shortage > 0
                    suggestions = []
                    for pid, info in per.items():
                        planned = int(info.get('planned_mcg', 0))
                        avail = int(info.get('available_mcg', 0))
                        shortage = max(0, planned - avail)
                        if shortage > 0:
                            suggestions.append((info.get('name'), pid, shortage))

                    if not suggestions:
                        DialogBuilder.show_info_dialog(self.app.page, 'Suggerimenti acquisto', ft.Text('Nessuna carenza rilevata', size=12))
                        return

                    lines = [ft.Text(f"- {name} (id={pid}): necessita {short} mcg") for name, pid, short in suggestions]
                    DialogBuilder.show_info_dialog(self.app.page, 'Suggerimenti acquisto', ft.Column(lines))

                actions_row = ft.Row([ft.ElevatedButton('Suggerisci acquisto', on_click=on_suggest_purchase), ft.ElevatedButton('Chiudi', on_click=lambda e: DialogBuilder.close_dialog(self.app.page))])

                DialogBuilder.show_info_dialog(self.app.page, f"Verifica Stock Ciclo #{cycle_id}", ft.Column([content, ft.Divider(), actions_row]))
            except Exception as ex:
                self.app.show_snackbar(f"❌ Errore verifica stock: {ex}", error=True)

        verify_btn = ft.ElevatedButton('Verifica Stock', on_click=on_verify_stock)

        def on_assign_retro(e=None):
            # Show a selectable list of existing administrations to assign to this cycle
            try:
                admins = self.app.manager.get_administrations(days_back=180)
            except Exception:
                admins = self.app.manager.get_administrations()

            # Filter out administrations already assigned to a cycle
            admins = [a for a in admins if not a.get('cycle_id')]

            if not admins:
                DialogBuilder.show_info_dialog(self.app.page, 'Assegna somministrazioni', ft.Text('Nessuna somministrazione trovata'))
                return

            # Time filter controls
            default_end = datetime.now()
            default_start = default_end - timedelta(days=30)
            start_field = ft.TextField(label='Data dal (YYYY-MM-DD)', value=default_start.strftime('%Y-%m-%d'), width=200, text_style=ft.TextStyle(color=ft.Colors.WHITE), bgcolor=ft.Colors.GREY_800)
            end_field = ft.TextField(label='Data al (YYYY-MM-DD)', value=default_end.strftime('%Y-%m-%d'), width=200, text_style=ft.TextStyle(color=ft.Colors.WHITE), bgcolor=ft.Colors.GREY_800)

            cb_map = {}

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

            def filter_admins(start_s: str, end_s: str):
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
                    adt = parse_admin_dt(a)
                    if adt is None:
                        # include if date not parsable
                        filtered.append(a)
                    else:
                        if start_dt <= adt <= (end_dt + timedelta(days=1)):
                            filtered.append(a)
                return filtered

            # Initial list
            filtered = filter_admins(start_field.value, end_field.value)
            cb_controls = build_checkboxes(filtered)

            def do_filter(ev=None):
                new_filtered = filter_admins(start_field.value, end_field.value)
                new_controls = build_checkboxes(new_filtered)
                content_container.content = ft.Column([ft.Row([start_field, end_field, ft.ElevatedButton('Filtra', on_click=do_filter)]), ft.Divider()] + new_controls, scroll=ft.ScrollMode.AUTO, tight=True)
                self.app.page.update()

            def do_assign(ev=None):
                selected = [aid for aid, cb in cb_map.items() if cb.value]
                if not selected:
                    self.app.show_snackbar('Nessuna somministrazione selezionata', error=True)
                    return
                try:
                    count = self.app.manager.assign_administrations_to_cycle(selected, cycle_id)
                    DialogBuilder.close_dialog(self.app.page)
                    self.refresh()
                    self.app.show_snackbar(f'✓ {count} somministrazioni assegnate al ciclo #{cycle_id}')
                except Exception as ex:
                    self.app.show_snackbar(f'❌ Errore assegnazione: {ex}', error=True)

            content_container = ft.Container(
                content=ft.Column([ft.Row([start_field, end_field, ft.ElevatedButton('Filtra', on_click=do_filter)]), ft.Divider()] + cb_controls, scroll=ft.ScrollMode.AUTO, tight=True),
                width=700,
                height=420,
            )

            dialog = ft.AlertDialog(
                title=ft.Text('Assegna somministrazioni retroattive'),
                content=content_container,
                actions=[
                    ft.TextButton('Annulla', on_click=lambda e: DialogBuilder.close_dialog(self.app.page)),
                    ft.ElevatedButton('Assegna', on_click=do_assign),
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

        assign_btn = ft.ElevatedButton('Assegna Somministrazioni Retroattive', on_click=on_assign_retro)

        content = ft.Column(info_lines + [ft.Divider(), snapshot_block, ft.Row([verify_btn, assign_btn], spacing=10)], tight=True)

        DialogBuilder.show_info_dialog(self.app.page, f"Ciclo #{cycle_id}", content)
