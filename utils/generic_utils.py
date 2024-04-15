import json


class GenericUtils:

    @staticmethod
    def read_json(i_json_file):
        with open(i_json_file, "r") as json_file:
            data = json.load(json_file)
        return data

    @staticmethod
    def read_property(i_property_file):
        with open(i_property_file, "r") as prop_file:
            prop = prop_file.read()
        return prop
