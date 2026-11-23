import os
from pathlib import Path

from ariadne import (
    MutationType,
    ObjectType,
    QueryType,
    graphql_sync,
    load_schema_from_path,
    make_executable_schema,
)
from flask import Flask, jsonify, make_response, request

import resolvers as r

PORT = int(os.environ.get("MOVIE_PORT", "3200"))
HOST = "0.0.0.0"
SERVICE_DIR = Path(__file__).resolve().parent

app = Flask(__name__)
typeDefs = load_schema_from_path(str(SERVICE_DIR / "movie.graphql"))

query = QueryType()
mutation = MutationType()
movieType = ObjectType("Movie")

query.set_field("all_movies", r.all_movies)
query.set_field("movie_with_id", r.movie_with_id)
mutation.set_field("create_movie", r.create_movie)
mutation.set_field("update_movie_rate", r.update_movie_rate)
mutation.set_field("delete_movie", r.delete_movie)
movieType.set_field("actors", r.resolve_actors_in_movie)

schema = make_executable_schema(typeDefs, query, mutation, movieType)


@app.route("/", methods=["GET"])
def home():
    """Retourne le message d'accueil du service"""

    return make_response("Welcome", 200)


@app.route("/graphql", methods=["POST"])
def graphql_server():
    """Exécute query ou mutation reçu dans le body jsob"""

    requestData = request.get_json(silent=True)

    if not isinstance(requestData, dict):
        return (
            jsonify(
                {
                    "errors": [{"message": "body doit être un objet json"}],
                }
            ),
            400,
        )

    success, result = graphql_sync(
        schema,
        requestData,
        context_value={},
        debug=app.debug,
    )
    statusCode = 200 if success else 400
    return jsonify(result), statusCode


if __name__ == "__main__":
    app.run(host=HOST, port=PORT)
