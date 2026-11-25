import os

import requests
from graphql import GraphQLError

MOVIE_URL = os.environ.get("MOVIE_GRAPHQL_URL", "http://localhost:3200/graphql")

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
