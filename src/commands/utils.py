import argparse
import json
import re
import os

JSON_FILE = os.path.join(os.path.dirname(os.getcwd()), "data", "NamesToNumbers.json" ) 

def raw_pokemon_name_to_id(name:str):
    """
    Takes in raw pokemon name from user input and returns id number.
    """
    clean_name = clean_pokemon_name(name)
    name_to_id_map = names_and_typos_to_id_map()
    return name_to_id_map[clean_name]

def clean_pokemon_name(name:str):
    """Returns name with all non alphanumeric chars stripped and all lowercase"""
    return re.sub('[^A-Za-z0-9]+', '', name).lower()

def name_to_id_map():
    """Returns dictionary mapping names to id numbers"""
    with open(JSON_FILE) as f:
        data = json.loads(f.read())
        return {element["name"]:element["id"] for element in data["pokemon"]}

def id_to_name_map():
    """Returns dictionary mapping id numbers to display names"""
    with open(JSON_FILE) as f:
        data = json.loads(f.read())
        return {element["id"]:element["display_name"] for element in data["pokemon"]}

def names_and_typos_to_id_map():
    """Returns dictionary mapping names """
    with open(JSON_FILE) as f:
        input_data = json.loads(f.read())

        return {name: data["id"]
                for data in input_data["pokemon"] 
                for name in [data['name'], *data['typos']] }
    
        
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("pokename")
    args = parser.parse_args()
    
    pokemon_name = args.pokename
    pokemon_id = raw_pokemon_name_to_id(pokemon_name)
    display_name = id_to_name_map()[pokemon_id]

    print("Input: {} Output: {}".format(pokemon_name, display_name))

