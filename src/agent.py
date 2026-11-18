"""Boucle de l'agent : recherche -> LLM -> (vérificateur) -> exécution des outils."""
import copy
import json
import time
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from .llm import get_llm
from .mandate import load_signed
from .retriever import Retriever, load_corpus
from .verifier import Verifier

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@dataclass
class StepResult:
    reponse: str
    actions_proposees: list
    actions_executees: list = field(default_factory=list)
    actions_refusees: list = field(default_factory=list)
    latence_llm_s: float = 0.0
    latence_verif_s: float = 0.0


class MaintenanceAgent:
    def __init__(self, backend: str = "mock", with_guard: bool = True, include_poisoned: bool = True,
                 today: date | None = None):
        self.llm = get_llm(backend)
        self.retriever = Retriever(load_corpus(include_poisoned))
        self.with_guard = with_guard
        self.taches = json.loads((DATA_DIR / "tasks.json").read_text(encoding="utf-8"))
        self.verifier = Verifier(load_signed(), copy.deepcopy(self.taches), aujourd_hui=today or date.today())

    def execute(self, action: dict) -> None:
        outil, args = action.get("outil"), action.get("arguments", {})
        if outil == "cloturer_tache" and args.get("tache_id") in self.taches:
            self.taches[args["tache_id"]]["statut"] = "close"
        elif outil == "reporter_inspection" and args.get("tache_id") in self.taches:
            self.taches[args["tache_id"]]["statut"] = f"reportée de {args.get('jours')} jours"

    def run(self, message: str) -> StepResult:
        docs = self.retriever.search(message, k=3)
        out, llm_time = self.llm.generate(message, docs)
        result = StepResult(out.get("reponse", ""), out.get("actions", []), latence_llm_s=llm_time)
        for action in result.actions_proposees:
            if self.with_guard:
                t0 = time.perf_counter()
                decision = self.verifier.check(action)
                result.latence_verif_s += time.perf_counter() - t0
                if not decision.autorise:
                    result.actions_refusees.append({**action, "raison": decision.raison})
                    continue
            self.verifier.record(action)
            self.execute(action)
            result.actions_executees.append(action)
        return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Assistant de maintenance avec vérificateur de mandat")
    parser.add_argument("message")
    parser.add_argument("--backend", default="mock", choices=["mock", "api"])
    parser.add_argument("--sans-verificateur", action="store_true")
    a = parser.parse_args()
    agent = MaintenanceAgent(a.backend, with_guard=not a.sans_verificateur)
    r = agent.run(a.message)
    print("Réponse :", r.reponse)
    print("Actions exécutées :", json.dumps(r.actions_executees, ensure_ascii=False))
    print("Actions refusées  :", json.dumps(r.actions_refusees, ensure_ascii=False))
