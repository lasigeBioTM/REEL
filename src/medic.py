import atexit
import logging
import obonet
import os
import networkx as nx
import pickle
import sys
import xml.etree.ElementTree as ET

from fuzzywuzzy import fuzz, process

sys.path.append("./")



# Import MEDIC cache storing the candidates list for each entity mention in corpus or create it if it does not exist

medic_cache_file = "temp/ctd_diseases_cache.pickle"

if os.path.isfile(medic_cache_file):
    logging.info("loading MEDIC dictionary...")
    medic_cache = pickle.load(open(medic_cache_file, "rb"))
    loadedmedic = True
    logging.info("loaded MEDIC dictionary with %s entries", str(len(medic_cache)))

else:
    medic_cache = {}
    loadedmedic = False
    logging.info("new MEDIC dictionary")


def exit_handler():
    print('Saving MEDIC dictionary...!')
    pickle.dump(medic_cache, open(medic_cache_file, "wb"))

atexit.register(exit_handler)



def load_medic():
    """Load MEDIC vocabulary from local file 'CTD_diseases.obo'.
    
    Ensures: 
        ontology_graph: is a MultiDiGraph object from Networkx representing the MEDIC vocabulary
        name_to_id: is dict with mappings between each ontology concept name and the respective MESH unique id
        synonym_to_id: is dict with mappings between each ontology concept name and the respective MESH unique id
    """
    
    print("Loading MEDIC ontology...")

    graph = obonet.read_obo("CTD_diseases.obo") # Load the ontology from local file 
    graph = graph.to_directed()
    
    # Create mappings
    name_to_id, synonym_to_id, edge_list = {}, {}, []

    for node in  graph.nodes(data=True):
        node_id, node_name = node[0][5:], node[1]["name"]
        
        if node_id == "C":
            node_id = "00000000000" # Node root "Diseases"

        name_to_id[node_name] = node_id
        
        if 'is_a' in node[1].keys(): # The root node of the ontology does not have is_a relationships with an ancestor
                
            for related_node in node[1]['is_a']: # Build the edge_list with only "is-a" relationships
                
                if related_node == "MESH:C":
                    relationship = (node_id, "00000000000")
                else:
                    relationship = (node_id, related_node[5:])
                
                edge_list.append(relationship) 
            
        if "synonym" in node[1].keys(): # Check for synonyms for node (if they exist)
                
            for synonym in node[1]["synonym"]:
                synonym_name = synonym.split("\"")[1]
                synonym_to_id[synonym_name] = node_id
            

    # Create a MultiDiGraph object with only "is-a" relations - this will allow the further calculation of shorthest path lenght
    ontology_graph = nx.MultiDiGraph([edge for edge in edge_list])
    
    print("Is ontology_graph acyclic:", nx.is_directed_acyclic_graph(ontology_graph))
    print("MEDIC loading complete")

    return ontology_graph, name_to_id, synonym_to_id



def map_to_medic(entity_text, name_to_id, synonym_to_id):
    """Get best MEDIC matches for entity text according to lexical similarity (edit distance).
    
    Requires: 
        entity_text: is (str) the surface form of given entity 
        name_to_id:  is dict with mappings between each ontology concept name and the respective ontology id
        synonym_to_id: is dict with mappings between each synonym for a given ontology concept and the respective ontology id

    Ensures: 
        matches: is list; each match is dict with the respective properties
    """
    
    global medic_cache
    
    if entity_text in name_to_id or entity_text in synonym_to_id: # There is an exact match for this entity
        drugs = [entity_text]
    
    if entity_text.endswith("s") and entity_text[:-1] in medic_cache: # Removal of suffix -s 
        drugs = medic_cache[entity_text[:-1]]
    
    elif entity_text in medic_cache: # There is already a candidate list stored in cache file
        drugs = medic_cache[entity_text]

    else:
        # Get first ten MeSH candidates according to lexical similarity with entity_text
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
        
        medic_cache[entity_text] = drugs
    
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


