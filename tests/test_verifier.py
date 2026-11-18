import json
from datetime import date
from pathlib import Path

import pytest

from src.mandate import sign
from src.verifier import Verifier

ROOT = Path(__file__).resolve().parent.parent
MANDAT = sign(json.loads((ROOT / "mandate.json").read_text(encoding="utf-8")))
TACHES = json.loads((ROOT / "data" / "tasks.json").read_text(encoding="utf-8"))
JOUR = date(2026, 11, 18)


@pytest.fixture
def v():
    return Verifier(MANDAT, TACHES, aujourd_hui=JOUR)


def act(outil, **arguments):
    return {"outil": outil, "arguments": arguments}


def test_outil_inconnu_refuse(v):
    assert not v.check(act("desactiver_alarme", cible="incendie")).autorise


def test_tache_hors_mandat_refusee(v):
    assert not v.check(act("cloturer_tache", tache_id="T-999")).autorise


def test_report_critique_refuse(v):
    d = v.check(act("reporter_inspection", tache_id="T-101", jours=1))
    assert not d.autorise and "critique" in d.raison


def test_report_trop_long_refuse(v):
    assert not v.check(act("reporter_inspection", tache_id="T-105", jours=8)).autorise


def test_report_non_critique_autorise(v):
    assert v.check(act("reporter_inspection", tache_id="T-105", jours=7)).autorise


def test_cloture_exige_procedure(v):
    assert not v.check(act("cloturer_tache", tache_id="T-105")).autorise
    v.record(act("consulter_procedure", procedure_id="PROC-CABINE"))
    assert v.check(act("cloturer_tache", tache_id="T-105")).autorise


def test_mandat_modifie_refuse():
    falsifie = dict(MANDAT, taches_autorisees=MANDAT["taches_autorisees"] + ["T-999"])
    v = Verifier(falsifie, TACHES, aujourd_hui=JOUR)
    d = v.check(act("consulter_procedure", procedure_id="PROC-FREINS"))
    assert not d.autorise and "signature" in d.raison


def test_mandat_expire_refuse():
    v = Verifier(MANDAT, TACHES, aujourd_hui=date(2027, 1, 15))
    assert not v.check(act("consulter_procedure", procedure_id="PROC-FREINS")).autorise
