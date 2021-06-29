# generate_digest.py (m3-download)
"""
Look up observations (with a valid image) for a given concept and generate a digest
"""

import argparse
import datetime
import json
import sys
import time

from lib.config import Config
from lib.m3_requests import get_fast_concept_images, get_concept_descendants, get_imaged_moment_data

WHITESPACE_REPLACEMENT = '_'


def write_digest(json_data, concept, include_descendants):
    out_path = concept.replace(' ', WHITESPACE_REPLACEMENT) + ('_desc' if include_descendants else '') + '_digest.json'
    with open(out_path, 'w') as f:
        json.dump(json_data, f, indent=2)
    print('Wrote digest to {}'.format(out_path))


def main(concept, config_path, include_descendants, include_all):
    config = Config(config_path)
    if include_descendants:
        print('Getting observations for {} + descendants...'.format(concept))
        concepts = list(get_concept_descendants(config, concept))
        concepts.insert(0, concept)
        print('Included concepts: {}'.format(', '.join(concepts)))
        json_data = []
        for c in concepts:
            json_part = get_fast_concept_images(config, c)
            if json_part is None:  # Fatal
                exit(1)
            json_data.extend(json_part)
        print('Found {} observations of {} + descendants with valid images'.format(len(json_data), concept))
    else:
        print('Getting observations for {}...'.format(concept))
        json_data = get_fast_concept_images(config, concept)
        if not json_data:  # Fatal
            exit(1)
        print('Found {} observations of {} with valid images'.format(len(json_data), concept))

    if include_all:
        imaged_moment_uuids = set(obs['imaged_moment_uuid'] for obs in json_data)
        n_uuids = len(imaged_moment_uuids)
        print('Fetching all other observations for {} imaged moments...'.format(n_uuids))

        t0 = time.time()

        added_observations = []
        observation_uuids = set(obs['observation_uuid'] for obs in json_data)
        for idx, imaged_moment_uuid in enumerate(imaged_moment_uuids):
            if idx % 1 == 0:
                rate = (time.time() - t0) / (idx + 1 / n_uuids)
                seconds_remaining = round(rate * (n_uuids - (idx + 1)))
                output_str = 'Remaining time: {:<10} {:>20}\r'.format(
                    str(datetime.timedelta(seconds=seconds_remaining)),
                    '({}/{})'.format(idx + 1, n_uuids)
                )
                sys.stdout.write(output_str)
                sys.stdout.flush()

            # Grab the imaged moment data
            imaged_moment = get_imaged_moment_data(config, imaged_moment_uuid)
            if not imaged_moment:
                continue

            # Add new observations
            for observation in imaged_moment['observations']:
                observation_uuid = observation['uuid']
                if observation_uuid not in observation_uuids:  # Ensures no duplicates
                    observation_uuids.add(observation_uuid)

                    # Construct a JSON blob following the fast endpoint response schema
                    obs_data = {
                        'observation_uuid': observation_uuid,
                        'concept': observation['concept'],
                        'observer': observation['observer'],
                        'video_reference_uuid': imaged_moment['video_reference_uuid'],
                        'imaged_moment_uuid': imaged_moment_uuid,
                        'associations': observation['associations'],
                        'image_references': imaged_moment['image_references']
                    }

                    # Find time key(s) and tack on
                    if 'recorded_date' in imaged_moment:
                        obs_data['recorded_timestamp'] = imaged_moment['recorded_date']  # Inconsistency in M3
                    if 'timecode' in imaged_moment:
                        obs_data['timecode'] = imaged_moment['timecode']
                    if 'elapsed_time_millis' in imaged_moment:
                        obs_data['elapsed_time_millis'] = imaged_moment['elapsed_time_millis']

                    # Some more misc keys
                    if 'activity' in observation:
                        obs_data['activity'] = observation['activity']

                    added_observations.append(obs_data)

        json_data += added_observations
        print('\nAdded {} observations'.format(len(added_observations)))

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
    parser.add_argument('-a', '--all',
                        action='store_true',
                        help='Flag to include all other observations for each imaged moment in digest')
    args = parser.parse_args()
    main(args.concept, args.config, args.descendants, args.all)
