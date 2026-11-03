class FestivalError(Exception):
    """Toute erreur du festival : le message dit quelle règle est cassée."""


class IntrouvableError(FestivalError):
    """Un lieu, un artiste ou un spectacle qui n'existe pas."""


class ConflitError(FestivalError):
    """Une demande valide qui heurte le programme existant."""


class InvalideError(FestivalError):
    """Une valeur qui ne respecte pas les règles."""


class StockageError(FestivalError):
    """Le fichier de données ne peut pas être lu ou écrit."""
