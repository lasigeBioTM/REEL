import atexit
import logging
import obonet
import os
import networkx as nx
import pickle
import sys
import xml.etree.ElementTree as ET

from rapidfuzz import fuzz, process

sys.path.append("./")



# Import ChEBI cache storing the candidates list for each entity mention in corpus or create it if it does not exist

chebi_cache_file = "temp/chebi_cache.pickle"

if os.path.isfile(chebi_cache_file):
    logging.info("loading ChEBI dictionary...")
    chebi_cache = pickle.load(open(chebi_cache_file, "rb"))
    loadedchebi = True
    logging.info("loaded ChEBI dictionary with %s entries", str(len(chebi_cache)))
  
else:
    chebi_cache = {}
    loadedchebi = False
    logging.info("new ChEBI dictionary")


def exit_handler():
    print('Saving ChEBI dictionary...!')
    pickle.dump(chebi_cache, open(chebi_cache_file, "wb"))

atexit.register(exit_handler)



def load_chebi():
    """Load ChEBI ontology from local file 'chebi.obo' or from online source.
    
    Ensures: 
        ontology_graph: is a MultiDiGraph object from Networkx representing ChEBI ontology;
        name_to_id: is dict with mappings between each ontology concept name and the respective ChEBI id;
        synonym_to_id: is dict with mappings between each ontology concept name and the respective ChEBI id;
    """
    
    print("Loading ChEBI ontology...")
    
    graph = obonet.read_obo("chebi.obo") # Load the ontology from local file 

    # Add root concept to the graph
    root_concept = "CHEBI_00000"
    graph.add_node(root_concept, name="ROOT")
    graph = graph.to_directed()
    
    # Create mappings
    name_to_id, synonym_to_id, edge_list = {}, {}, []

    for node in  graph.nodes(data=True):
        
        node_id, node_name = node[0].replace(':', '_'), node[1]["name"]
        name_to_id[node_name] = node_id
        
        if 'is_a' in node[1].keys(): # The root node of the ontology does not have is_a relationships
                
            for related_node in node[1]['is_a']: # Build the edge_list with only "is-a" relationships
                relationship = (node_id, related_node.replace(':', '_'))
                edge_list.append(relationship) 
            
        if "synonym" in node[1].keys(): # Check for synonyms for node (if they exist)
                
            for synonym in node[1]["synonym"]:
                synonym_name = synonym.split("\"")[1]
                synonym_to_id[synonym_name] = node_id.replace(':', '_')
  
    # Create a MultiDiGraph object with only "is-a" relations - this will allow the further calculation of shorthest path lenght
    ontology_graph = nx.MultiDiGraph([edge for edge in edge_list])
    
    # Add edges between the ontology root and sub-ontology roots
    chemical_entity = "CHEBI_24431"
    role = "CHEBI_50906"
    subatomic_particle = "CHEBI_36342"
    application = "CHEBI_33232"
    ontology_graph.add_node(root_concept, name="ROOT")
    ontology_graph.add_edge(chemical_entity, root_concept, edgetype='is_a')
    ontology_graph.add_edge(role, root_concept, edgetype='is_a')
    ontology_graph.add_edge(subatomic_particle, root_concept, edgetype='is_a')
    ontology_graph.add_edge(application, root_concept, edgetype='is_a')

    #print("Is ontology_graph acyclic:", nx.is_directed_acyclic_graph(ontology_graph))
    print("ChEBI loading complete")
    
    return ontology_graph, name_to_id, synonym_to_id



def map_to_chebi(entity_text, name_to_id, synonym_to_id):
    """Get best ChEBI matches for entity text according to lexical similarity (edit distance).
    
    Requires: 
        entity_text: is (str) the surface form of given entity 
        name_to_id:  is dict with mappings between each ontology concept name and the respective ontology id
        synonym_to_id: is dict with mappings between each synonym for a given ontology concept and the respective ontology id

    Ensures: 
        matches: is list; each match is dict with the respective properties
    """
    
    global chebi_cache
    
    if entity_text in name_to_id or entity_text in synonym_to_id: # There is an exact match for this entity
        drugs = [entity_text]
    
    if entity_text.endswith("s") and entity_text[:-1] in chebi_cache: # Removal of suffix -s 
        drugs = chebi_cache[entity_text[:-1]]
    
    elif entity_text in chebi_cache: # There is already a candidate list stored in cache file
        drugs = chebi_cache[entity_text]

    else:
        # Get first ten MeSH candidates according to lexical similarity with entity_text
        drugs = process.extract(entity_text, name_to_id.keys(), scorer=fuzz.token_sort_ratio, limit=10)
        
        if drugs[0][1] == 100: # There is an exact match for this entity
            drugs = [drugs[0]]
    
        if drugs[0][1] < 70: # Check for synonyms to this entity
            drug_syns = process.extract(entity_text, synonym_to_id.keys(), limit=10, scorer=fuzz.token_sort_ratio)

            #print("best synonyms of ", entity_text, ":", drug_syns)
            for drug_syn in drug_syns:
                
                if drug_syn[1] > drugs[0][1]:
                    drugs.append(drug_syn)
        
        chebi_cache[entity_text] = drugs
    
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


