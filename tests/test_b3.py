from datetime import date, datetime

import pytest

from b3_festival import Festival, Spectacle, charger_festival, creer_spectacle


@pytest.fixture
def festival() -> Festival:
    return charger_festival()


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
    return creer_spectacle(festival, donnees)


def test_un_spectacle_libre_est_ajoute(festival):
    festival.ajouter(solo(festival))
    assert festival.trouver_spectacle("la-cabane-2027-06-13-0800") is not None


def test_salle_occupee(festival):
    nouveau = solo(festival, venue="le-kiosque", start="2027-06-12T02:15")
    with pytest.raises(ValueError, match="Le Kiosque is busy with After Hours"):
        festival.ajouter(nouveau)


def test_artiste_occupe_dans_une_autre_salle(festival):
    nouveau = solo(festival, artist="max-pellerin", start="2027-06-11T23:00")
    with pytest.raises(ValueError, match="Max Pellerin is on stage in Late Laughs"):
        festival.ajouter(nouveau)


def test_artiste_occupe_comme_numero_d_un_plateau(festival):
    nouveau = solo(festival, artist="hugo-lemaire", start="2027-06-12T01:30")
    with pytest.raises(ValueError, match="Hugo Lemaire is on stage in After Hours"):
        festival.ajouter(nouveau)


def test_un_spectacle_a_une_heure_appartient_a_la_veille(festival):
    after_hours = festival.trouver_spectacle("le-kiosque-2027-06-12-0100")
    assert after_hours.jour_festival == date(2027, 6, 11)
    assert after_hours in festival.programme(date(2027, 6, 11))


def test_jour_hors_du_festival(festival):
    with pytest.raises(ValueError, match="2027-06-14 is not a day of the festival"):
        festival.ajouter(solo(festival, start="2027-06-14T08:00"))


def test_duree_de_0_minute(festival):
    with pytest.raises(ValueError, match="1 to 360"):
        solo(festival, duration_minutes=0)


def test_duree_de_361_minutes(festival):
    with pytest.raises(ValueError, match="1 to 360"):
        solo(festival, duration_minutes=361)


def test_salle_inconnue(festival):
    with pytest.raises(ValueError, match="No venue 'nowhere'"):
        solo(festival, venue="nowhere")


def test_artiste_inconnu(festival):
    with pytest.raises(ValueError, match="No artist 'nobody'"):
        solo(festival, artist="nobody")


def test_en_scene_et_a_venir(festival):
    moment = datetime(2027, 6, 11, 21, 0)
    assert [s.titre for s in festival.en_scene(moment)] == ["Tall Tales"]
    suivants = [s.titre for s in festival.a_venir(moment)]
    assert suivants == ["Straight Face", "Late Laughs", "After Hours"]
