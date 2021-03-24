# localization.py (m3-download)
import json
from uuid import UUID


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
        return [self.x, self.y, self.width, self.height]

    @property
    def xmax(self):
        return self.x + self.width

    @property
    def ymax(self):
        return self.y + self.height

    @property
    def points_min(self):
        return [self.x, self.y]

    @property
    def points_max(self):
        return [self.xmax, self.ymax]


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
