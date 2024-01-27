"""An application regarding a Web REST-API that fetches the artists from a MongoDB
and sends them into a Kafka topic channel."""
import json
import os

from dotenv import load_dotenv
from flask import Flask, jsonify
from kafka import KafkaProducer

from common.mongoDb import MyMongoClient
from common.webUtils import WebUtils

# Load environment variables from .env file
load_dotenv()

# MongoDB's connection settings
mongo_uri = os.environ.get("MONGODB_URI")
database_name = "MusicAlbums"
collection_name = "Albums"

PORT = os.environ.get("ARTISTS_PORT")
TOPIC = os.environ.get("KAFKA_TOPIC_ARTISTS")

# Connect to MongoDB
collection, client = MyMongoClient.connect_to_mongodb(mongo_uri, database_name, collection_name)

app = Flask(__name__)

"""
A route GET regarding the artists that are located on a MondoDB collection,
that fetched the artists who released albums on the given <data> parameter.
"""


@app.route("/get_artists/<date>", methods=["GET"])
def get_artists(date):
    str_iso_date = WebUtils.date_str_to_iso_format(date)

    app.logger.debug("Searching for Artists the released date: %s", str_iso_date)

    artists = WebUtils.parse_json(collection.find({"albums.release_date": {"$eq": str_iso_date}}))

    send_artists_metadata(artists)
    return jsonify(artists)


producer = KafkaProducer(bootstrap_servers=[os.environ.get("KAFKA_BROKER")],
                         value_serializer=lambda m: json.dumps(m).encode("ASCII")
                         )


# Log on successful sent.
def on_send_success(record_metadata):
    app.logger.debug(record_metadata.topic)
    app.logger.debug(record_metadata.partition)
    app.logger.debug(record_metadata.offset)


def on_send_error(excp):
    app.logger.error("Error occurred on kafka topic sent", exc_info=excp)


"""
Send an artist payload into a Kafka topic named uni-artist as defined
in environment variable KAFKA_TOPIC_ARTISTS.
"""


def send_artists_metadata(metadata):
    (producer.send(TOPIC, metadata)
     .add_callback(on_send_success)
     .add_errback(on_send_error))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=True)
