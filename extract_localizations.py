# extract_localizations.py (m3-download)
"""
Extract localizations from a digest (see generate_digest.py) and format them nicely
"""

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
                    e['format']: {
                        'url': e['url'],
                        'image_reference_uuid': e['uuid']
                    }
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
            localizations = extract_localizations(observations)
            print('{:<50}: {:>10} localizations'.format(digest_path, len(localizations)))
            all_localizations.extend(localizations)

    print('Extracted {} total localizations'.format(len(all_localizations)))

    out_path = 'localizations.json'
    with open(out_path, 'w') as f:
        json.dump(all_localizations, f, indent=2)

    print('Wrote to {}'.format(out_path))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('digest', nargs='+', type=str, help='Path to the digest JSON')
    args = parser.parse_args()
    main(args.digest)
