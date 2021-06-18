# add_taxonomy.py (m3-download)
"""
Add taxonomic information to Pascal VOC annotations
"""
import argparse
import glob
import json
import os
import re
from typing import List, Optional
from urllib.request import urlopen
from urllib.error import URLError
from urllib.parse import quote
import xml.etree.ElementTree as ETree
from xml.dom import minidom

TAXONOMY_ENDPOINT = 'http://dsg.mbari.org/kb/v1/phylogeny/basic'
CONCEPT_REGEX = '<name>.*</name>'


def get_basic_taxonomy(concept: str):
    """ Call the phylogeny/basic endpoint on a concept and return its response as decoded JSON """
    url = TAXONOMY_ENDPOINT + '/' + quote(concept)
    try:
        with urlopen(url) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print('[ERROR] Failed to decode JSON in taxonomy response')
        print(e)
    except URLError as e:
        print('[ERROR] Failed to fetch taxonomic information for {} at {}'.format(concept, url))
        print(e)


def extract_taxonomy(taxonomy_json: List[dict]):
    """ Extract the taxonomic names into a dict """
    rank_dict = {}
    for object_data in taxonomy_json:
        if 'rank' in object_data:
            rank_dict[object_data['rank']] = object_data['name']

    return rank_dict


def add_taxonomy(voc_paths: List[str], output_dir: Optional[str] = None):
    """ Add taxonomic information to a list of Pascal VOC annotation files """
    concept_pattern = re.compile(CONCEPT_REGEX)

    all_concepts = set()
    for voc_path in voc_paths:
        with open(voc_path) as f:
            data = f.read()
            for concept_match in concept_pattern.finditer(data):
                concept = concept_match[0][6:-7]
                all_concepts.add(concept)

    print('[INFO] Identified {} unique concepts. Fetching taxonomic info...'.format(len(all_concepts)))

    concept_taxa_map = {}
    for concept in all_concepts:
        concept_json = get_basic_taxonomy(concept)
        if concept_json is None:
            continue

        concept_taxa = extract_taxonomy(concept_json)
        concept_taxa_map[concept] = concept_taxa

    for voc_path in voc_paths:
        tree = ETree.parse(voc_path)
        root = tree.getroot()

        objects = root.findall('object')
        for object_el in objects:
            concept = object_el.find('name').text

            if concept not in concept_taxa_map:
                continue

            taxonomy = ETree.SubElement(object_el, 'taxonomy')
            for tax_rank, tax_name in concept_taxa_map[concept].items():
                tax_data_el = ETree.SubElement(taxonomy, tax_rank)
                tax_data_el.text = tax_name

        output_path = voc_path
        if output_dir is not None:
            output_path = os.path.join(output_dir, os.path.basename(voc_path))

        # Write out the XML
        with open(output_path, 'w') as f:
            f.write('\n'.join([
                line for line in minidom.parseString(
                    ETree.tostring(root, encoding='unicode')
                ).toprettyxml(indent=' '*4).splitlines()[1:]
                if line.strip()
            ]))


def main(input_dir: str, output_dir: Optional[str] = None):
    if not os.path.exists(input_dir) or not os.path.isdir(input_dir):
        print('[ERROR] Input directory {} does not exist'.format(input_dir))
        exit(1)

    if output_dir is not None and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        print('[INFO] Created output directory {}'.format(output_dir))

    voc_paths = glob.glob(os.path.join(input_dir, '*.xml'))

    print('[INFO] Found {} annotation XMLs'.format(len(voc_paths)))

    add_taxonomy(voc_paths, output_dir=output_dir)


if __name__ == '__main__':
    _parser = argparse.ArgumentParser(description=__doc__)
    _parser.add_argument('input_dir',
                         type=str,
                         help='Input directory of VOC annotation XMLs')
    _parser.add_argument('-o', '--output_dir',
                         type=str,
                         default=None,
                         help='(optional) Output directory for new annotations (if unspecified, original '
                              'annotation files will be overwritten)')
    _args = _parser.parse_args()
    main(_args.input_dir, _args.output_dir)
