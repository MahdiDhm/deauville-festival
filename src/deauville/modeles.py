import unicodedata
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Self

from deauville.erreurs import ConflitError, InvalideError

ECART = timedelta(minutes=30)
FIN_DE_NUIT = timedelta(hours=6)


def fabriquer_code(texte: str) -> str:
    """'Théâtre des Planches' → 'theatre-des-planches'."""
    texte = unicodedata.normalize("NFKD", texte)
    texte = texte.encode("ascii", "ignore").decode("ascii").lower()
    propre = ""
    for caractere in texte:
        if caractere.isalnum():
            propre += caractere
        else:
            propre += " "
    return "-".join(propre.split())


def lire_jour(texte: str) -> date:
    try:
        return date.fromisoformat(texte)
    except ValueError:
        raise InvalideError(f"'{texte}' is not a day, use YYYY-MM-DD.") from None


def lire_moment(texte: str) -> datetime:
    try:
        return datetime.fromisoformat(texte)
    except ValueError:
        raise InvalideError(
            f"'{texte}' is not a moment, use YYYY-MM-DDTHH:MM."
        ) from None


def lire_entier(valeur: Any, quoi: str) -> int:
    """Un entier, ou une InvalideError qui dit ce qu'on attendait (`quoi`)."""
    try:
        return int(valeur)
    except (TypeError, ValueError):
        raise InvalideError(f"'{valeur}' is not {quoi}.") from None


def texte_moment(moment: datetime) -> str:
    return f"{moment:%Y-%m-%dT%H:%M}"


@dataclass(eq=False)
class Salle:
    """Un lieu du festival ; deux salles sont la même si elles ont le même code."""

    nom: str
    capacite: int
    adresse: str = ""

    def __post_init__(self) -> None:
        if self.capacite < 1:
            raise InvalideError(f"{self.nom} needs at least one seat.")

    @property
    def slug(self) -> str:
        return fabriquer_code(self.nom)

    def __eq__(self, autre: object) -> bool:
        return isinstance(autre, Salle) and autre.slug == self.slug

    def __hash__(self) -> int:
        return hash(self.slug)

    def vers_dict(self) -> dict:
        return {"name": self.nom, "capacity": self.capacite, "address": self.adresse}

    def vue(self) -> dict:
        return {"slug": self.slug, **self.vers_dict()}


@dataclass(eq=False)
class Artiste:
    """Un artiste ; deux artistes sont le même s'ils ont le même code."""

    nom: str
    bio: str = ""
    photo_url: str = ""

    def __post_init__(self) -> None:
        self.nom = self.nom.strip()
        if not self.slug:
            raise InvalideError("An artist needs a name.")

    @property
    def slug(self) -> str:
        return fabriquer_code(self.nom)

    def __eq__(self, autre: object) -> bool:
        return isinstance(autre, Artiste) and autre.slug == self.slug

    def __hash__(self) -> int:
        return hash(self.slug)

    def vers_dict(self) -> dict:
        return {"name": self.nom, "bio": self.bio, "photo_url": self.photo_url}

    def vue(self) -> dict:
        return {"slug": self.slug, **self.vers_dict()}


ChercherArtiste = Callable[[str], Artiste]


class Spectacle(ABC):
    """Ce que tous les spectacles partagent : un lieu, un horaire, une durée."""

    kind: str

    def __init__(
        self,
        titre: str,
        salle: Salle,
        debut: datetime,
        duree: int,
        description: str = "",
    ) -> None:
        self.titre = titre.strip()
        self.salle = salle
        self.debut = debut
        self.duree = duree
        self.description = description
        self.verifier()

    @classmethod
    @abstractmethod
    def depuis_dict(
        cls, donnees: dict, communs: dict, artiste: ChercherArtiste
    ) -> Self:
        """Construit le spectacle depuis le JSON ; `communs` est déjà lu."""

    @property
    @abstractmethod
    def artistes(self) -> list[Artiste]: ...

    @abstractmethod
    def role(self, artiste: Artiste) -> str | None: ...

    @abstractmethod
    def resume(self) -> str: ...

    @abstractmethod
    def champs(self) -> dict:
        """Les champs propres à ce genre de spectacle, comme dans le fichier."""

    @property
    def fin(self) -> datetime:
        return self.debut + timedelta(minutes=self.duree)

    @property
    def jour_festival(self) -> date:
        """La date du début moins 6 h : 01:00 le samedi compte pour le vendredi."""
        return (self.debut - FIN_DE_NUIT).date()

    @property
    def id(self) -> str:
        return f"{self.salle.slug}-{self.debut:%Y-%m-%d-%H%M}"

    @property
    def places(self) -> int:
        return self.salle.capacite

    def verifier(self) -> None:
        if not self.titre:
            raise InvalideError("A performance needs a title.")
        if not 1 <= self.duree <= 360:
            raise InvalideError(
                f"{self.duree} minutes: a performance lasts from 1 to 360 minutes."
            )

    def implique(self, artiste: Artiste) -> bool:
        return self.role(artiste) is not None

    def trop_proche(self, autre: "Spectacle") -> bool:
        """Vrai si les deux spectacles ne laissent pas 30 minutes entre eux."""
        return self.debut < autre.fin + ECART and autre.debut < self.fin + ECART

    def inscrire(self, nom: str) -> None:
        raise InvalideError(f"{self.titre} is not a workshop.")

    def vers_dict(self) -> dict:
        return {
            "kind": self.kind,
            "title": self.titre,
            "venue": self.salle.slug,
            "start": texte_moment(self.debut),
            "duration_minutes": self.duree,
            "description": self.description,
            **self.champs(),
        }

    def vue(self) -> dict:
        return {
            **self.vers_dict(),
            "id": self.id,
            "venue_name": self.salle.nom,
            "end": texte_moment(self.fin),
            "festival_day": self.jour_festival.isoformat(),
            "summary": self.resume(),
            "capacity": self.places,
            "artists": [{"slug": a.slug, "name": a.nom} for a in self.artistes],
        }

    def __lt__(self, autre: "Spectacle") -> bool:
        return (self.debut, self.salle.nom) < (autre.debut, autre.salle.nom)

    def __str__(self) -> str:
        heures = f"{self.debut:%H:%M}-{self.fin:%H:%M}"
        return f"{heures} | {self.salle.nom} | {self.titre} ({self.kind})"


class Solo(Spectacle):
    """Un artiste seul en scène, avec un âge minimum."""

    kind = "solo"

    def __init__(
        self,
        titre: str,
        salle: Salle,
        debut: datetime,
        duree: int,
        artiste: Artiste,
        age_min: int = 0,
        description: str = "",
    ) -> None:
        self.artiste = artiste
        self.age_min = age_min
        super().__init__(titre, salle, debut, duree, description)

    @classmethod
    def depuis_dict(
        cls, donnees: dict, communs: dict, artiste: ChercherArtiste
    ) -> Self:
        age = lire_entier(donnees.get("min_age", 0), "an age")
        return cls(**communs, artiste=artiste(donnees["artist"]), age_min=age)

    def verifier(self) -> None:
        super().verifier()
        if not 0 <= self.age_min <= 18:
            raise InvalideError(f"Minimum age {self.age_min}: it goes from 0 to 18.")

    @property
    def artistes(self) -> list[Artiste]:
        return [self.artiste]

    def role(self, artiste: Artiste) -> str | None:
        return "solo" if artiste == self.artiste else None

    def resume(self) -> str:
        return self.artiste.nom

    def champs(self) -> dict:
        return {"artist": self.artiste.slug, "min_age": self.age_min}


class Plateau(Spectacle):
    """Un plateau : un maître de cérémonie et au moins deux artistes."""

    kind = "lineup"

    def __init__(
        self,
        titre: str,
        salle: Salle,
        debut: datetime,
        duree: int,
        hote: Artiste,
        numeros: list[Artiste],
        description: str = "",
    ) -> None:
        self.hote = hote
        self._numeros = tuple(numeros)
        super().__init__(titre, salle, debut, duree, description)

    @classmethod
    def depuis_dict(
        cls, donnees: dict, communs: dict, artiste: ChercherArtiste
    ) -> Self:
        numeros = [artiste(slug) for slug in donnees["acts"]]
        return cls(**communs, hote=artiste(donnees["host"]), numeros=numeros)

    @property
    def numeros(self) -> tuple[Artiste, ...]:
        return self._numeros

    def verifier(self) -> None:
        super().verifier()
        n = len(self._numeros)
        if n < 2:
            raise InvalideError("A lineup needs at least two acts.")
        if len(set(self._numeros)) != n:
            raise InvalideError("Each act appears only once in a lineup.")
        if self.hote in self._numeros:
            raise InvalideError(f"{self.hote.nom} cannot be the host and an act.")
        minimum = 10 * n + 3 * (n - 1)
        if self.duree < minimum:
            raise InvalideError(f"{n} acts need at least {minimum} minutes.")

    @property
    def artistes(self) -> list[Artiste]:
        return [self.hote, *self._numeros]

    def role(self, artiste: Artiste) -> str | None:
        if artiste == self.hote:
            return "host"
        if artiste in self._numeros:
            return "act"
        return None

    def resume(self) -> str:
        noms = ", ".join(a.nom for a in self._numeros)
        return f"hosted by {self.hote.nom}, with {noms}"

    def champs(self) -> dict:
        return {"host": self.hote.slug, "acts": [a.slug for a in self._numeros]}


class Atelier(Spectacle):
    """Un atelier : un intervenant et des participants inscrits."""

    kind = "workshop"

    def __init__(
        self,
        titre: str,
        salle: Salle,
        debut: datetime,
        duree: int,
        intervenant: Artiste,
        max_participants: int,
        participants: list[str] | None = None,
        description: str = "",
    ) -> None:
        self.intervenant = intervenant
        self.max_participants = max_participants
        self._participants = tuple(participants or [])
        super().__init__(titre, salle, debut, duree, description)

    @classmethod
    def depuis_dict(
        cls, donnees: dict, communs: dict, artiste: ChercherArtiste
    ) -> Self:
        return cls(
            **communs,
            intervenant=artiste(donnees["teacher"]),
            max_participants=lire_entier(
                donnees["max_participants"], "a number of places"
            ),
            participants=list(donnees.get("participants", [])),
        )

    @property
    def participants(self) -> tuple[str, ...]:
        return self._participants

    @property
    def places(self) -> int:
        return min(self.max_participants, self.salle.capacite)

    @property
    def places_restantes(self) -> int:
        return self.places - len(self._participants)

    def verifier(self) -> None:
        super().verifier()
        if self.max_participants < 1:
            raise InvalideError("A workshop needs at least one place.")
        noms = [nom.strip().lower() for nom in self._participants]
        if len(set(noms)) != len(noms):
            raise InvalideError(f"A participant is registered twice in {self.titre}.")
        if self.places_restantes < 0:
            raise InvalideError(
                f"{self.titre} has {len(noms)} participants for {self.places} places."
            )

    def inscrire(self, nom: str) -> None:
        nom = nom.strip()
        if not nom:
            raise InvalideError("A participant needs a name.")
        if nom.lower() in (p.lower() for p in self._participants):
            raise ConflitError(f"{nom} is already registered in {self.titre}.")
        if self.places_restantes == 0:
            raise ConflitError(f"{self.titre} is full.")
        self._participants = (*self._participants, nom)

    @property
    def artistes(self) -> list[Artiste]:
        return [self.intervenant]

    def role(self, artiste: Artiste) -> str | None:
        return "teacher" if artiste == self.intervenant else None

    def resume(self) -> str:
        pris = len(self._participants)
        return f"with {self.intervenant.nom}, {pris}/{self.places} places taken"

    def champs(self) -> dict:
        return {
            "teacher": self.intervenant.slug,
            "max_participants": self.max_participants,
            "participants": list(self._participants),
        }

    def vue(self) -> dict:
        return {**super().vue(), "places_left": self.places_restantes}
