import os
import sys
import time
import xml.etree.ElementTree as ET

from chebi import load_chebi
from medic import load_medic
from ctd_chemicals import load_ctd_chemicals
from annotations import parse_craft_chebi_annotations, parse_cdr_annotations_pubtator
from candidates import write_candidates, generate_candidates_for_entity
from information_content import generate_ic_file
from relations import import_bolstm_output, import_cdr_relations_pubtator
from strings import entity_string

sys.path.append("./")



def build_entity_candidate_dict(ontology, annotations, min_match_score, ontology_graph, name_to_id, synonym_to_id):
    """Builds the dict with candidates for all entity mentions in all corpus documents.
    
    Requires: 
        ontology: is str, either "medic", "chebi" or "ctd_chemicals"
        annotations: is dict, each key is a document name, value is a list containing all annotations in document (in tuple format)
        min_match_score: is float that represents minimum edit distance between the mention text and candidate string, 
            candidates below this threshold are excluded from candidates list
        ontology_graph: is a MultiDiGraph object from Networkx representing the ontology
        name_to_id: is dict with mappings between each ontology concept name and the respective id
        synonym_to_id: is dict with mappings between each synonym for a given ontology concept and the respective id
    
    Ensures: 
        documents_entity_list: is dict, for each document in corpus there is a dict (entity_dict) with each entity mention
            and respective ontology candidates
        statistics: is str, contains several statistics associated with the corpus characteristics and disambiguation accuracy
            of the baseline model
    """

    doc_count, nil_count, total_entities, total_unique_entities, no_solution, solution_is_first_count = int(), int(),int(), int(), int(), int()
    
    documents_entity_list = dict() 

    
    doc_total = len(annotations.keys())

    for document in annotations.keys(): 
        doc_count += 1 
        percent = round((doc_count/doc_total*100), 2)
        print("Parsing document", document, "(", doc_count, "/", doc_total, " - ", str(percent), "%)...")
        entity_dict = dict() 
        document_entities = list()

        for annotation in annotations[document]:
            annotation_id, entity_text = annotation[0], annotation[1]
            normalized_text = entity_text.lower()
            total_entities += 1
            
            if annotation_id == None or annotation_id == "" or annotation_id == "-1": # The annotations is a NIL entity
                annotation_id = "NIL"
                nil_count += 1
            
            else:
                if normalized_text in document_entities: # Repeated instances of the same entity are not considered
                    continue
                
                else:    
                    document_entities.append(normalized_text)
                    total_unique_entities += 1
                     
                    # Get ontology candidates for entity
                    entity_dict[normalized_text], solution_is_first = generate_candidates_for_entity(normalized_text, annotation_id,
                                                                                                ontology, name_to_id, synonym_to_id,
                                                                                                min_match_score, ontology_graph)

                    # Check the solution found for this entity
                    
                    if solution_is_first: # The solution found is the correct one
                        solution_is_first_count += 1
                    
                    if len(entity_dict[normalized_text]) == 0: # Do not consider this entity if no candidate was found
                        del entity_dict[normalized_text]
                        no_solution += 1
                                     
                    else: # The entity has candidates, so it is added to entity_dict
                        entity_type = str()
                        
                        if ontology == "chebi" or ontology == "ctd_chemicals":
                            entity_type = "chemical"
                        
                        elif ontology == "medic":
                            entity_type = "disease"
                        
                        entity_str = entity_string.format(entity_text, normalized_text, entity_type, doc_count, document, annotation_id)
                        current_values = entity_dict[normalized_text]
                        current_values.insert(0, entity_str)
                        entity_dict[normalized_text] = current_values
            
        documents_entity_list[document] = entity_dict
    
    # Calculate statistics to output
    statistics = str()

    micro_precision = solution_is_first_count/(total_unique_entities-no_solution)
    micro_recall = solution_is_first_count/(solution_is_first_count + no_solution)
    micro_f1 = (2*(micro_precision*micro_recall)/(micro_precision+micro_recall))

    statistics += "\nNumber of documents: " + str(len(documents_entity_list.keys())) 
    statistics += "\nTotal entities: " + str(total_entities) + "\nNILs: " + str(nil_count)
    statistics += "\nValid entities: " + str(total_entities-nil_count)
    valid_entities_perc = ((total_entities-nil_count)/total_entities)*100
    statistics += "\n % of valid entities: " + str(valid_entities_perc)
    statistics += "\n\nTotal unique entities: " + str(total_unique_entities)
    entities_w_solution = total_unique_entities-no_solution
    statistics += "\nEntities w/ solution: " + str(entities_w_solution)
    statistics += "\nEntities w/o solution (FN): " + str(no_solution)    
    statistics += "\nWrong Disambiguations (FP): " + str(entities_w_solution-solution_is_first_count)
    statistics += "\nCorrect disambiguations (TP): " + str(solution_is_first_count) 
    statistics += "\nPrecision: " + str(micro_precision)
    statistics += "\nRecall: " + str(micro_recall)
    statistics += "\nMicro-F1 score: " + str(micro_f1)
    
    return documents_entity_list, statistics
    


def pre_process():

    start_time = time.time()
    
    min_match_score = 0.5 # min lexical similarity between entity text and candidate text
    
    corpus_ontology = str(sys.argv[1]) 
    model = str(sys.argv[2]) 
    link_mode = str(sys.argv[3]) 

    ontology_graph, name_to_id, synonym_to_id, annotations,  = None, dict(), dict(), dict()
    ontology, statistics, entity_type, subset = str(), str(), str(), str()

    if corpus_ontology == "craft_chebi":
        ontology_graph, name_to_id, synonym_to_id  = load_chebi()  # Load ontology file into graph and MultiDiGraph objects of Networkx
        entity_type = "Chemical"
        annotations = parse_craft_chebi_annotations() # Parse corpus annotations
        ontology = "chebi"
    
    else:
        bc5cdr_medic_list = ["bc5cdr_medic_train", "bc5cdr_medic_dev", "bc5cdr_medic_test", "bc5cdr_medic_all"]
        bc5cdr_chemicals_list = ["bc5cdr_chemicals_train", "bc5cdr_chemicals_dev", "bc5cdr_chemicals_test", "bc5cdr_chemicals_all"]
        
        if corpus_ontology in bc5cdr_medic_list:
            ontology_graph, name_to_id, synonym_to_id  = load_medic()
            subset = corpus_ontology.split("_")[2]
            entity_type = "Disease" 
            ontology = "medic"
        
        elif corpus_ontology in bc5cdr_chemicals_list:
            ontology_graph, name_to_id, synonym_to_id  = load_ctd_chemicals()
            subset = corpus_ontology.split("_")[2]
            entity_type = "Chemical"
            ontology = "ctd_chemicals"
        
        annotations = parse_cdr_annotations_pubtator(entity_type, subset)
    
    documents_entity_list, statistics = build_entity_candidate_dict(ontology, annotations, min_match_score, ontology_graph, name_to_id, synonym_to_id)
    
    statistics_filename = "results/" + corpus_ontology + "/baseline/"+ corpus_ontology + "_baseline_statistics"
    
    with open(statistics_filename, "w") as statistics_file:
        statistics_file.write(statistics)
        statistics_file.close()
    if model == "baseline":
        print(statistics)

    print("Parsing time (aprox.):", int((time.time() - start_time)/60.0), "minutes\n----------------------------------")
    
    # Import extracted relations from file into list if not baseline model or link_mode = "kb_link"
    if model != "baseline": 
        
        extracted_relations = []

        if link_mode == "corpus_link" or link_mode == "kb_corpus_link": 
            
            if corpus_ontology == "craft_chebi":
                extracted_relations = import_bolstm_output()
            
            else:
                extracted_relations = import_cdr_relations_pubtator(corpus_ontology, subset)
                
               

        # Create a candidates file for each corpus document
        document_count, entities_writen = int(), int()
        
        for document in documents_entity_list:
            document_count += 1
            candidates_filename = "candidates/{}/{}/{}".format(corpus_ontology, link_mode, document)
            print("Writing candidates:\t", document_count, "/", len(documents_entity_list.keys()))
            entities_writen += write_candidates(documents_entity_list[document], candidates_filename, entity_type,  ontology_graph, link_mode, extracted_relations)
        
        print("Entities writen in the candidates files:", entities_writen)
        
        # Create file with the information content of each ontology candidate appearing in candidates files 
        generate_ic_file(corpus_ontology, link_mode, annotations, ontology_graph)

    print("Total time (aprox.):", int((time.time() - start_time)/60.0), "minutes\n----------------------------------")   
    


if __name__ == "__main__":
    pre_process()
         
       
