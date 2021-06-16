# count_localizations.py (m3-download)
"""
Count localizations per concept in a directory of Pascal VOC annotation XMLs
"""

import os
import glob
import argparse
import xml.etree.ElementTree as ETree


class BoundingBox:
    """ Simple bounding box class """
    __slots__ = ['x', 'y', 'w', 'h', 'concept']

    def __init__(self, x: int, y: int,
                 w: int = None, h: int = None,
                 x_max: int = None, y_max: int = None,
                 concept=''):
        self.x = x
        self.y = y
        if w and h:
            self.w = w
            self.h = h
        else:
            self.w = x_max - x
            self.h = y_max - y
        self.concept = concept

    def __iter__(self):
        yield self.x
        yield self.y
        yield self.w
        yield self.h

    @property
    def corners(self):
        """ Returns the box in corner format """
        return self.x, self.y, self.x + self.w, self.y + self.h

    @property
    def json(self):
        """ Returns a JSON dict representation of the box """
        return {
            'x': self.x,
            'y': self.y,
            'width': self.w,
            'height': self.h
        }


class RectLabelXML:
    """ RectLabel XML parser """
    def __init__(self, path: str):
        self.path = path
        self.root = None
        self.load()

    def load(self):
        tree = ETree.parse(self.path)
        self.root = tree.getroot()

    def get_objects(self):
        return self.root.findall('object')

    def get_filename(self):
        return self.root.find('filename').text

    def read_boxes(self):
        for obj in self.get_objects():
            concept = obj.find('name').text
            bndbox = obj.find('bndbox')
            x_min = int(bndbox.find('xmin').text)
            y_min = int(bndbox.find('ymin').text)
            x_max = int(bndbox.find('xmax').text)
            y_max = int(bndbox.find('ymax').text)
            yield BoundingBox(x_min, y_min, x_max=x_max, y_max=y_max, concept=concept)


def count_localizations(directory):
    xml_files = glob.glob(os.path.join(directory, '*.xml'))

    concept_map = dict()
    for xml_file in xml_files:
        try:
            rl_xml = RectLabelXML(xml_file)
            for box in rl_xml.read_boxes():
                if box.concept not in concept_map:
                    concept_map[box.concept] = []
                concept_map[box.concept].append(box)
        except Exception as e:
            print(e)

    return concept_map


def main(directory, csv=False, show_total=False):
    if not os.path.isdir(directory):
        raise Exception('{} is not a valid directory'.format(directory))

    concept_map = count_localizations(directory)

    output_format = '{:<40} : {:>5}' if not csv else '{},{}'

    total = 0
    for concept in sorted(concept_map):
        print(output_format.format(concept, len(concept_map[concept])))
        total += len(concept_map[concept])
    if show_total:
        print(output_format.format('TOTAL', total))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', help='Localization directory')
    parser.add_argument('-c', '--csv', action='store_true', help='CSV-formatted output')
    parser.add_argument('-t', '--total', action='store_true', help='Append total of all counts in output')
    args = parser.parse_args()

    main(args.directory, args.csv, args.total)
