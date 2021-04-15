# download_images.py (m3-download)
"""
Download images corresponding to localizations
"""

import argparse
import json
import os
from multiprocessing import Pool

import requests


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


def get_image_info(localizations, image_format):
    all_urls = set(loc['images'][image_format]['url'] for loc in localizations if image_format in loc['images'])
    urls = list(all_urls)
    filenames = [os.path.basename(url) for url in urls]

    return urls, filenames


def main(localizations_path, output_dir, n_workers, image_format, overwrite=False):
    with open(localizations_path) as f:
        localizations = json.load(f)

    urls, filenames = get_image_info(localizations, image_format)
    paths = [os.path.join(output_dir, filename) for filename in filenames]

    if not overwrite:
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
            fail_out = 'failures.csv'
            with open(fail_out, 'w') as f:
                f.write('\n'.join([failure[0] + ',' + failure[1] for failure in failures]))
            print('{} failures written to {}'.format(len(failures), fail_out))
    else:
        print('Canceled.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('localizations', type=str, help='Path to JSON list of localizations')
    parser.add_argument('output_dir', type=str, help='Output directory')
    parser.add_argument('-j', '--jobs', type=int, default=1, help='Number of multiprocessing jobs to use (default=1)')
    parser.add_argument('-f', '--format', type=str, default='image/png', help='Image format to use (default=image/png)')
    parser.add_argument('-o', '--overwrite', action='store_true', help='Overwrite existing images')
    args = parser.parse_args()
    main(args.localizations, args.output_dir, args.jobs, args.format, overwrite=args.overwrite)
