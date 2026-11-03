import copy
import json
from abc import ABC, abstractmethod
from pathlib import Path

from deauville.erreurs import StockageError
from deauville.festival import Festival


class Stockage(ABC):
    """L'endroit où le festival est rangé ; le festival ne sait pas lequel."""

    @abstractmethod
    def charger(self) -> Festival: ...

    @abstractmethod
    def sauver(self, festival: Festival) -> None: ...


class StockageJson(Stockage):
    """Le festival dans un fichier JSON."""

    def __init__(self, chemin: str | Path) -> None:
        self.chemin = Path(chemin)

    def charger(self) -> Festival:
        try:
            with self.chemin.open(encoding="utf-8") as fichier:
                donnees = json.load(fichier)
        except FileNotFoundError:
            raise StockageError(f"{self.chemin} does not exist.") from None
        except json.JSONDecodeError as erreur:
            raise StockageError(
                f"{self.chemin} is damaged (line {erreur.lineno})."
            ) from None
        return Festival.depuis_dict(donnees)

    def sauver(self, festival: Festival) -> None:
        try:
            with self.chemin.open("w", encoding="utf-8") as fichier:
                json.dump(festival.vers_dict(), fichier, ensure_ascii=False, indent=2)
                fichier.write("\n")
        except OSError as erreur:
            raise StockageError(
                f"{self.chemin} cannot be written ({erreur.strerror})."
            ) from None


class StockageMemoire(Stockage):
    """Le festival gardé en mémoire, pour les tests."""

    def __init__(self, donnees: dict) -> None:
        self.donnees = copy.deepcopy(donnees)

    def charger(self) -> Festival:
        return Festival.depuis_dict(copy.deepcopy(self.donnees))

    def sauver(self, festival: Festival) -> None:
        self.donnees = festival.vers_dict()
