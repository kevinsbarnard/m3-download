# generate_digest.py (m3-download)
"""
Look up observations (with a valid image) for a given concept and generate a digest
"""

import argparse
import json

import requests

from lib.config import Config
from lib.m3_requests import get_fast_concept_images, get_concept_descendants

WHITESPACE_REPLACEMENT = '_'


def write_digest(json_data, concept, include_descendants):
    out_path = concept.replace(' ', WHITESPACE_REPLACEMENT) + ('_desc' if include_descendants else '') + '_digest.json'
    with open(out_path, 'w') as f:
        json.dump(json_data, f, indent=2)
    print('Wrote digest to {}'.format(out_path))


def main(concept, config_path, include_descendants):
    config = Config(config_path)
    if include_descendants:
        print('Getting observations for {} + descendants...'.format(concept))
        concepts = list(get_concept_descendants(config, concept))
        concepts.insert(0, concept)
        json_data = []
        for c in concepts:
            json_data.extend(get_fast_concept_images(config, c))
        print('Found {} observations of {} + descendants with valid images'.format(len(json_data), concept))
    else:
        print('Getting observations for {}...'.format(concept))
        json_data = get_fast_concept_images(config, concept)
        print('Found {} observations of {} with valid images'.format(len(json_data), concept))
    write_digest(json_data, concept, include_descendants)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('concept',
                        type=str,
                        help='VARS concept')
    parser.add_argument('-c', '--config',
                        type=str,
                        default='config.ini',
                        help='Config path')
    parser.add_argument('-d', '--descendants',
                        action='store_true',
                        help='Flag to include descendants in digest')
    args = parser.parse_args()
    main(args.concept, args.config, args.descendants)
