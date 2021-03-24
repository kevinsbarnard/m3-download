# m3_requests.py (m3-download)

import requests

from lib.config import Config


def get_fast_concept_images(config: Config, concept: str):
    return requests.get(config('m3', 'fastconceptimages') + '/' + concept).json()


def get_concept_descendants(config:Config, concept: str) -> list:
    def recursive_accumulate(tree):
        names = set()
        if 'children' not in tree:
            return names

        for child in tree['children']:
            names.add(child['name'])
            names = names.union(recursive_accumulate(child))

        return names

    url = config('m3', 'kbdesc')
    res = requests.get(url + '/' + concept)

    return recursive_accumulate(res.json())
