# config.py (m3-download)

import configparser


class Config:
    def __init__(self, path: str):
        self.path = path
        self.parser = configparser.ConfigParser()
        self.parser.read(path)

    def __call__(self, *args, **kwargs):
        assert len(args) == 2
        return self.parser.get(args[0], args[1])
