# localization.py (m3-download)
import json
import os
from typing import List, Optional, Tuple
from uuid import UUID
import xml.etree.ElementTree as ETree
from xml.dom import minidom
from PIL import Image


class Localization:
    __slots__ = ['x', 'y', 'width', 'height']

    def __init__(self, x: int, y: int, width: int, height: int):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    @property
    def area(self):
        return self.width * self.height

    @property
    def box(self):
        return self.x, self.y, self.width, self.height

    @property
    def xmax(self):
        return self.x + self.width

    @property
    def ymax(self):
        return self.y + self.height

    @property
    def points_min(self):
        return self.x, self.y

    @property
    def points_max(self):
        return self.xmax, self.ymax

    @property
    def points(self):
        return self.points_min + self.points_max


class COCO:
    INFO_ATTRIBUTES = [
        'year',
        'version',
        'description',
        'contributor',
        'url',
        'date_created'
    ]
    IMAGE_ATTRIBUTES = [
        'id',
        'width',
        'height',
        'file_name',
        'license',
        'flickr_url',
        'coco_url',
        'date_captured'
    ]
    LICENSE_ATTRIBUTES = [
        'id',
        'name',
        'url'
    ]

    class Annotation:
        ATTRIBUTES = [
            'id',
            'image_id',
            'category_id',
            'segmentation',
            'iscrowd'
        ]

        def __init__(self, localization: Localization, **kwargs):
            for attrib in COCO.Annotation.ATTRIBUTES:
                if attrib in kwargs:
                    self.__setattr__(attrib, kwargs[attrib])

            self.localization = localization

        @property
        def json(self):
            return {
                'bbox': self.localization.box,
                'area': self.localization.area,
                **self.meta
            }

        @property
        def meta(self):
            return {
                k: self.__getattribute__(k)
                for k in COCO.Annotation.ATTRIBUTES
                if k in self.__dict__
            }

    def __init__(self,
                 images: list = None,
                 licenses: list = None,
                 categories: list = None,
                 **kwargs):
        self.images = []
        if images:
            for image_info in images:
                self.add_image(image_info)

        self.licenses = []
        if licenses:
            for license_info in licenses:
                self.add_license(license_info)

        self.annotations = []

        self.category_map = {}
        self.categories = []
        for idx, category in enumerate(categories):
            self.category_map[category] = idx
            self.categories.append({
                'id': idx,
                'name': category
            })

        for attrib in COCO.INFO_ATTRIBUTES:
            if attrib in kwargs:
                self.__setattr__(attrib, kwargs[attrib])

    @property
    def info(self):
        return {
            k: self.__getattribute__(k)
            for k in COCO.INFO_ATTRIBUTES
            if k in self.__dict__
        }

    def add_image(self, image_info: dict):
        self.images.append({
            k: image_info[k]
            for k in COCO.IMAGE_ATTRIBUTES
            if k in image_info
        })

    def add_license(self, license_info: dict):
        self.images.append({
            k: license_info[k]
            for k in COCO.LICENSE_ATTRIBUTES
            if k in license_info
        })

    def add_annotation(self, ann: dict):
        loc = ann['localization']

        localization = Localization(loc['x'], loc['y'], loc['width'], loc['height'])

        self.annotations.append(COCO.Annotation(localization,
                                                id=UUID(ann['association_uuid']).int,
                                                image_id=UUID(loc['image_reference_uuid']).int,
                                                category_id=self.category_map[ann['concept']]))

    @property
    def json(self):
        return {
            'info': self.info,
            'images': self.images,
            'annotations': [ann.json for ann in self.annotations],
            'categories': self.categories,
            'licenses': self.licenses
        }

    def write(self, path):
        with open(path, 'w') as f:
            json.dump(self.json, f, indent=2)


class PascalVOC:
    """ Pascal Visual Object Classes (VOC) """

    class Annotation:
        def __init__(self, folder: str, filename: str, size: tuple,
                     localizations: Optional[List[Tuple[str, Localization]]] = None):
            self._folder = folder
            self._filename = filename

            self._width = 0
            self._height = 0
            self._depth = 1

            self.size = size

            self._localizations: List[Tuple[str, Localization]] = []
            if localizations:
                for name, loc in localizations:
                    self.add(name, loc)

        def add(self, name: str, localization: Localization):
            self._localizations.append((name, localization))

        def clear(self):
            self._localizations.clear()

        def __getitem__(self, item):
            return self._localizations[item]

        @property
        def filename(self):
            return self._filename

        @property
        def size(self):
            return self._height, self._width, self._depth

        @size.setter
        def size(self, value: tuple):
            if len(value) < 2 or len(value) > 3:
                raise ValueError(f'Bad number of dimensions in size tuple {value}.')

            self._height, self._width, *ext = value  # Unpack

            if ext:  # Handle depth
                self._depth = ext[0]

        @property
        def xml(self) -> str:
            annotation = ETree.Element('annotation')  # Root

            # Meta
            folder = ETree.SubElement(annotation, 'folder')
            folder.text = self._folder
            filename = ETree.SubElement(annotation, 'filename')
            filename.text = self._filename

            # Size
            size = ETree.SubElement(annotation, 'size')
            width = ETree.SubElement(size, 'width')
            width.text = str(self._width)
            height = ETree.SubElement(size, 'height')
            height.text = str(self._height)
            depth = ETree.SubElement(size, 'depth')
            depth.text = str(self._depth)

            # Localizations
            for name, loc in self._localizations:
                loc_object = ETree.SubElement(annotation, 'object')

                loc_name = ETree.SubElement(loc_object, 'name')
                loc_name.text = name

                bndbox = ETree.SubElement(loc_object, 'bndbox')
                xmin = ETree.SubElement(bndbox, 'xmin')
                ymin = ETree.SubElement(bndbox, 'ymin')
                xmax = ETree.SubElement(bndbox, 'xmax')
                ymax = ETree.SubElement(bndbox, 'ymax')

                xmin.text, ymin.text, xmax.text, ymax.text = tuple(map(str, loc.points))

            return ETree.tostring(annotation, encoding='unicode')

    def __init__(self):
        self.annotations: List[PascalVOC.Annotation] = []

    def add_annotation(self, image_reference_uuid: str, anns: List[dict], image_map: dict):
        if not anns:
            return

        if image_reference_uuid in image_map:
            filename = image_map[image_reference_uuid]
        else:
            raise ValueError(f'No image found for image reference UUID {image_reference_uuid}')

        names = []
        localizations = []
        for ann in anns:
            loc = ann['localization']
            names.append(ann['concept'])
            localizations.append(Localization(loc['x'], loc['y'], loc['width'], loc['height']))

        if not os.path.exists(filename):
            print('[WARNING] No image found at {}, skipping'.format(filename))
            return

        with Image.open(filename) as im:
            width, height = im.size
            depth = len(im.getbands())

        annotation = PascalVOC.Annotation(
            os.path.dirname(filename),
            os.path.basename(filename),
            (height, width, depth),
            list(zip(names, localizations))
        )

        self.annotations.append(annotation)

    def write(self, dirpath, form):
        os.makedirs(dirpath, exist_ok=True)  # Make directory if doesn't exist

        for annotation in self.annotations:
            with open(os.path.join(dirpath, form.format(os.path.splitext(annotation.filename)[0])), 'w') as f:
                f.write('\n'.join(minidom.parseString(annotation.xml).toprettyxml(indent=' '*4).splitlines()[1:]))
