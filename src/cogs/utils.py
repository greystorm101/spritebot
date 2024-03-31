import argparse
import json
import re
import os



JSON_FILE = os.path.join(os.getcwd(), "src", "data", "NamesToNumbers.json" ) 
MULTI_NAME_FILE = os.path.join(os.path.dirname(os.getcwd()), "data", "MultiWordNames.json" ) 

def raw_pokemon_name_to_id(name:str):
    """
    Takes in raw pokemon name from user input and returns id number.
    """
    clean_name = clean_pokemon_string(name)
    name_to_id_map = names_and_typos_to_id_map()

    id = None
    try:
        id = name_to_id_map[clean_name]
    except KeyError:
        pass 
    return id

def clean_pokemon_string(name:str):
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
    
def multi_word_name_list():
    """Returns list of names potentially seperated by spaces """
    with open(MULTI_NAME_FILE) as f:
        input_data = json.loads(f.read())

        return input_data

def fusion_is_valid(id: str):   
    """Returns true if the id number is a valid fusion, false otherwise"""
    valid_ids_map = id_to_name_map()
    # Handle legacy images that have ultra necrozma as 450_1
    valid_ids_map["450_1"] = "Ultra Necrozma"
    return id in valid_ids_map.keys()

def print_typo_list():
    with open(JSON_FILE) as f:
        data = json.loads(f.read())
        typos_list = [item["display_name"]+ ": "+ str(item["typos"]) for item in data["pokemon"]]
        for poke in typos_list:
            print(poke)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("pokename")
    args = parser.parse_args()
    
    pokemon_name = args.pokename
    pokemon_id = raw_pokemon_name_to_id(pokemon_name)
    display_name = id_to_name_map()[pokemon_id]
    print("Input: {} Output: {}".format(pokemon_name, display_name))
    

