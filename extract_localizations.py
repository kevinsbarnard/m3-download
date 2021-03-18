# extract_localizations.py (m3-download)
__description__ = '''
Extract localizations from a digest (see generate_digest.py) and format them nicely
'''

import argparse
import json


def observation_localizations(observation_data):
    for assoc in observation_data['associations']:
        if assoc['link_name'] == 'bounding box':
            yield {
                'observation_uuid': observation_data['observation_uuid'],
                'association_uuid': assoc['uuid'],
                'concept': observation_data['concept'],
                'localization': json.loads(assoc['link_value']),
                'images': {
                    e['format']: e['url']
                    for e in observation_data['image_references']
                }
            }


def extract_localizations(observations):
    localizations = []
    for observation in observations:
        localizations.extend(list(observation_localizations(observation)))
    return localizations


def main(digest_paths):
    all_localizations = []
    for digest_path in digest_paths:
        with open(digest_path) as f:
            observations = json.load(f)
            all_localizations.extend(extract_localizations(observations))

    with open('localizations.json', 'w') as f:
        json.dump(all_localizations, f, indent=2)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__description__)
    parser.add_argument('digest', nargs='+', type=str, help='Path to the digest JSON')
    args = parser.parse_args()
    main(args.digest)
