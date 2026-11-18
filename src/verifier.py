"""Vérificateur d'actions : contrôle chaque action proposée par l'agent AVANT exécution.

Principe : le vérificateur ne fait pas confiance au LLM. Il ne regarde que
l'action proposée, l'état de la session et le mandat signé. Une action qui sort
du mandat est refusée, même si l'agent a été piégé par une injection de prompt.
"""
from dataclasses import dataclass, field
from datetime import date

from . import mandate as mandate_mod


@dataclass
class Decision:
    autorise: bool
    raison: str


@dataclass
class Verifier:
    mandat: dict
    taches: dict
    aujourd_hui: date = field(default_factory=date.today)
    procedures_consultees: set = field(default_factory=set)

    def __post_init__(self):
        self.mandat_valide = mandate_mod.is_valid(self.mandat)

    def check(self, action: dict) -> Decision:
        outil = action.get("outil")
        args = action.get("arguments", {}) or {}
        m = self.mandat

        if not self.mandat_valide:
            return Decision(False, "signature du mandat invalide")
        if not (date.fromisoformat(m["valide_du"]) <= self.aujourd_hui <= date.fromisoformat(m["valide_jusqu_au"])):
            return Decision(False, "mandat hors de sa période de validité")
        if outil not in m["outils_autorises"]:
            return Decision(False, f"outil '{outil}' non autorisé par le mandat")

        if outil == "consulter_procedure":
            return Decision(True, "consultation autorisée")

        tache_id = args.get("tache_id")
        if tache_id not in m["taches_autorisees"]:
            return Decision(False, f"tâche {tache_id} hors du mandat")
        tache = self.taches.get(tache_id)
        if tache is None:
            return Decision(False, f"tâche {tache_id} inconnue")
        critique = tache["categorie"] in m["categories_critiques"]

        if outil == "reporter_inspection":
            regle = m["regles"]["reporter_inspection"]
            if critique and regle["interdit_si_categorie_critique"]:
                return Decision(False, f"report interdit : catégorie critique ({tache['categorie']})")
            jours = args.get("jours")
            if not isinstance(jours, int) or jours <= 0 or jours > regle["jours_max"]:
                return Decision(False, f"report de {jours} jours hors limite ({regle['jours_max']} max)")
            return Decision(True, "report autorisé")

        if outil == "cloturer_tache":
            if m["regles"]["cloturer_tache"]["exige_procedure_consultee"] \
                    and tache["procedure"] not in self.procedures_consultees:
                return Decision(False, f"procédure {tache['procedure']} non consultée avant clôture")
            return Decision(True, "clôture autorisée")

        return Decision(False, "action non prévue")

    def record(self, action: dict) -> None:
        """Met à jour l'état de session après une action autorisée et exécutée."""
        if action.get("outil") == "consulter_procedure":
            self.procedures_consultees.add(action["arguments"].get("procedure_id"))
