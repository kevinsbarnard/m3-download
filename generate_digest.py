# generate_digest.py (m3-download)
__description__ = '''
Look up observations (with a valid image) for a given concept and generate a digest
'''

import argparse
import json

from lib.config import Config
from lib.m3_requests import get_fast_concept_images

WHITESPACE_REPLACEMENT = '_'


def write_digest(json_data, concept):
    out_path = concept.replace(' ', WHITESPACE_REPLACEMENT) + '_digest.json'
    with open(out_path, 'w') as f:
        json.dump(json_data, f, indent=2)
    print('Wrote digest to {}'.format(out_path))


def main(concept, config_path):
    config = Config(config_path)
    print('Getting observations for {}...'.format(concept))
    json_data = get_fast_concept_images(config, concept)
    print('Found {} observations of {} with valid images'.format(len(json_data), concept))
    write_digest(json_data, concept)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__description__)
    parser.add_argument('concept', type=str, help='VARS concept')
    parser.add_argument('--config', type=str, default='config.ini', help='Config path')
    args = parser.parse_args()
    main(args.concept, args.config)
