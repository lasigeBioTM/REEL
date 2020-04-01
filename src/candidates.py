import networkx as nx

from chebi import map_to_chebi
from ctd_chemicals import map_to_ctd_chemicals
from fuzzywuzzy import fuzz, process
from medic import map_to_medic
from strings import candidate_string



def write_candidates(entity_list, candidates_filename, entity_type, ontology_graph, link_mode, extracted_relations):
    """Write the entities and respective candidates of one corpus document to a distinct file.
    
    Requires: 
        entity_list: is dict of entities in doc, values are the candidates of each entity 
        candidates_filename: is str with the output file name 
        entity_type: is str, either "Chemical" or "Diseases
        ontology_graph: is a MultiDiGraph object from Networkx representing the specified ontology
        link_mode: is str specifying how the edges in disambiguation graph are built ('kb_link', 'corpus_link', 'kb_corpus_link')
        extracted_relations: is dict, keys are entities ids and values are the ids of related entities 
    
    Ensures: 
        entities_used: (int) number of entities with at least one candidate and that were included in the candidates file
    """
    
    entities_used = int() # entitites with at least one candidate
    candidates_links = dict() # (url: links)
    candidates_file = open(candidates_filename, 'w')
    
    for e in entity_list:
    
        if len(entity_list[e]) > 0:
            entity_str = entity_list[e][0]
            candidates_file.write(entity_str)
            entities_used += 1
        
        for ic, c in enumerate(entity_list[e][1:]): # iterate over the candidates for current entity
            
            if c["url"] in candidates_links:
                c["links"] = candidates_links[c["url"]]
    
            else: 
                links, other_candidates = [], []
                    
                for e2 in entity_list: # Iterate over candidates for every other entity except current one
                    
                    if e2 != e:
                        
                        for ic2, c2 in enumerate(entity_list[e2][1:]):
                            other_candidates.append((c2["url"], c2["id"]))
    
                for c2 in other_candidates: # calculate distance between two candidates according to link_mode
                    c1 = c["url"]
                    relation_string_1 = c1 + "_" + c2[0]
                    relation_string_2 = c2[0] + "_" + c1
                    
                    if link_mode == "corpus_link":
                       
                        if c1 in extracted_relations.keys():
                            relations_with_c1 = extracted_relations[c1]
                            
                            if c2[0] in relations_with_c1: # There is an extracted relation between the two candidates
                                links.append(str(c2[1]))

                    else:

                        if c1 == c2[0] or relation_string_1 in ontology_graph.edges() or relation_string_2 in ontology_graph.edges(): 
                            candidates_linked = True
                        
                        else:
                            candidates_linked = False
                            
                        if candidates_linked: # The two candidates are linked in the ontology
                            links.append(str(c2[1]))
                            
                        else:
                            
                            if link_mode == "kb_link": # There is no relation between the candidates
                                continue
                            
                            elif link_mode == "kb_corpus_link": # Maybe there is an extracted relation between the candidates
                                
                                if c1 in extracted_relations.keys():
                                    relations_with_c1 = extracted_relations[c1]
                            
                                    if c2[0] in relations_with_c1: # There is an extracted relation between the two candidates
                                        links.append(str(c2[1]))

                c["links"] = ";".join(set(links))
                candidates_links[c["url"]] = c["links"][:]

            candidates_file.write(candidate_string.format(c["id"], c["incount"],
                                                          c["outcount"], c["links"],
                                                          c["url"], c["name"], c["name"].lower(), c["name"].lower(), entity_type))
    
    candidates_file.close()
    
    return entities_used



def update_entity_list(entity_list, solution_found, normalized_text, solution_label_matches_entity):
    """ Put the correct candidate in the first position of the candidates list."""

    updated_list, entity_perfect_matches = list(), list()
    correct = entity_list[solution_found]
    
    del entity_list[solution_found]
    
    if entity_perfect_matches: # There are perfect matches for this entity (some label lowercased)
    
        if solution_label_matches_entity:
            updated_list = [correct] + [e for e in entity_perfect_matches[:] if e != correct]
    
    else:
        updated_list = [correct] + entity_list
    
    return updated_list



def generate_candidates_for_entity(entity_text, entity_id, ontology_name, name_to_id, synonym_to_id, min_match_score, ontology_graph):
    """Get the structured candidates list for given entity.
    
    Requires: 
        entity_text: (str) the surface form of given entity; 
        entity_id: is str with the ontology id corresponding to the correct disambiguation for given entity 
        ontology_name: is str specifying the target ontology to which the entity disambiguation will be made
        name_to_id:  is dict with mappings between each ontology concept name and the respective ontology id
        synonym_to_id: is dict with mappings between each synonym for a given ontology concept and the respective ontology id
        min_match_score: is float that represents lexical similarity or edit distance between entity_text and candidate string,
                candidates below this threshold are excluded from candidates list
        ontology_graph: is a MultiDiGraph object from Networkx representing the specified ontology
    
    Ensures: 
        structured_candidates: is list containing all valid candidates for given entity and the respective properties (each 
                candidate is a dict)
        solution_found: is bool with value True if the correct disambiguation for entity_text is in the candidates list
    """

    ncandidates, structured_candidates  = list(), list()
    less_than_min_score = int()
    
    # First step is to retrieve best ontology candidates names and respective ontology ids
    if ontology_name == "chebi":
        candidate_names = map_to_chebi(entity_text, name_to_id, synonym_to_id)
    
    elif ontology_name == "medic":
        candidate_names = map_to_medic(entity_text, name_to_id, synonym_to_id)
    
    elif ontology_name == "ctd_chemicals":
        candidate_names = map_to_ctd_chemicals(entity_text, name_to_id, synonym_to_id)

    else:
        raise Exception("Invalid target ontology, valid inputs: 'chebi', 'medic' or 'ctd_chemicals'")
    
    # Get properties for each retrieved candidate 
    solution_found, match_nils = -1, 0
    solution_label_matches_entity = False
    
    for i, candidate_match in enumerate(candidate_names): 
    
        if candidate_match["ontology_id"] == "NIL":
            match_nils += 1
            continue
    
        if candidate_match["match_score"] > min_match_score and candidate_match["ontology_id"] != "NIL":
            outcount = ontology_graph.out_degree(candidate_match["ontology_id"])
            incount = ontology_graph.in_degree(candidate_match["ontology_id"])
            candidate_id = str()
            
            if ontology_name == "medic" or ontology_name == "ctd_chemicals":
                candidate_id = candidate_match["ontology_id"]
                
                if len(candidate_id)>1:

                    if candidate_id[:1] == "D" or candidate_id[:1] == "C":
                        candidate_id = int(candidate_id[1:])

                    else:
                        candidate_id = int(candidate_id)
                
                elif len(candidate_id) == 1:

                    if candidate_id == "D":
                        candidate_id = "0000"

            elif ontology_name == "chebi":
                candidate_id = int(candidate_match["ontology_id"].split(":")[1])
            
            # The first candidate in candidate_names should be the correct solution
            structured_candidates.append({"url": candidate_match["ontology_id"], "name": candidate_match["name"],
                                             "outcount": outcount, "incount": incount,
                                             "id": candidate_id, "links": [],
                                             "score": candidate_match["match_score"]})
        
            if entity_id == candidate_match["ontology_id"]:
                solution_found = i - match_nils - less_than_min_score

                if entity_text == candidate_match["name"]:
                    solution_label_matches_entity = True
            
        else:
            less_than_min_score += 1

    if solution_found > -1:
        # update entity list to put the correct answer as first and if there are any perfect matches,
        structured_candidates = update_entity_list(structured_candidates, solution_found, entity_text, solution_label_matches_entity)

        if structured_candidates:
            ncandidates.append(len(structured_candidates))
    
    else:
        structured_candidates = []
    
    return structured_candidates, solution_found == 0
