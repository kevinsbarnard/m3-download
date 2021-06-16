# m3-download
Quick scripts for downloading localizations and images via M3

_Author: Kevin Barnard_

## Dependencies
PIP packages:

- `requests`
- `pillow`

To install all dependencies:
```bash
pip install requests pillow
```

---

## Usage

### 1. Generate observation digests
An observation digest is simply a JSON list of observations as supplied by M3. To get this for a specific concept, use `generate_digest.py`:
```
usage: generate_digest.py [-h] [-c CONFIG] [-d] [-a] concept

Look up observations (with a valid image) for a given concept and generate a digest

positional arguments:
  concept               VARS concept

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        Config path
  -d, --descendants     Flag to include descendants in digest
  -a, --all             Flag to include all other observations for each imaged moment in digest
```

This will write a file `[concept]_digest.json` with the corresponding observations with valid images.

#### Example:
```bash
python generate_digest.py -d 'Sebastes'
```

### 2. Extracting localizations
The next step is to extract and reformat the localizations using `extract_localizations.py`:
```
usage: extract_localizations.py [-h] digest [digest ...]

Extract localizations from a digest (see generate_digest.py) and format them nicely

positional arguments:
  digest      Path to the digest JSON

optional arguments:
  -h, --help  show this help message and exit
```

__Any number of observation digest JSONs can be supplied.__ This will create `localizations.json`, a reformatted JSON list of all localizations and some associated metadata.

#### Example:
```bash
python extract_localizations.py /Users/lonny/Desktop/m3-download-main/Sebastes_desc_digest.json
```

### 3. Download images
Now, we can download the images corresponding to the localizations in our JSON list using `download_images.py`:
```
usage: download_images.py [-h] [-j JOBS] [-c CONFIG] [-o] localizations output_dir

Download images corresponding to localizations

positional arguments:
  localizations         Path to JSON list of localizations
  output_dir            Output directory

optional arguments:
  -h, --help            show this help message and exit
  -j JOBS, --jobs JOBS  Number of multiprocessing jobs to use (default=1)
  -c CONFIG, --config CONFIG
                        Config path
  -o, --overwrite       Overwrite existing images
```

If you want to use multiprocessing (default is none), specify the `-j` option with a number of workers.

Image overwrite is false by default to account for any program/network failures. Specify the `-o` flag to overwrite images if desired.

A JSON mapping from image reference UUID to the image file path will be written to `image_map.json`. 
This is useful for back-referencing images in VARS and becomes necessary when performing VOC formatting (see `reformat.py`).

In case any images fail to download, their URLs will be written to `failures.csv`.

#### Example:
```bash
python download_images.py /Users/lonny/Desktop/m3-download-main/localizations.json /Users/lonny/Desktop/Sebastes/
```

### 4. Reformat localizations
Localization reformatting is done through `reformat.py`:
```
usage: reformat.py [-h] [-o OUTPUT] [-f FORMAT] [--image_map IMAGE_MAP] localizations

Reformat a localization file to a desired format

positional arguments:
  localizations         Path to localizations JSON file (see extract_localizations.py)

optional arguments:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        Output file name, omitting the extension (dependent on format)
  -f FORMAT, --format FORMAT
                        Localization format to write. Options: CSV, COCO, VOC, TF
  --image_map IMAGE_MAP
                        Image filename map for VOC formatting (see download_images.py)
```

#### Example:
```bash
python reformat.py \
    -o ~/Desktop/reformat \
    -f VOC \
    --image_map image_map.json \
    /Users/lonny/Desktop/m3-download-main/localizations.json
```

_Note for VOC formatting:_ The `--image_map` argument must be specified (see `download_images.py`).
This file should be a mapping from image reference UUID to the downloaded image path.

---

## Utility scripts (in `scripts/`)

### `voc_to_yolo.py`: convert Pascal VOC to YOLO
`voc_to_yolo.py` accepts any number of input directories containing Pascal VOC annotation XMLs, converts them to YOLO annotations, and writes them to a specified output directory.
```
usage: voc_to_yolo.py [-h] [-o OUTPUT_DIR] input_dir [input_dir ...]

Convert Pascal VOC annotation XMLs to YOLO format

positional arguments:
  input_dir             Input directory of VOC annotation XMLs

optional arguments:
  -h, --help            show this help message and exit
  -o OUTPUT_DIR, --output_dir OUTPUT_DIR
                        Output directory for YOLO annotations
```

The class label names file `yolo.names` will be written to the working directory.

#### Example:
```bash
python voc_to_yolo.py -o Sebastes_yolo/ Sebastes_voc_1/ Sebastes_voc_2/
```

### `count_localizations.py`: count localizations in Pascal VOC annotations
`count_localizations.py` counts the number of localizations per concept in a directory of Pascal VOC annotation XMLs.
```
usage: count_localizations.py [-h] [-c] [-t] directory

positional arguments:
  directory    Localization directory

optional arguments:
  -h, --help   show this help message and exit
  -c, --csv    CSV-formatted output
  -t, --total  Append total of all counts in output
```

### `remap_voc.py`: remap concepts in Pascal VOC annotations
`remap_voc.py` performs a bulk remapping on a directory of Pascal VOC annotation XMLs as specified by a remapping file. The remapping file may be a CSV (`.csv`) or JSON (`.json`) as specified:

- __CSV__ remapping files consist of one remapping per line. The current concept should be in the first column, and the new concept should be in the second column. Example:
```text
LRJ complex,Benthocodon
Benthocodon pedunculata,Benthocodon
Peniagone sp. A,Peniagone
Peniagone sp. 2,Peniagone
Peniagone sp. 1,Peniagone
Peniagone vitrea,Peniagone
Peniagone vitrea- sp. 1 complex,Peniagone
Peniagone papillata,Peniagone
Scotoplanes sp. A,Scotoplanes
Scotoplanes clarki,Scotoplanes
Scotoplanes globosa,Scotoplanes
```
- __JSON__ remapping files consist of the literal map as a JSON object. Example:
```json
{
  "LRJ complex": "Benthocodon",
  "Benthocodon pedunculata": "Benthocodon",
  "Peniagone sp. A": "Peniagone",
  "Peniagone sp. 2": "Peniagone",
  "Peniagone sp. 1": "Peniagone",
  "Peniagone vitrea": "Peniagone",
  "Peniagone vitrea- sp. 1 complex": "Peniagone",
  "Peniagone papillata": "Peniagone",
  "Scotoplanes sp. A": "Scotoplanes",
  "Scotoplanes clarki": "Scotoplanes",
  "Scotoplanes globosa": "Scotoplanes"
}
```

```
usage: remap_voc.py [-h] [-o OUTPUT_DIR] map_file input_dir

Remap concepts in a directory of Pascal VOC annotation XMLs

positional arguments:
  map_file              File (.csv or .json) containing remapping
  input_dir             Input directory of VOC annotation XMLs

optional arguments:
  -h, --help            show this help message and exit
  -o OUTPUT_DIR, --output_dir OUTPUT_DIR
                        (optional) Output directory for remapped annotations (if unspecified, original annotation files will be overwritten)
```

_Note:_ If the `--output_dir` option is unspecified, __the original annotation files will be overwritten.__

#### Example:
```bash
python remap_voc.py -o Benthocodon_remapped/ remapping.csv Benthocodon/
```