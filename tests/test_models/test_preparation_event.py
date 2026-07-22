"""
Test per lo storico eventi delle preparazioni.

Prima della migrazione 024 gli sprechi erano accumulati in colonne piatte
(wastage_ml totale + wastage_notes come testo libero): i singoli episodi non
avevano identita', quindi non erano ne' verificabili ne' correggibili.

Questi test verificano proprio quella proprieta': ogni spreco resta un record
distinto e correggibile, e ogni correzione riallinea il volume rimanente.
"""

import sqlite3
from datetime import date
from decimal import Decimal

import pytest

from peptide_manager.models.preparation import Preparation, PreparationRepository
from peptide_manager.models.preparation_event import PreparationEvent


@pytest.fixture
def db_connection():
    """Database in-memory con lo schema completo (status + wastage + eventi)."""
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            vials_remaining INTEGER NOT NULL DEFAULT 0,
            mg_per_vial REAL,
            deleted_at TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE preparations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id INTEGER NOT NULL,
            vials_used INTEGER NOT NULL,
            volume_ml REAL NOT NULL,
            diluent TEXT NOT NULL DEFAULT 'BAC Water',
            preparation_date DATE NOT NULL,
            expiry_date DATE,
            volume_remaining_ml REAL NOT NULL,
            storage_location TEXT,
            notes TEXT,
            status TEXT DEFAULT 'active',
            actual_depletion_date DATE,
            wastage_ml REAL,
            wastage_reason TEXT,
            wastage_notes TEXT,
            deleted_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE administrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            preparation_id INTEGER NOT NULL,
            dose_ml REAL NOT NULL,
            administration_datetime TIMESTAMP NOT NULL,
            deleted_at TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE preparation_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            preparation_id INTEGER NOT NULL,
            event_type TEXT NOT NULL DEFAULT 'wastage',
            volume_ml REAL NOT NULL,
            event_date DATE NOT NULL,
            reason TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP,
            deleted_at TIMESTAMP
        )
    ''')
    cursor.execute(
        "INSERT INTO batches (product_name, vials_remaining, mg_per_vial) "
        "VALUES ('Test Peptide', 10, 5.0)"
    )
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def repo(db_connection):
    return PreparationRepository(db_connection)


@pytest.fixture
def prep_id(repo):
    """Preparazione da 2.00 ml, attiva e intatta."""
    return repo.create(Preparation(
        batch_id=1, vials_used=1, volume_ml=Decimal('2.0'),
        preparation_date=date(2026, 1, 1),
    ))


class TestWastageEventIdentity:
    """Ogni spreco deve restare un episodio distinto e ispezionabile."""

    def test_ogni_spreco_e_un_evento_separato(self, repo, prep_id):
        # Il bug storico: due sprechi finivano sommati in wastage_ml e
        # concatenati in un unico campo di testo, perdendo i singoli episodi
        repo.record_wastage(prep_id, 0.30, 'spillage', 'prima goccia')
        repo.record_wastage(prep_id, 0.20, 'contamination', 'seconda')

        events = repo.events.get_by_preparation(prep_id)

        assert len(events) == 2
        assert [float(e.volume_ml) for e in events] == [0.30, 0.20]
        # Il motivo del primo episodio non viene sovrascritto dal secondo
        assert events[0].reason == 'spillage'
        assert events[1].reason == 'contamination'
        assert events[0].notes == 'prima goccia'

    def test_evento_ha_identita_propria(self, repo, prep_id):
        repo.record_wastage(prep_id, 0.30, 'spillage')
        event = repo.events.get_by_preparation(prep_id)[0]

        # Senza un id non e' possibile correggere un singolo episodio
        assert event.id is not None
        assert repo.events.get_by_id(event.id) is not None


class TestWastageCorrection:
    """Correggere uno spreco deve riallineare il volume, non solo il testo."""

    def test_correzione_volume_riallinea_il_rimanente(self, repo, prep_id):
        repo.record_wastage(prep_id, 0.50, 'spillage')
        assert float(repo.get_by_id(prep_id).volume_remaining_ml) == 1.50

        event_id = repo.events.get_by_preparation(prep_id)[0].id
        success, _ = repo.update_wastage_event(event_id, volume_ml=0.20)

        assert success
        # 2.00 - 0.20: i 0.30 tolti per errore tornano disponibili
        assert float(repo.get_by_id(prep_id).volume_remaining_ml) == 1.80

    def test_cancellazione_restituisce_il_volume(self, repo, prep_id):
        repo.record_wastage(prep_id, 0.50, 'spillage')
        event_id = repo.events.get_by_preparation(prep_id)[0].id

        success, _ = repo.delete_wastage_event(event_id)

        assert success
        assert float(repo.get_by_id(prep_id).volume_remaining_ml) == 2.00
        assert repo.events.get_by_preparation(prep_id) == []

    def test_correzione_non_puo_superare_il_volume_disponibile(self, repo, prep_id):
        repo.record_wastage(prep_id, 0.50, 'spillage')
        event_id = repo.events.get_by_preparation(prep_id)[0].id

        success, message = repo.update_wastage_event(event_id, volume_ml=5.0)

        assert not success
        assert 'supera' in message
        # Lo stato non deve essere stato toccato dal tentativo fallito
        assert float(repo.get_by_id(prep_id).volume_remaining_ml) == 1.50

    def test_annullare_lo_spreco_riattiva_la_preparazione(self, repo, prep_id):
        # Uno spreco che esaurisce tutto il volume chiude la preparazione...
        repo.record_wastage(prep_id, 2.00, 'contamination', 'fiala persa')
        prep = repo.get_by_id(prep_id)
        assert prep.status == 'depleted'
        assert prep.actual_depletion_date is not None

        # ...ma se era un errore di registrazione deve tornare utilizzabile
        event_id = repo.events.get_by_preparation(prep_id)[0].id
        repo.delete_wastage_event(event_id)

        prep = repo.get_by_id(prep_id)
        assert prep.status == 'active'
        assert prep.actual_depletion_date is None
        assert float(prep.volume_remaining_ml) == 2.00


class TestVolumeRecalculation:
    """Il rimanente e' derivato: volume - somministrazioni - sprechi."""

    def test_registrare_uno_spreco_scala_solo_quel_volume(self, repo, prep_id):
        repo.record_wastage(prep_id, 0.10, 'spillage')

        prep = repo.get_by_id(prep_id)

        # Il rimanente scende esattamente dello spreco registrato
        assert float(prep.volume_remaining_ml) == 1.90
        assert float(prep.wastage_ml) == 0.10

    def test_riconciliazione_esplicita_somma_sprechi_e_somministrazioni(
        self, repo, prep_id, db_connection
    ):
        # Somministrazione inserita senza scalare il rimanente: e' proprio il
        # disallineamento che recalculate_volume() esiste per riassorbire
        db_connection.execute(
            "INSERT INTO administrations (preparation_id, dose_ml, "
            "administration_datetime) VALUES (?, 0.40, '2026-01-02')",
            (prep_id,)
        )
        db_connection.commit()
        repo.record_wastage(prep_id, 0.10, 'spillage')

        repo.recalculate_volume(prep_id)

        prep = repo.get_by_id(prep_id)
        # 2.00 - 0.40 somministrati - 0.10 sprecati
        assert float(prep.volume_remaining_ml) == 1.50
        assert float(prep.wastage_ml) == 0.10

    def test_wastage_ml_resta_allineato_come_totale(self, repo, prep_id):
        repo.record_wastage(prep_id, 0.30, 'spillage')
        repo.record_wastage(prep_id, 0.20, 'spillage')

        # Molti lettori (report, GUI) usano ancora questa colonna cache
        assert float(repo.get_by_id(prep_id).wastage_ml) == 0.50

        event_id = repo.events.get_by_preparation(prep_id)[0].id
        repo.delete_wastage_event(event_id)

        assert float(repo.get_by_id(prep_id).wastage_ml) == 0.20


class TestOverAdministeredPreparations:
    """
    Regressione: le dosi registrate possono superare il volume nominale.

    Succede davvero (dosaggio impreciso delle penne da insulina: prep #55 in
    produzione aveva 2.0 ml nominali e 2.2 ml somministrati, con 0.09 ml ancora
    fisicamente presenti). Correggere uno spreco NON deve ricalcolare il volume
    in assoluto, altrimenti quel residuo reale viene azzerato.
    """

    @pytest.fixture
    def over_administered(self, repo, db_connection):
        """2.00 ml nominali, 2.20 ml somministrati, 0.09 ml reali rimasti."""
        prep_id = repo.create(Preparation(
            batch_id=1, vials_used=1, volume_ml=Decimal('2.0'),
            preparation_date=date(2026, 7, 3),
        ))
        db_connection.execute(
            "INSERT INTO administrations (preparation_id, dose_ml, "
            "administration_datetime) VALUES (?, 2.20, '2026-07-17')",
            (prep_id,)
        )
        db_connection.commit()
        repo.record_wastage(prep_id, 0.01, 'other', 'spreco registrato per errore')
        # Il volume reale rilevato dall'utente, non quello aritmetico
        db_connection.execute(
            'UPDATE preparations SET volume_remaining_ml = 0.09 WHERE id = ?',
            (prep_id,)
        )
        db_connection.commit()
        return prep_id

    def test_annullare_uno_spreco_non_azzera_il_residuo_reale(
        self, repo, over_administered
    ):
        prep_id = over_administered
        event_id = repo.events.get_by_preparation(prep_id)[0].id

        repo.delete_wastage_event(event_id)

        prep = repo.get_by_id(prep_id)
        # 0.09 reali + 0.01 che non erano mai stati persi = 0.10
        # Col ricalcolo assoluto verrebbe 2.00 - 2.20 = -0.20 -> troncato a 0
        assert float(prep.volume_remaining_ml) == 0.10
        assert prep.status == 'active'

    def test_lo_scostamento_preesistente_viene_conservato(
        self, repo, over_administered
    ):
        prep_id = over_administered
        event_id = repo.events.get_by_preparation(prep_id)[0].id

        repo.update_wastage_event(event_id, volume_ml=0.05)

        # Lo spreco cresce di 0.04, quindi il rimanente cala di 0.04.
        # Lo scostamento da penna da insulina resta intatto, non riassorbito.
        assert float(repo.get_by_id(prep_id).volume_remaining_ml) == 0.05

    def test_riconciliazione_esplicita_riassorbe_lo_scostamento(
        self, repo, over_administered
    ):
        prep_id = over_administered

        # recalculate_volume e' l'operazione esplicita di riconciliazione:
        # li' il ricalcolo assoluto e' voluto
        repo.recalculate_volume(prep_id)

        prep = repo.get_by_id(prep_id)
        assert float(prep.volume_remaining_ml) == 0.0
        assert prep.status == 'depleted'


class TestPreparationEventModel:
    """Validazioni del modello."""

    def test_volume_deve_essere_positivo(self):
        with pytest.raises(ValueError):
            PreparationEvent(preparation_id=1, volume_ml=Decimal('0'))

    def test_reason_deve_essere_valido(self):
        with pytest.raises(ValueError, match='Reason'):
            PreparationEvent(preparation_id=1, volume_ml=Decimal('1'),
                             reason='motivo_inventato')

    def test_event_type_deve_essere_valido(self):
        with pytest.raises(ValueError, match='Event type'):
            PreparationEvent(preparation_id=1, volume_ml=Decimal('1'),
                             event_type='qualcosa')
