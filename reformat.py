# reformat.py (m3-download)
"""
Reformat a localization file to a desired format
"""

import argparse
import json
import os
from datetime import datetime
from uuid import UUID

from lib.localization import COCO, PascalVOC

FORMATS = {
    'COCO': 'json',
    'VOC': 'xml'
}


def formats_str() -> str:
    return ', '.join([f.upper() for f in FORMATS])


def main(localizations_path: str, output_name: str, format_type: str, image_map_filename: str):
    with open(localizations_path) as f:
        localizations = json.load(f)

    if format_type == 'COCO':
        output_path = output_name + '.' + FORMATS[format_type]
        all_images = []
        all_categories = set()
        for localization in localizations:
            for image_reference_uuid, url in localization['image_urls'].items():
                record = {
                    'id': UUID(image_reference_uuid).int,
                    'file_name': os.path.basename(url)
                }
                if record not in all_images:
                    all_images.append(record)

            all_categories.add(localization['concept'])

        now = datetime.now()
        annotation_record = COCO(images=all_images,
                                 categories=list(all_categories),
                                 year=now.year,
                                 date_created=str(now))

        for localization in localizations:
            annotation_record.add_annotation(localization)

        annotation_record.write(output_path)
        print('Wrote COCO annotation record to {}'.format(output_path))

    elif format_type == 'VOC':
        if not image_map_filename:
            print('[ERROR] Image map argument must be specified for VOC formatting (--image_map)')
            exit(1)

        # Load the image map
        with open(image_map_filename) as f:
            image_map = json.load(f)

        iruuid_locs = {}
        for loc in localizations:
            if 'image_reference_uuid' not in loc['localization']:  # Malformed localization, cannot backreference
                print('[WARNING] Localization with association UUID {} has malformed JSON, skipping'.format(
                    loc['association_uuid']
                ))
                continue

            iruuid = loc['localization']['image_reference_uuid']
            if iruuid not in iruuid_locs:
                iruuid_locs[iruuid] = []

            iruuid_locs[iruuid].append(loc)

        annotation_record = PascalVOC()
        for iruuid, locs in iruuid_locs.items():
            annotation_record.add_annotation(iruuid, locs, image_map)

        annotation_record.write(output_name, '{}.' + FORMATS[format_type])
        print('Wrote {} VOC XML files to {}'.format(len(annotation_record.annotations), output_name))

    elif format_type in FORMATS:
        print('Unimplemented format: {}'.format(format_type))
    else:
        print('Invalid format: {}'.format(format_type))


if __name__ == '__main__':
    _parser = argparse.ArgumentParser(description=__doc__)
    _parser.add_argument('localizations',
                         type=str,
                         help='Path to localizations JSON file (see extract_localizations.py)')
    _parser.add_argument('-o', '--output',
                         type=str,
                         default='',
                         help='Output file name, omitting the extension (dependent on format)')
    _parser.add_argument('-f', '--format',
                         type=str,
                         default='COCO',
                         help='Localization format to write. Options: ' + formats_str())
    _parser.add_argument('--image_map',
                         type=str,
                         help='Image filename map for VOC formatting (see download_images.py)')
    _args = _parser.parse_args()

    _output = _args.output
    if not _output:
        _output = os.path.splitext(_args.localizations)[0] + '_reformatted'

    main(_args.localizations, _output, _args.format.upper(), _args.image_map)
