from pathlib import Path

from ariadne import (
    graphql_sync,
    make_executable_schema,
    load_schema_from_path,
    ObjectType,
    QueryType,
    MutationType,
)
from flask import Flask, request, jsonify, make_response

import resolvers as r

PORT = 3001
HOST = "0.0.0.0"
app = Flask(__name__)

# create elements for Ariadne
schemaPath = Path(__file__).resolve().parent / "booking.graphql"
typeDefs = load_schema_from_path(str(schemaPath))

query = QueryType()
mutation = MutationType()
bookingDateType = ObjectType("BookingDate")

query.set_field("booking_with_userid", r.booking_with_userid)
mutation.set_field("create_booking", r.create_booking)
mutation.set_field("delete_booking", r.delete_booking)
bookingDateType.set_field("movie_details", r.resolve_movie_details)

schema = make_executable_schema(typeDefs, query, mutation, bookingDateType)


# root message
@app.route("/", methods=["GET"])
def home():
    """Retourne le message d'accueil du service"""

    return make_response(
        "<h1 style='color:blue'>Welcome to the Booking service!</h1>", 200
    )


# graphql entry points
@app.route("/graphql", methods=["POST"])
def graphql_server():
    """Exécute une query ou mutation reçue dans le body json"""

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
    print("Server running in port %s" % (PORT))
    app.run(host=HOST, port=PORT)
