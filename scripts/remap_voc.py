# remap_voc.py (m3-download)
"""
Remap concepts in a directory of Pascal VOC annotation XMLs
"""
import argparse
import csv
import glob
import json
import os
from typing import Optional, List
import xml.etree.ElementTree as ETree
from xml.dom import minidom


def read_map_file(map_file: str) -> Optional[dict]:
    ext = os.path.splitext(map_file)[-1]

    if ext == '.csv':  # Detect CSV
        concept_map = {}
        with open(map_file) as f:
            reader = csv.reader(f)
            for line in reader:
                concept_map[line[0]] = line[1]

        return concept_map

    elif ext == '.json':  # Detect JSON
        with open(map_file) as f:
            return json.load(f)


def remap_voc(voc_paths: List[str], mapping: dict, output_dir: Optional[str] = None):
    """
    Remap concepts in a list of VOC annotations according to `mapping`
    Overwrite files unless `output_dir` is specified
    """
    n_modified = 0

    for voc_path in voc_paths:
        tree = ETree.parse(voc_path)
        root = tree.getroot()

        modified = False

        objects = root.findall('object')
        for loc in objects:
            # Get class label name and map index
            name_tag = loc.find('name')
            name = name_tag.text

            if name in mapping and name != mapping[name]:
                name_tag.text = mapping[name]
                modified = True

        n_modified += modified

        # Write to output
        if modified or output_dir is not None:
            output_path = voc_path
            if output_dir is not None:
                output_path = os.path.join(output_dir, os.path.basename(voc_path))

            with open(output_path, 'w') as f:
                f.write('\n'.join([
                    line for line in minidom.parseString(
                        ETree.tostring(root, encoding='unicode')
                    ).toprettyxml(indent=' ' * 4).splitlines()[1:]
                    if line.strip()
                ]))

    print('[INFO] Modified {} annotation XMLs'.format(n_modified))


def main(map_file: str, input_dir: str, output_dir: Optional[str] = None):
    concept_map = read_map_file(map_file)
    if concept_map is None:
        print('[ERROR] Invalid map file extension')
        exit(1)

    if not os.path.exists(input_dir) or not os.path.isdir(input_dir):
        print('[ERROR] Input directory {} does not exist'.format(input_dir))
        exit(1)

    if output_dir is not None and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        print('[INFO] Created output directory {}'.format(output_dir))

    voc_paths = glob.glob(os.path.join(input_dir, '*.xml'))

    print('[INFO] Found {} annotation XMLs'.format(len(voc_paths)))

    remap_voc(voc_paths, concept_map, output_dir=output_dir)


if __name__ == '__main__':
    _parser = argparse.ArgumentParser(description=__doc__)
    _parser.add_argument('map_file',
                         type=str,
                         help='File (.csv or .json) containing remapping')
    _parser.add_argument('input_dir',
                         type=str,
                         help='Input directory of VOC annotation XMLs')
    _parser.add_argument('-o', '--output_dir',
                         type=str,
                         default=None,
                         help='(optional) Output directory for remapped annotations (if unspecified, original '
                              'annotation files will be overwritten)')
    _args = _parser.parse_args()
    main(_args.map_file, _args.input_dir, _args.output_dir)
