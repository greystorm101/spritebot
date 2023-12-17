

import re


def clean_pokemon_name(name:str):
    """Returns name with all non alphanumeric chars stripped and all lowercase"""
    return re.sub('[^A-Za-z0-9]+', '', name).lower()

