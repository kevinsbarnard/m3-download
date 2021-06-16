# voc_to_yolo.py (m3-download)
"""
Convert Pascal VOC annotation XMLs to YOLO format
"""
import argparse
import glob
import os
from typing import List
import xml.etree.ElementTree as ETree


def format_line(object_id, center_x, center_y, width, height):
    """ Format an output line for a YOLO annotation file """
    return '{} {} {} {} {}'.format(object_id, center_x, center_y, width, height)


def convert_voc_to_yolo(voc_paths: List[str], output_dir: str):
    """ Convert VOC annotations to YOLO and write to `output_dir` """
    names = {}  # Map of class names (written to yolo.names)

    for voc_path in voc_paths:
        lines = []

        tree = ETree.parse(voc_path)
        root = tree.getroot()

        # Get image size
        size = root.find('size')
        image_width = int(size.find('width').text)
        image_height = int(size.find('height').text)

        # Compute scaling values
        scale_x = 1 / image_width
        scale_y = 1 / image_height

        objects = root.findall('object')
        for loc in objects:
            # Get class label name and map index
            name = loc.find('name').text
            if name not in names:
                names[name] = len(names)
            name_idx = names[name]

            # Get box position and size
            box = loc.find('bndbox')
            x = float(box.find('xmin').text)
            y = float(box.find('ymin').text)
            width = float(box.find('xmax').text) - x
            height = float(box.find('ymax').text) - y

            # Compute scaled YOLO quantities
            scaled_center_x = (x + width / 2) * scale_x
            scaled_center_y = (y + height / 2) * scale_y
            scaled_width = width * scale_x
            scaled_height = height * scale_y

            lines.append(format_line(name_idx, scaled_center_x, scaled_center_y, scaled_width, scaled_height) + '\n')

        # Write to output
        output_path = os.path.join(output_dir, os.path.splitext(os.path.basename(voc_path))[0] + '.txt')
        with open(output_path, 'w') as f:
            f.writelines(lines)

    print('[INFO] Wrote {} output YOLO annotation files to {}'.format(len(voc_paths), output_dir))

    # Write class name map to yolo.names
    reverse_names = {idx: name for name, idx in names.items()}
    with open('yolo.names', 'w') as f:
        f.writelines([reverse_names[idx] + '\n' for idx in range(len(reverse_names))])

    print('[INFO] Wrote yolo.names')


def main(input_dirs: List[str], output_dir: str):
    # Check for existence of input directories
    valid_input_dirs = filter(os.path.exists, input_dirs)
    valid_input_dirs = list(filter(os.path.isdir, valid_input_dirs))
    for input_dir in input_dirs:
        if input_dir not in valid_input_dirs:
            print('[WARNING] Input directory {} does not exist, skipping'.format(input_dir))

    # Make the output directory, if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        print('[INFO] Created output directory {}'.format(output_dir))

    # Collect all VOC XML file paths in all directories
    voc_paths = []
    for input_dir in valid_input_dirs:
        xml_paths = glob.glob(os.path.join(input_dir, '*.xml'))
        voc_paths.extend(xml_paths)

    print('[INFO] Found {} annotation XMLs in {} directories'.format(len(voc_paths), len(valid_input_dirs)))

    # Convert and write
    convert_voc_to_yolo(voc_paths, output_dir)


if __name__ == '__main__':
    _parser = argparse.ArgumentParser(description=__doc__)
    _parser.add_argument('-o', '--output_dir',
                         type=str,
                         default='yolo_localizations',
                         help='Output directory for YOLO annotations')
    _parser.add_argument('input_dir',
                         nargs='+',
                         help='Input directory of VOC annotation XMLs')
    _args = _parser.parse_args()
    main(_args.input_dir, _args.output_dir)
