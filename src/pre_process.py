import argparse
import os
import orjson as json
import sys
import time
import xml.etree.ElementTree as ET

from tqdm import tqdm
from src.chebi import load_chebi
from src.medic import load_medic
from src.ctd_chemicals import load_ctd_chemicals
from src.annotations import parse_input_file, parse_craft_chebi_annotations, parse_cdr_annotations_pubtator
from src.candidates import write_candidates, generate_candidates_for_entity
from src.information_content import generate_ic_file
from src.relations import import_bolstm_output, import_cdr_relations_pubtator
from src.strings import entity_string

sys.path.append("./")


def check_if_dirs_exist(candidates=False, results=False, run_label=None, dataset=None, link_mode=None):
    """asffssf"""

    target_dir = ''

    if candidates:
        target_dir = 'candidates/'

    elif results:
        target_dir = 'results/'

    if run_label != None:
        target_dir += run_label + '/'
    
    elif dataset != None:
        target_dir += dataset + '/'

    # Create directories for candidates files
    if not os.path.exists(target_dir):
        os.mkdir(target_dir)

    target_dir_2 = ''

    if results:
        target_dir_1_0 = target_dir + 'ppr_ic/'

        if not os.path.exists(target_dir_1_0):
            os.mkdir(target_dir_1_0)

        target_dir_2 = target_dir_1_0 + link_mode + '/'
        
    
    elif candidates:
        target_dir_2 = target_dir + link_mode + '/'

    if not os.path.exists(target_dir_2):
        os.mkdir(target_dir_2)
    
    # Delete existing candidates files
    cand_files = os.listdir(target_dir_2)

    if len(cand_files)!=0:
        
        for file in cand_files:
            os.remove(target_dir_2 + file)

    return target_dir_2


def build_entity_candidate_dict(ontology, annotations, min_match_score, ontology_graph, name_to_id, synonym_to_id, dataset=None):
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

    nil_count, total_entities, total_unique_entities, no_solution, solution_is_first_count = int(),int(), int(), int(), int()
    
    documents_entity_list = dict() 

    pbar = tqdm(total= len(annotations.keys()), colour= 'green', desc='Pre-processing')

    for i, document in enumerate(annotations.keys()): 
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
                    entity_dict[normalized_text], solution_is_first = generate_candidates_for_entity(
                        normalized_text, annotation_id, ontology, name_to_id, synonym_to_id,
                        min_match_score, ontology_graph, dataset=dataset)

                    # Check the solution found for this entity
                    
                    if solution_is_first: # The solution found is the correct one
                        solution_is_first_count += 1
                    
                    if len(entity_dict[normalized_text]) == 0 and dataset != None: # Do not consider this entity if no candidate was found
                        del entity_dict[normalized_text]
                        no_solution += 1
                                     
                    elif (len(entity_dict[normalized_text]) > 0 and dataset != None) or \
                            dataset == None:
                        # The entity has candidates, so it is added to entity_dict
                        entity_type = str()
                        
                        if ontology == "chebi" or ontology == "ctd_chem":
                            entity_type = "chemical"
                        
                        elif ontology == "medic":
                            entity_type = "disease"
                        
                        entity_str = entity_string.format(entity_text, normalized_text, entity_type, i, document, annotation_id)
                        current_values = entity_dict[normalized_text]
                        current_values.insert(0, entity_str)
                        entity_dict[normalized_text] = current_values
            
        documents_entity_list[document] = entity_dict
        pbar.update(1)
    
    pbar.close()
    
    # Calculate statistics to output
    statistics = str()

    try:
        micro_precision = solution_is_first_count/(total_unique_entities-no_solution)
    
    except:
        micro_precision = 0

    try:
        micro_recall = solution_is_first_count/(solution_is_first_count + no_solution)
    
    except:
        micro_recall = 0

    try:
        micro_f1 = (2*(micro_precision*micro_recall)/(micro_precision+micro_recall))
    
    except:
        micro_f1 = 0

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
    


def pre_process(model, run_label=None, link_mode="none", dataset=None, 
        input_file=None, target_kb=None):
    
    start_time = time.time()
    #-------------------------------------------------------------------------
    
    ontology_graph, name_to_id, synonym_to_id, annotations,  = None, {}, {}, {}
    statistics, entity_type, subset = '', '', ''

    if dataset != None:
        bc5cdr_medic_list = ["bc5cdr_medic_train", "bc5cdr_medic_dev", "bc5cdr_medic_test", "bc5cdr_medic_all"]
        bc5cdr_chemicals_list = ["bc5cdr_chemicals_train", "bc5cdr_chemicals_dev", "bc5cdr_chemicals_test", "bc5cdr_chemicals_all"]
        run_label = dataset

        if dataset == "craft_chebi":
            ontology_graph, name_to_id, synonym_to_id  = load_chebi()  # Load ontology file into graph and MultiDiGraph objects of Networkx
            entity_type = "Chemical"
            annotations = parse_craft_chebi_annotations() # Parse corpus annotations
            target_kb = "chebi"

        elif dataset in bc5cdr_medic_list:
            ontology_graph, name_to_id, synonym_to_id  = load_medic()
            subset = dataset.split("_")[2]
            entity_type = "Disease" 
            target_kb = "medic"

            annotations = parse_cdr_annotations_pubtator(entity_type, subset)
        
        elif dataset in bc5cdr_chemicals_list:
            ontology_graph, name_to_id, synonym_to_id  = load_ctd_chemicals()
            subset = dataset.split("_")[2]
            entity_type = "Chemical"
            target_kb = "ctd_chem"
            
            annotations = parse_cdr_annotations_pubtator(entity_type, subset)
    
    else:
        run_label = run_label

        if input_file != None:

            if target_kb == 'chebi':
                ontology_graph, name_to_id, synonym_to_id  = load_chebi()
                entity_type = 'Chemical'
            
            elif target_kb == 'ctd_chem':
                ontology_graph, name_to_id, synonym_to_id  = load_ctd_chemicals()
                entity_type = 'Chemical'
                
            elif target_kb == 'medic':
                ontology_graph, name_to_id, synonym_to_id  = load_medic()
                entity_type = 'Disease'
            
            annotations = parse_input_file(input_file)

        else:
            raise ValueError('You need to input either a dataset or a file with entities!')
    #---------------------------------------------------------------------------
    min_match_score = 0.5 # min lexical similarity between entity text and candidate text
    #print(target_kb)
    documents_entity_list, statistics = build_entity_candidate_dict(target_kb, annotations, min_match_score, ontology_graph, name_to_id, synonym_to_id, dataset=dataset )
    

    if model == "baseline" or dataset != None:
        statistics_filename = "results/{}/baseline/{}_baseline_statistics".format(run_label, run_label)
    
        with open(statistics_filename, "w") as statistics_file:
            statistics_file.write(statistics)
            statistics_file.close()
        
        print(statistics)
        print("Parsing time (aprox.):", int((time.time() - start_time)/60.0), "minutes\n----------------------------------")
    
    # Import extracted relations from file into list if not baseline model or link_mode = "kb_link"
    if model != "baseline": 
        
        extracted_relations = []

        if link_mode == "corpus_link" or link_mode == "kb_corpus_link": 
            
            if target_kb == "chebi":

                with open('chebi_relations.json', 'r') as rel_file:
                    extracted_relations = json.loads(rel_file.read())
                    rel_file.close()
                #extracted_relations = import_bolstm_output()
            
            elif target_kb == "ctd_chem" or target_kb == "medic":
                
                with open(entity_type + '_relations.json', 'r') as rel_file:
                    extracted_relations = json.loads(rel_file.read())
                    rel_file.close()

                #extracted_relations = import_cdr_relations_pubtator(entity_type)

        # Create a candidates file for each corpus document
        entities_writen = 0
        
        check_if_dirs_exist(candidates=True, run_label=run_label, dataset=dataset, link_mode=link_mode)

        pbar = tqdm(total= len(documents_entity_list.keys()), colour= 'green', desc='Writing candidates files')

        for document in documents_entity_list:
            candidates_filename = "candidates/{}/{}/{}".format(run_label, link_mode, document)
            entities_writen += write_candidates(documents_entity_list[document], candidates_filename, entity_type,  ontology_graph, link_mode, extracted_relations)
            pbar.update(1)
        
        pbar.close()
        print("Entities writen in the candidates files:", entities_writen)
        
        # Create file with the information content of each ontology candidate appearing in candidates files 
        generate_ic_file(run_label, link_mode, annotations)

    check_if_dirs_exist(results=True, run_label=run_label, dataset=dataset, link_mode=link_mode)

    print("Total time (aprox.):", int((time.time() - start_time)/60.0), "minutes\n----------------------------------")   