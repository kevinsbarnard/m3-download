# m3_requests.py (m3-download)

import requests

from lib.config import Config


def get_fast_concept_images(config: Config, concept: str):
    return requests.get(config('m3', 'fastconceptimages') + '/' + concept).json()
