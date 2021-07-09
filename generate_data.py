# generate_data.py (m3-download)
"""
Generate a complete dataset (combination of individual tools)
"""
import argparse
import json
import os
from json import JSONDecodeError

import progressbar
import requests
import PIL.Image as Image

from lib.config import Config
from lib.localization import Localization, PascalVOC
from lib.m3_requests import get_concept_taxa, get_fast_concept_images, get_imaged_moment_data, get_image_reference_data
from lib.utils import error, warning


def read_concepts_from_file(concept_file: str):
    if not os.path.exists(concept_file):
        raise FileNotFoundError('{} does not exist.'.format(concept_file))
    if not os.path.isfile(concept_file):
        raise ValueError('{} is not a file.'.format(concept_file))

    with open(concept_file) as f:
        return f.read().splitlines()


def extract_observation_localizations(observation):
    concept = observation['concept']
    if 'associations' in observation:
        for association_item in observation['associations']:
            to_concept = association_item['to_concept']
            if association_item['link_name'] == 'bounding box':
                box_json = association_item['link_value']
                try:
                    box_data = json.loads(box_json)
                    localization = Localization(float(box_data['x']),
                                                float(box_data['y']),
                                                float(box_data['width']),
                                                float(box_data['height']))
                    image_reference_uuid = box_data['image_reference_uuid']
                    yield concept, to_concept, localization, image_reference_uuid
                except JSONDecodeError:
                    warning('Malformed JSON in bounding box association with UUID {}'.format(association_item['uuid']))
                except KeyError as e:
                    warning('Missing key {} in bounding box association with UUID {}'.format(e.args,
                                                                                             association_item['uuid']))


def get_image_url(config, image_reference_uuid):
    image_data = get_image_reference_data(config, image_reference_uuid)
    if image_data is None:
        return None

    return image_data['url']


def download_image(url, path):
    res = requests.get(url, stream=True, timeout=10)  # stream=True so we don't load the whole thing into memory
    if res.status_code == 200:
        with open(path, 'wb') as f:
            for chunk in res.iter_content(1024):
                f.write(chunk)
        return True
    return False


def main(concepts, output_dir, config_file, include_descendants, include_all, overwrite_images):
    # Make the output directory if it doesn't exist
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    # Read the config file
    config = Config(config_file)

    # Collect specified concepts
    specified_concepts = []
    if include_descendants:
        print('Getting descendants for {} concepts...'.format(len(concepts)))
        for concept in progressbar.progressbar(concepts, redirect_stdout=True):
            concept_taxa = get_concept_taxa(config, concept)  # Call to vars-kb-server
            if concept_taxa is not None:
                specified_concepts.extend(concept_taxa)
    else:
        specified_concepts = concepts

    specified_concepts = set(specified_concepts)
    print('Concepts specified ({} total):\n'.format(len(specified_concepts)) +
          '\n'.join(['- ' + concept for concept in sorted(specified_concepts)]))

    # Look up observations of all specified concepts
    print('\nGetting observations for specified concepts...')
    observations = []
    for concept in progressbar.progressbar(specified_concepts, redirect_stdout=True):
        observation_data = get_fast_concept_images(config, concept)
        if observation_data is not None:
            observations.extend(observation_data)
    print('Fetched {} total observations'.format(len(observations)))

    # Extract available image references
    image_reference_map = {}
    print('\nExtracting image reference map...')
    for observation in progressbar.progressbar(observations):
        if 'image_references' in observation:
            for image_reference_item in observation['image_references']:
                image_reference_map[image_reference_item['uuid']] = image_reference_item['url']
    print('Extracted {} image references'.format(len(image_reference_map)))

    # Extract bounding box associations from available observations
    all_localizations = []
    print('\nExtracting localizations from available observations...')
    for observation in progressbar.progressbar(observations, redirect_stdout=True):
        all_localizations.extend(extract_observation_localizations(observation))

    # Fetch all other localizations in corresponding imaged moments
    if include_all:
        prior_observation_uuids = set(
            observation['observation_uuid']
            for observation in observations
            if 'imaged_moment_uuid' in observation
        )

        imaged_moment_uuids = set(  # Collect imaged moment UUIDs
            observation['imaged_moment_uuid']
            for observation in observations
            if 'imaged_moment_uuid' in observation
        )

        print('Getting all other localizations in {} corresponding imaged moments...'.format(len(imaged_moment_uuids)))
        for imaged_moment_uuid in progressbar.progressbar(imaged_moment_uuids, redirect_stdout=True):
            imaged_moment_data = get_imaged_moment_data(config, imaged_moment_uuid)  # Call to annosaurus
            if imaged_moment_data is not None and 'observations' in imaged_moment_data:
                imaged_moment_observations = imaged_moment_data['observations']
                for observation in imaged_moment_observations:
                    if observation['uuid'] not in prior_observation_uuids:
                        all_localizations.extend(extract_observation_localizations(observation))

    print('Fetched {} total localizations'.format(len(all_localizations)))

    image_reference_uuids = set(
        loc_tup[3] for loc_tup in all_localizations
    )
    print('\nFetching any missing URLs...'.format(len(image_reference_uuids)))
    with progressbar.ProgressBar(max_value=progressbar.UnknownLength, redirect_stdout=True) as bar:
        count = 0
        for image_reference_uuid in image_reference_uuids:
            if image_reference_uuid not in image_reference_map:
                url = get_image_url(config, image_reference_uuid)
                if url is not None:
                    image_reference_map[image_reference_uuid] = url
                    count += 1
                    bar.update(count)

    image_subdir = os.path.join(output_dir, 'images')
    os.makedirs(image_subdir, exist_ok=True)  # Make the image download directory if it doesn't exist
    filename_map = {  # Construct map of url -> filename (using image reference UUID as filename)
        url: os.path.join(image_subdir, image_reference_uuid + os.path.splitext(url)[-1])
        for image_reference_uuid, url in image_reference_map.items()
        if image_reference_uuid in image_reference_uuids
    }
    needed_urls = []
    for url, image_path in filename_map.items():
        if not os.path.exists(image_path) or not os.path.isfile(image_path):
            needed_urls.append(url)

    print('\nDownloading {} images to {}...'.format(len(needed_urls), image_subdir))
    image_download_bar_widgets = [
        progressbar.Percentage(),
        ' (', progressbar.SimpleProgress(), ') ',
        progressbar.Bar(),
        progressbar.AdaptiveTransferSpeed(prefixes=('',), unit='images', samples=100),
        ' ', progressbar.Timer(),
        ' ', progressbar.ETA()
    ]
    with progressbar.ProgressBar(max_value=len(needed_urls), widgets=image_download_bar_widgets, redirect_stdout=True) as bar:
        for idx, url in enumerate(needed_urls):
            output_file = filename_map[url]
            success = download_image(url, output_file)  # Download the image
            if not success:
                warning('{} failed to download.'.format(url))
            bar.update(idx + 1)

    xml_subdir = os.path.join(output_dir, 'xml')
    os.makedirs(xml_subdir, exist_ok=True)
    valid_localizations = [
        loc_tup
        for loc_tup in all_localizations
        if loc_tup[3] in image_reference_map and os.path.exists(filename_map[image_reference_map[loc_tup[3]]])
    ]
    image_reference_loc_map = {}
    for concept, to_concept, localization, image_reference_uuid in valid_localizations:
        if image_reference_uuid not in image_reference_loc_map:  # Collect localizations by image reference
            image_reference_loc_map[image_reference_uuid] = []

        label = concept
        if to_concept != 'self':
            label += ' ' + to_concept
        image_reference_loc_map[image_reference_uuid].append((label, localization))

    voc_annotation_record = PascalVOC()
    for image_reference_uuid, label_loc_tups in image_reference_loc_map.items():
        image_path = filename_map[image_reference_map[image_reference_uuid]]
        with Image.open(image_path) as im:
            width, height = im.size
            depth = len(im.getbands())

        annotation = PascalVOC.Annotation(image_subdir,
                                          os.path.basename(image_path),
                                          (height, width, depth),
                                          label_loc_tups)

        voc_annotation_record.annotations.append(annotation)

    voc_annotation_record.write(xml_subdir, '{}.xml')
    print('\nWrote {} VOC-formatted localizations to {}.'.format(len(valid_localizations), xml_subdir))


if __name__ == '__main__':
    _parser = argparse.ArgumentParser(description=__doc__)

    _mutex_concept_spec_group = _parser.add_mutually_exclusive_group()
    _mutex_concept_spec_group.add_argument('--concepts',
                                           type=str,
                                           help='Concepts to include, separated by commas.')
    _mutex_concept_spec_group.add_argument('--concept-file',
                                           type=str,
                                           dest='conceptfile',
                                           help='Path to file containing list of concepts, one per line.')

    _parser.add_argument('--config',
                         type=str,
                         default='config.ini',
                         help='Path to configuration file.')
    _parser.add_argument('-d', '--include-descendants',
                         action='store_true',
                         dest='include_descendants',
                         help='Flag to include descendants of specified concepts.')
    _parser.add_argument('-a', '--include-all',
                         action='store_true',
                         dest='include_all',
                         help='Flag to include all other observations for each imaged moment in digest.')
    _parser.add_argument('-o', '--overwrite',
                         action='store_true',
                         dest='overwrite_images',
                         help='Flag to overwrite existing images. If unspecified, existing images will be detected and skipped.')

    _parser.add_argument('output_dir',
                         type=str,
                         help='Path to output directory. If output_dir does not exist, it will be created.')

    _args = _parser.parse_args()

    _concepts = []
    if _args.conceptfile is not None:
        try:
            _concepts = read_concepts_from_file(_args.conceptfile)
        except (FileNotFoundError, ValueError) as _e:
            error(_e)
            exit(1)
    else:
        _concepts = _args.concepts.split(',')

    main(_concepts, _args.output_dir, _args.config, _args.include_descendants, _args.include_all, _args.overwrite_images)
