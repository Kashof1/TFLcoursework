import logging
import json 
import csv

class DatabaseHandler:
    def __init__(self, filename: str):
        self.destinationfile = filename

    def write(self, contents):
        with open (self.destinationfile, 'a') as file:
            file.write(f'{contents}\n')
