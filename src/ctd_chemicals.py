import atexit
import csv
import logging
import os
import networkx as nx
import pickle
import sys

from rapidfuzz import fuzz, process

sys.path.append("./")


# Import CTD-Chemicals vocabulary cache storing the candidates list for each entity mention in corpus or create it if it does not exist

ctd_chem_cache_file = "temp/ctd_chemicals_cache.pickle"

if os.path.isfile(ctd_chem_cache_file):
    logging.info("loading Chemical vocabulary dictionary...")
    ctd_chem_cache = pickle.load(open(ctd_chem_cache_file, "rb"))
    loaded_ctdchem = True
    logging.info("loaded Chemical dictionary with %s entries", str(len(ctd_chem_cache)))

else:
    ctd_chem_cache = {}
    loaded_ctd_chem = False
    logging.info("new Chemical vocabulary dictionary")


def exit_handler():
    print('Saving Chemical vocabulary dictionary...!')
    pickle.dump(ctd_chem_cache, open(ctd_chem_cache_file, "wb"))

atexit.register(exit_handler)



def load_ctd_chemicals():
    """Load CTD_chemicals vocabulary from local 'CTD_chemicals.tsv' file
    
    Ensures: 
        ontology_graph: is a MultiDiGraph object from Networkx representing the CTD Chemicals vocabulary;
        name_to_id: is dict with mappings between each ontology concept name and the respective MESH unique id;
        synonym_to_id: is dict with mappings between each ontology concept name and the respective MESH unique id;
    """

    print("Loading Chemical vocabulary..")

    name_to_id, synonym_to_id, edge_list = {}, {},[]

    with open("CTD_chemicals.tsv") as ctd_chem:
        reader = csv.reader(ctd_chem, delimiter="\t")
        row_count = int()
        
        for row in reader:
            row_count += 1
            
            if row_count >= 30:
                chemical_name = row[0] 
                chemical_id = row[1][5:]
                chemical_parents = row[4].split('|')
                synonyms = row[7].split('|')
                name_to_id[chemical_name] = chemical_id
                
                for parent in chemical_parents:
                    relationship = (chemical_id, parent[5:])
                    edge_list.append(relationship)
                
                for synonym in synonyms:
                    synonym_to_id[synonym] = chemical_id

    # Create a MultiDiGraph object with only "is-a" relations - this will allow the further calculation of shorthest path lenght
    ontology_graph = nx.MultiDiGraph([edge for edge in edge_list])
    #print("Is ontology_graph acyclic:", nx.is_directed_acyclic_graph(ontology_graph))
    print("Loading complete")
    
    return ontology_graph, name_to_id, synonym_to_id



def map_to_ctd_chemicals(entity_text, name_to_id, synonym_to_id):
    """Get best ctd_chemicals matches for entity text according to lexical similarity (edit distance).
    
    Requires: 
        entity_text: is (str) the surface form of given entity
        name_to_id:  is dict with mappings between each ontology concept name and the respective ontology id
        synonym_to_id: is dict with mappings between each synonym for a given ontology concept and the respective ontology id

    Ensures: 
        matches: is list; each match is dict with the respective properties
    """
    
    global ctd_chem_cache
    
    if entity_text in name_to_id or entity_text in synonym_to_id: # There is an exact match for this entity
        drugs = [entity_text]
    
    if entity_text.endswith("s") and entity_text[:-1] in ctd_chem_cache: # Removal of suffix -s 
        drugs = ctd_chem_cache[entity_text[:-1]]
    
    elif entity_text in ctd_chem_cache: # There is already a candidate list stored in cache file
        drugs = ctd_chem_cache[entity_text]

    else:
        # Get first ten candidates according to lexical similarity with entity_text
        drugs = process.extract(entity_text, name_to_id.keys(), scorer=fuzz.token_sort_ratio, limit=10)
        
        if drugs[0][1] == 100: # There is an exact match for this entity
            drugs = [drugs[0]]
    
        elif drugs[0][1] < 100: # Check for synonyms to this entity
            drug_syns = process.extract(entity_text, synonym_to_id.keys(), limit=10, scorer=fuzz.token_sort_ratio)

            for synonym in drug_syns:

                if synonym[1] == 100:
                    drugs = [synonym]
                
                else:
                    if synonym[1] > drugs[0][1]:
                        drugs.append(synonym)
        
        ctd_chem_cache[entity_text] = drugs
    
    # Build the candidates list with each match id, name and matching score with entity_text
    matches = []
    
    for d in drugs:
        
        term_name = d[0]
        
        if term_name in name_to_id.keys():
            term_id = name_to_id[term_name]
        
        elif term_name in synonym_to_id.keys():
            term_id = synonym_to_id[term_name]
        
        else:
            term_id = "NIL"

        match = {"ontology_id": term_id,
                 "name": term_name,
                 "match_score": d[1]/100}
    
        matches.append(match)
  
    return matches

