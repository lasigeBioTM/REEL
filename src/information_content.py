import os
import networkx as nx
import xml.etree.ElementTree as ET
from math import log



def build_extrinsic_information_content_dict(annotations):
    """Dict with extrinsic information content (Resnik's) for each term in a corpus.""" 

    term_counts, extrinsic_ic = {}, {}
   
    # Get the term frequency in the corpus
    for document in annotations: 
        
        for annotation in annotations[document]:
            
            term_id = annotation[0]
            
            if term_id not in term_counts.keys():
                term_counts[term_id] = 1
            else:
                term_counts[term_id] += 1
            
    max_freq = max(term_counts.values()) # Frequency of the most frequent term in dataset
    
    for term_id in term_counts:
        
        term_frequency = term_counts[term_id] 
   
        term_probability = (term_frequency + 1)/(max_freq + 1)
    
        information_content = -log(term_probability) + 1
        
        extrinsic_ic[term_id] = information_content + 1
    
    return extrinsic_ic


def generate_ic_file(target_ontology, link_mode, annotations):
    """Generate file with information content of all entities referred in candidates file."""

    ontology_pop_string = str()
    
    candidates_dir = "candidates/{}/{}/".format(target_ontology, link_mode)
    
    ic_dict = build_extrinsic_information_content_dict(annotations) 
    
    url_temp = list()

    for file in os.listdir(candidates_dir): 
        data = ''
        path = candidates_dir + file
        candidate_file = open(path, 'r', errors="ignore")
        data = candidate_file.read()
        candidate_file.close()
        
        for line in data.split('\n'):
            url, surface_form = str(), str()
            
            if line[0:6] == "ENTITY":
                surface_form = line.split('\t')[1].split('text:')[1]
                url = line.split('\t')[8].split('url:')[1]
                #predicted_type = line.split('\t')[3][14:]
            
            elif line[0:9] == "CANDIDATE":
                surface_form = line.split('\t')[6].split('name:')[1]
                url = line.split('\t')[5].split('url:')[1]
                #predicted_type = line.split('\t')[9][14:]     
          
                
            if url in url_temp:
                continue
                
            else:
                    
                if url != "":   
                    url_temp.append(url)

                    if url in ic_dict.keys():
                        ic = ic_dict[url]                        
                                
                    else:
                        ic = 1.0
                        
                    #if target_ontology == "craft_chebi":
                    #    print(url)
                    #    url = url.split("_")[1]
                        #ontology_pop_string += "url:http:" + url +'\t' + str(ic) + '\n'
                        
                    #else:
                    ontology_pop_string += url.replace(':', '_') +'\t' + str(ic) + '\n'
                        
    # Create file ontology_pop with information content for all entities in candidates file
    output_file_name = target_ontology + "_ic"
    
    with open(output_file_name, 'w') as ontology_pop:
        ontology_pop.write(ontology_pop_string)
        ontology_pop.close()


