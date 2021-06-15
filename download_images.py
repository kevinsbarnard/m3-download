# download_images.py (m3-download)
"""
Download images corresponding to localizations
"""

import argparse
import json
import os
from multiprocessing import Pool

import requests

from lib.config import Config
from lib.m3_requests import get_image_reference_data

IMAGE_MAP_FILENAME = 'image_map.json'
DOWNLOAD_FAILURE_FILENAME = 'failures.csv'


def download_image(url, path):
    res = requests.get(url, stream=True)  # stream=True so we don't load the whole thing into memory
    if res.status_code == 200:
        with open(path, 'wb') as f:
            for chunk in res.iter_content(1024):
                f.write(chunk)
        return True
    return False


def download_helper(url_path_tup):
    url, path = url_path_tup
    return download_image(url, path)


def download_images(urls, paths, n_workers):
    """ Download the images specified by `urls` to `paths` using `n_workers` """
    # Zip the urls and paths for mapping
    url_path_tups = list(zip(urls, paths))

    multi = n_workers > 1
    if multi:  # Use multiprocessing
        pool = Pool(n_workers)
        successes = pool.map(download_helper, url_path_tups)
    else:  # Don't use multiprocessing
        successes = map(download_helper, url_path_tups)

    # Zip the results into a dictionary
    success_map = dict(zip(url_path_tups, successes))

    # Extract failures and return
    failures = [k for k, v in success_map.items() if not v]
    return failures


def get_image_url(config, image_reference_uuid):
    image_data = get_image_reference_data(config, image_reference_uuid)
    if image_data is None:
        return None

    return image_data['url']


def main(localizations_path, output_dir, n_workers, config_path, overwrite=False):
    # Load the config
    config = Config(config_path)

    # Load localizations
    with open(localizations_path) as f:
        localizations = json.load(f)

    # Extract all image reference UUIDs required by localizations
    all_locs_json = [loc['localization'] for loc in localizations]  # Get the JSON from all localization objects
    image_reference_uuids = set(  # Extract the set of image reference UUIDs
        loc_json['image_reference_uuid']
        for loc_json in all_locs_json
        if 'image_reference_uuid' in loc_json
    )

    # Extract all available image reference UUID -> URL mappings from initial digest
    available_url_map = {}
    for loc in localizations:
        available_url_map.update(loc['image_urls'])

    # Get all needed URLs
    # If any missing, fetch from VARS
    url_map = {}
    for image_reference_uuid in image_reference_uuids:
        if image_reference_uuid in available_url_map:
            url = available_url_map[image_reference_uuid]
        else:
            print('Fetching missing URL for image reference UUID: {}'.format(image_reference_uuid))
            url = get_image_url(config, image_reference_uuid)
            if url is None:
                continue

        url_map[image_reference_uuid] = url

    # Compute and write out a filename JSON map (for back-referencing)
    filename_map = {
        iruuid: os.path.join(output_dir, os.path.basename(url_map[iruuid]))
        for iruuid in url_map
    }
    with open(IMAGE_MAP_FILENAME, 'w') as f:
        json.dump(filename_map, f, indent=2, sort_keys=True)
    print('Image map written to {}'.format(IMAGE_MAP_FILENAME))

    # Extract URLs and file paths to parallel work lists
    urls = list(url_map.values())
    paths = [os.path.join(output_dir, os.path.basename(url)) for url in urls]

    if not overwrite:  # Filter out already-downloaded images
        url_path_tups = zip(urls, paths)
        url_path_tups = list(filter(lambda t: not os.path.exists(t[1]), url_path_tups))
        if not url_path_tups:
            print('All images already downloaded.')
            return
        urls, paths = zip(*url_path_tups)

    confirm = input('Confirm download of {} images to {} (y/n): '.format(len(urls), os.path.abspath(output_dir)))
    if confirm.lower() == 'y':
        os.makedirs(output_dir, exist_ok=True)  # Create directories if they don't exist
        print('Downloading images (this could take a while)...')
        failures = download_images(urls, paths, n_workers)
        print('Download successful for {}/{} images.'.format(len(urls) - len(failures), len(urls)))
        if failures:
            with open(DOWNLOAD_FAILURE_FILENAME, 'w') as f:
                f.write('\n'.join([failure[0] + ',' + failure[1] for failure in failures]))
            print('{} failures written to {}'.format(len(failures), DOWNLOAD_FAILURE_FILENAME))
    else:
        print('Canceled.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('localizations',
                        type=str,
                        help='Path to JSON list of localizations')
    parser.add_argument('output_dir',
                        type=str,
                        help='Output directory')
    parser.add_argument('-j', '--jobs',
                        type=int,
                        default=1,
                        help='Number of multiprocessing jobs to use (default=1)')
    parser.add_argument('-c', '--config',
                        type=str,
                        default='config.ini',
                        help='Config path')
    parser.add_argument('-o', '--overwrite', action='store_true', help='Overwrite existing images')
    args = parser.parse_args()
    main(args.localizations, args.output_dir, args.jobs, args.config, overwrite=args.overwrite)
