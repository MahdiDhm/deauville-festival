import json
from datetime import date, datetime
from pathlib import Path

import pytest

from deauville.erreurs import ConflitError, IntrouvableError, InvalideError
from deauville.festival import Festival
from deauville.modeles import Artiste, Atelier, Plateau, Spectacle
from deauville.stockage import StockageMemoire

DONNEES = Path(__file__).parent.parent / "data" / "festival.json"


@pytest.fixture
def donnees() -> dict:
    return json.loads(DONNEES.read_text(encoding="utf-8"))


@pytest.fixture
def festival(donnees: dict) -> Festival:
    return StockageMemoire(donnees).charger()


def solo(festival: Festival, **changements) -> Spectacle:
    donnees = {
        "kind": "solo",
        "title": "Test",
        "artist": "karim-benali",
        "venue": "la-cabane",
        "start": "2027-06-13T08:00",
        "duration_minutes": 30,
    }
    donnees.update(changements)
    return festival.creer_spectacle(donnees)


def plateau(festival: Festival, actes: list[str], duree: int) -> Spectacle:
    return festival.creer_spectacle(
        {
            "kind": "lineup",
            "title": "Test",
            "venue": "la-cabane",
            "start": "2027-06-13T08:00",
            "duration_minutes": duree,
            "host": "tom-vasseur",
            "acts": actes,
        }
    )


def atelier(festival: Festival, salle: str, places: int) -> Atelier:
    return Atelier(
        "Test",
        festival.salle(salle),
        datetime(2027, 6, 13, 8, 0),
        60,
        festival.artiste("paul-kerbrat"),
        places,
    )


# ===== Step 08 : les règles du programme =====


def test_un_spectacle_libre_est_ajoute(festival):
    festival.ajouter(solo(festival))
    assert festival.spectacle("la-cabane-2027-06-13-0800").titre == "Test"


def test_salle_occupee(festival):
    nouveau = solo(festival, venue="le-kiosque", start="2027-06-12T02:15")
    with pytest.raises(ConflitError, match="Le Kiosque is busy with After Hours"):
        festival.ajouter(nouveau)


def test_artiste_occupe_dans_une_autre_salle(festival):
    nouveau = solo(festival, artist="max-pellerin", start="2027-06-11T23:00")
    with pytest.raises(ConflitError, match="Max Pellerin is on stage in Late Laughs"):
        festival.ajouter(nouveau)


def test_artiste_occupe_comme_numero_d_un_plateau(festival):
    nouveau = solo(festival, artist="hugo-lemaire", start="2027-06-12T01:30")
    with pytest.raises(ConflitError, match="Hugo Lemaire is on stage in After Hours"):
        festival.ajouter(nouveau)


def test_un_spectacle_a_une_heure_appartient_a_la_veille(festival):
    after_hours = festival.spectacle("le-kiosque-2027-06-12-0100")
    assert after_hours.jour_festival == date(2027, 6, 11)
    assert after_hours in festival.programme(date(2027, 6, 11))


def test_jour_hors_du_festival(festival):
    with pytest.raises(InvalideError, match="2027-06-14 is not a day"):
        festival.ajouter(solo(festival, start="2027-06-14T08:00"))


@pytest.mark.parametrize("duree", [0, 361])
def test_duree_hors_limites(festival, duree):
    with pytest.raises(InvalideError, match="1 to 360"):
        solo(festival, duration_minutes=duree)


def test_salle_inconnue(festival):
    with pytest.raises(IntrouvableError, match="No venue 'nowhere'"):
        solo(festival, venue="nowhere")


def test_artiste_inconnu(festival):
    with pytest.raises(IntrouvableError, match="No artist 'nobody'"):
        solo(festival, artist="nobody")


def test_en_scene_et_a_venir(festival):
    moment = datetime(2027, 6, 11, 21, 0)
    assert [s.titre for s in festival.en_scene(moment)] == ["Tall Tales"]
    suivants = [s.titre for s in festival.a_venir(moment)]
    assert suivants == ["Straight Face", "Late Laughs", "After Hours"]


# ===== Step 09 : les trois genres =====


def test_on_ne_cree_pas_un_spectacle_abstrait(festival):
    with pytest.raises(TypeError):
        Spectacle("X", festival.salle("la-cabane"), datetime(2027, 6, 13, 8), 30)


def test_resumes(festival):
    plateau = festival.spectacle("le-kiosque-2027-06-12-0100")
    assert plateau.resume() == "hosted by Tom Vasseur, with Hugo Lemaire, Maya Choukri"
    atelier = festival.spectacle("la-cabane-2027-06-11-1030")
    assert atelier.resume() == "with Inès Moreau, 3/12 places taken"
    solo = festival.spectacle("grand-casino-2027-06-11-2030")
    assert solo.resume() == "Léa Fontaine"


def test_age_minimum_de_0_a_18(festival):
    with pytest.raises(InvalideError, match="0 to 18"):
        solo(festival, min_age=19)


def test_plateau_avec_un_seul_numero(festival):
    with pytest.raises(InvalideError, match="at least two acts"):
        plateau(festival, ["nora-lebrun"], 60)


def test_plateau_avec_un_numero_en_double(festival):
    with pytest.raises(InvalideError, match="only once"):
        plateau(festival, ["nora-lebrun", "nora-lebrun"], 60)


def test_l_hote_n_est_pas_un_numero(festival):
    with pytest.raises(InvalideError, match="host and an act"):
        plateau(festival, ["tom-vasseur", "nora-lebrun"], 60)


def test_trois_numeros_demandent_36_minutes(festival):
    actes = ["nora-lebrun", "lea-fontaine", "jeanne-aubry"]
    with pytest.raises(InvalideError, match="36 minutes"):
        plateau(festival, actes, 35)
    assert plateau(festival, actes, 36).duree == 36


def test_atelier_limite_par_la_salle(festival):
    assert atelier(festival, "grand-casino", 999).places == 650


def test_atelier_sans_place(festival):
    with pytest.raises(InvalideError, match="at least one place"):
        atelier(festival, "la-cabane", 0)


# ===== Step 10 : à travers le festival, rien ne passe sans les règles =====


def test_inscriptions_d_un_atelier(festival):
    petit = festival.ajouter(atelier(festival, "la-cabane", 1))
    festival.inscrire(petit.id, "Lou")
    with pytest.raises(ConflitError, match="already registered"):
        festival.inscrire(petit.id, "lou")
    with pytest.raises(ConflitError, match="full"):
        festival.inscrire(petit.id, "Zoé")


def test_on_n_inscrit_pas_a_un_plateau(festival):
    with pytest.raises(InvalideError, match="not a workshop"):
        festival.inscrire("le-kiosque-2027-06-12-0100", "Lou")


def test_un_deplacement_change_l_id(festival):
    deplace = solo(
        festival, artist="nora-lebrun", venue="le-kiosque", start="2027-06-13T12:00"
    )
    festival.remplacer("theatre-des-planches-2027-06-11-1800", deplace)
    assert festival.spectacle("le-kiosque-2027-06-13-1200").titre == "Test"
    with pytest.raises(IntrouvableError):
        festival.spectacle("theatre-des-planches-2027-06-11-1800")


def test_un_deplacement_refuse_ne_change_rien(festival):
    avant = [s.id for s in festival.spectacles]
    deplace = solo(
        festival, artist="nora-lebrun", venue="le-kiosque", start="2027-06-13T15:00"
    )
    with pytest.raises(ConflitError):
        festival.remplacer("theatre-des-planches-2027-06-11-1800", deplace)
    assert [s.id for s in festival.spectacles] == avant


def test_artiste_en_double(festival):
    festival.ajouter_artiste(Artiste("Zoé Tanguy"))
    with pytest.raises(ConflitError, match="Zoé Tanguy already exists"):
        festival.ajouter_artiste(Artiste("zoe tanguy"))


def test_les_collections_ne_se_modifient_pas_de_l_exterieur(festival):
    assert isinstance(festival.spectacles, tuple)
    assert isinstance(festival.artistes, tuple)
    after_hours = festival.spectacle("le-kiosque-2027-06-12-0100")
    assert isinstance(after_hours, Plateau)
    assert isinstance(after_hours.numeros, tuple)


# ===== Step 11 : le stockage est une pièce qu'on peut changer =====


def test_sauver_puis_recharger(donnees):
    stockage = StockageMemoire(donnees)
    festival = stockage.charger()
    festival.ajouter(solo(festival))
    stockage.sauver(festival)
    assert len(stockage.charger().spectacles) == 24
