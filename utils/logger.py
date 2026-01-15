import logging
import os

LOG_FILE = os.path.join(
    os.path.dirname(__file__),
    "..",
    "logs",
    "runtime.log"
)

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(message)s"
)

def log(msg):
    logging.info(msg)
