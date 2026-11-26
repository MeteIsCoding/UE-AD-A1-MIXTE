import json
import os
from pathlib import Path
from threading import Lock

import requests
from graphql import GraphQLError

MOVIE_URL = os.environ.get("MOVIE_GRAPHQL_URL", "http://localhost:3200/graphql")
SCHEDULE_URL = os.environ.get("SCHEDULE_REST_URL", "http://localhost:3002/schedule")
BOOKINGS_PATH = Path(__file__).resolve().parent / "data" / "bookings.json"
bookingsLock = Lock()

MOVIE_QUERY = """
query MovieDetails($movieId: String!) {
    movie_with_id(_id: $movieId) {
        id
        title
        director
        rating
    }
}
"""


def get_movie_details(movieId):
    """Récupère les infos d'un movie via api grapql de Movie"""

    try:
        response = requests.post(
            MOVIE_URL,
            json={
                "query": MOVIE_QUERY,
                "variables": {
                    "movieId": movieId,
                },
            },
            timeout=5,
        )
        response.raise_for_status()
    except requests.RequestException as erreur:
        raise GraphQLError("erreur dans l'appel de Movie") from erreur

    try:
        responseData = response.json()
    except ValueError as erreur:
        raise GraphQLError("erreur dans la réponse de Movie") from erreur

    if responseData.get("errors"):
        raise GraphQLError("movie retourné une erreur graphQL")

    movieData = responseData["data"]
    movieDetails = movieData["movie_with_id"]

    return movieDetails


def resolve_movie_details(bookingDate, info):
    """Récupère les infos des movies d'une date"""

    movieDetails = []

    for movieId in bookingDate["movies"]:
        movieDetails.append(get_movie_details(movieId))

    return movieDetails


def load_bookings_fichier():
    """Charge les bookings depuis le fichier json"""

    with BOOKINGS_PATH.open("r", encoding="utf-8") as fichier:
        return json.load(fichier)


def save_bookings_fichier(bookingsData):
    """Remplace le fichier après avoir écrit le document complet"""

    temporaryPath = BOOKINGS_PATH.with_suffix(".tmp")

    with temporaryPath.open("w", encoding="utf-8") as fichier:
        json.dump(bookingsData, fichier, indent=2, ensure_ascii=False)
        fichier.write("\n")

    temporaryPath.replace(BOOKINGS_PATH)


def get_schedule_par_date(dateValue):
    """Récupère le schedule d'une date via l'API REST de Schedule"""

    try:
        response = requests.get(f"{SCHEDULE_URL}/{dateValue}", timeout=5)

        if response.status_code == 404:
            return None

        response.raise_for_status()
    except requests.RequestException as erreur:
        raise GraphQLError("erreur dans l'appel de Schedule") from erreur

    try:
        return response.json()
    except ValueError as erreur:
        raise GraphQLError("erreur dans la réponse de Schedule") from erreur


def booking_with_userid(_, info, _userid):
    """Retourne les bookings d'un utilisateur"""

    with bookingsLock:
        bookingsData = load_bookings_fichier()

    for bookingUser in bookingsData["bookings"]:
        if bookingUser["userid"] == _userid:
            return bookingUser

    return None


def create_booking(_, info, _userid, _date, _movieid):
    """Crée un booking après vérification auprès de Schedule et Movie"""

    if not _userid.strip():
        raise GraphQLError("userid ne peut pas être vide")

    if len(_date) != 8 or not _date.isdigit():
        raise GraphQLError("date doit être au format YYYYMMDD")

    scheduleData = get_schedule_par_date(_date)

    if scheduleData is None:
        raise GraphQLError("pas de schedule pour cette date")

    if _movieid not in scheduleData["movies"]:
        raise GraphQLError("movie n'est pas programmé pour cette date")

    if get_movie_details(_movieid) is None:
        raise GraphQLError("movie n'existe pas")

    with bookingsLock:
        bookingsData = load_bookings_fichier()
        bookingUser = None

        for booking in bookingsData["bookings"]:
            if booking["userid"] == _userid:
                bookingUser = booking
                break

        if bookingUser is None:
            bookingUser = {
                "userid": _userid,
                "dates": [],
            }
            bookingsData["bookings"].append(bookingUser)

        bookingDate = None

        for dateEntry in bookingUser["dates"]:
            if dateEntry["date"] == _date:
                bookingDate = dateEntry
                break

        if bookingDate is None:
            bookingDate = {
                "date": _date,
                "movies": [],
            }
            bookingUser["dates"].append(bookingDate)

        if _movieid in bookingDate["movies"]:
            raise GraphQLError("booking existe déjà")

        bookingDate["movies"].append(_movieid)
        save_bookings_fichier(bookingsData)

    return bookingUser


def delete_booking(_, info, _userid, _date, _movieid):
    """Supprime un booking d'un utilisateur"""

    with bookingsLock:
        bookingsData = load_bookings_fichier()

        for bookingUser in bookingsData["bookings"]:
            if bookingUser["userid"] != _userid:
                continue

            for bookingDate in bookingUser["dates"]:
                if bookingDate["date"] != _date:
                    continue

                if _movieid not in bookingDate["movies"]:
                    return False

                bookingDate["movies"].remove(_movieid)

                if not bookingDate["movies"]:
                    bookingUser["dates"].remove(bookingDate)

                if not bookingUser["dates"]:
                    bookingsData["bookings"].remove(bookingUser)

                save_bookings_fichier(bookingsData)
                return True

    return False
