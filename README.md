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
```
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
```
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
```
python download_images.py /Users/lonny/Desktop/m3-download-main/localizations.json ~/Desktop/Sebastes/
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
```
python reformat.py \
    -o ~/Desktop/reformat \
    -f VOC \
    --image_map image_map.json \
    /Users/lonny/Desktop/m3-download-main/localizations.json
```

_Note for VOC formatting:_ The `--image_map` argument must be specified (see `download_images.py`).
This file should be a mapping from image reference UUID to the downloaded image path.
