from gui_modular.views.cycles import format_stock_report


def test_format_stock_report_simple():
    report = {
        'per_peptide': {
            1: {'peptide_id': 1, 'name': 'BPC', 'planned_mcg': 5000, 'available_mcg': 25000, 'mix_dependencies': []},
            2: {'peptide_id': 2, 'name': 'TB', 'planned_mcg': 5000, 'available_mcg': 25000, 'mix_dependencies': []},
        },
        'mixes': [
            {'batch_id': 10, 'product_name': 'Mix BPC+TB', 'vials_remaining': 5, 'composition': [{'peptide_id': 1, 'mg_per_vial': 5}, {'peptide_id': 2, 'mg_per_vial': 5}], 'supported_admins_for_cycle': 5}
        ]
    }

    text = format_stock_report(report)
    assert 'Disponibilità per peptide' in text
    assert 'BPC' in text
    assert 'TB' in text
    assert 'Mix BPC+TB' in text