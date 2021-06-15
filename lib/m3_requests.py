# m3_requests.py (m3-download)
from json import JSONDecodeError

import requests

from lib.config import Config


def get_fast_concept_images(config: Config, concept: str):
    try:
        return requests.get(config('m3', 'fastconceptimages') + '/' + concept).json()
    except JSONDecodeError:
        print('[ERROR] Failed to get observations for concept: {}'.format(concept))


def get_concept_descendants(config: Config, concept: str) -> list:
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


def get_imaged_moment_data(config: Config, imaged_moment_uuid: str):
    try:
        return requests.get(config('m3', 'imagedmoment') + '/' + imaged_moment_uuid.lower()).json()
    except JSONDecodeError:
        print('[ERROR] Failed to get imaged moment data for UUID: {}'.format(imaged_moment_uuid.lower()))


def get_image_reference_data(config: Config, image_reference_uuid: str):
    try:
        return requests.get(config('m3', 'imagereference') + '/' + image_reference_uuid.lower()).json()
    except JSONDecodeError:
        print('[ERROR] Failed to get image reference data for UUID: {}'.format(image_reference_uuid.lower()))
