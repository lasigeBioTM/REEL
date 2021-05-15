from spacy.lang.en import English
from spacy.pipeline import Sentencizer
import os
import sys
import xml.etree.ElementTree as ET

sys.path.append("./")



def import_bolstm_output():
    """Parses the BO-LSTM output to obtain extracted relationship between ChEBI entities.

    Ensures: 
        extracted_relations: is dict where key is a disease id and values are the ids of related diseases
    """
    
    id_to_ontology_id = dict()

    # Create mappings between entity id and ChEBI id in the original file (pre-bolstm)
    path = "full_model_temp.chebicraftresults.txt"
    corpus_dir = "converted_chebi_craft_corpus/"
    docs_list = os.listdir(corpus_dir)
    
    for document in docs_list:
        tree = ET.parse(corpus_dir + document)
        root = tree.getroot()

        for entity in root.iter("entity"):
            ontology_id = entity.get("ontology_id")
            entity_id = entity.get("id")
            id_to_ontology_id[entity_id] = ontology_id

    # Read the bolstm output file and import relations
    bolstm_file = open(path, 'r')

    extracted_relations = dict()
    
    for line in bolstm_file.readlines():

        if line[:7] != "entity1": # Ignore the file header

            entity1_id = line.split('\t')[0]
            entity2_id = line.split('\t')[1]
            
            if line.split('\t')[2] == "effect\n": # There is a relation between the two entities
                entity1_ontology_id = id_to_ontology_id[entity1_id]  # Update the entity id with the respective ontology id
                entity2_ontology_id = id_to_ontology_id[entity2_id]

                if entity1_ontology_id in extracted_relations.keys():

                    if entity2_ontology_id not in extracted_relations[entity1_ontology_id]:
                        old_values = extracted_relations[entity1_ontology_id]
                        old_values.append(entity2_ontology_id) 
                        extracted_relations[entity1_ontology_id] = old_values
                            
                else:
                    new_values = [entity2_ontology_id]
                    extracted_relations[entity1_ontology_id] = new_values

                
                if entity2_ontology_id in extracted_relations.keys():
                    
                    if entity1_ontology_id not in extracted_relations[entity2_ontology_id]:
                        old_values = extracted_relations[entity2_ontology_id]
                        old_values.append(entity1_ontology_id) 
                        extracted_relations[entity2_ontology_id] = old_values
                
                else:
                    new_values = [entity1_ontology_id]
                    extracted_relations[entity2_ontology_id] = new_values
                    
    bolstm_file.close()

    return extracted_relations



def craft_input_to_bolstm():
        """Convert the documents in the CRAFT corpus to the input structure of BO-LSTM."""

        # Sentence segmentation using Spacy
        nlp = English()
        sentencizer = Sentencizer()
        nlp.add_pipe(sentencizer)

        # Parse each document in corpus directory -
        corpus_dir = "chebi_craft_corpus/"
        docs_list = os.listdir(corpus_dir)

        for idoc, file in enumerate(docs_list):
                
                if file[-3:] == "xmi":
                        file_path = corpus_dir + file 
                        file_id = str(file[:-4])
                        
                        #Retrieve the entire document text
                        tree = ET.parse(file_path)
                        root = tree.getroot()

                        for child in root: 
                                if child.tag == "{http:///uima/cas.ecore}Sofa":
                                        document_text = child.attrib["sofaString"]

                        # Import annotations from annotations file into annotation_list
                        annotation_list = []
                        annotation_file = open(file_path[:-3] + "ann", "r")

                        for line in annotation_file.readlines():
                                entity_text = line.split("\t")[2].strip("\n")
                                ontology_id = line.split("\t")[1].split(" ")[0].replace("_", ":")
                                offset_begin = int(line.split("\t")[1].split(" ")[1])
                                offset_end = int(line.split("\t")[1].split(" ")[2].split(";")[0])
                                annotation_list.append((entity_text, ontology_id, offset_begin, offset_end))

                        annotation_file.close()

                        # Create the xml tree for output file
                        new_root = ET.Element("document") 
                        new_root.set("id", file_id)

                        # Iterate over each sentence in document
                        docSpacy = nlp(document_text) 
                        sentence_count, token_count = 0, 0

                        for sentence in docSpacy.sents:
                                sentence_count += 1
                                begin_offset = token_count + 1
                                token_count += len(sentence.text) + 1
                                final_offset = token_count
                                sentence_id = str(file_id) + ".s" + str(sentence_count)
                                entity_count = 0
                                entity_check = []

                                # Create xml structure for sentence
                                new_sentence = ET.SubElement(new_root, "sentence")
                                new_sentence.set("id", sentence_id)
                                new_sentence.set("text", sentence.text)
                                
                                # Check if there is any annotation present in the current sentence
                                valid_entities_list = []
                                
                                for annotation in annotation_list:
                                        
                                        if annotation[2] >= begin_offset and annotation[2] <= final_offset: 
                                                # There is an annotation in this sentence
                                                entity_text = annotation[0]
                                                
                                                if entity_text not in entity_check: # The entity was not added to sentence

                                                        #Upgrade the entity offset in sentence context
                                                        entity_begin_offset = sentence.text.find(entity_text)
                                                        
                                                        if entity_begin_offset > -1: 
                                                                entity_count += 1
                                                                entity_id = sentence_id + ".e" + str(entity_count)
                                                                entity_final_offset = entity_begin_offset + len(entity_text) - 1
                                                                entity_offset = str(entity_begin_offset) + "-" + str(entity_final_offset)
                                                                entity_check.append(entity_text)
                                                                valid_entities_list.append(entity_id)
                                                              
                                                                # Create xml structure for annotation
                                                                new_entity = ET.SubElement(new_sentence, "entity")
                                                                new_entity.set("id", entity_id)
                                                                new_entity.set("charOffset", entity_offset)
                                                                new_entity.set("type", "chebi")
                                                                new_entity.set("text", entity_text)
                                                                new_entity.set("ontology_id", annotation[1])

                                # Create Xml structure for pairs of entities in sentence
                                pair_count = 0
                                pair_check = []

                                for valid_entity in valid_entities_list:

                                    for valid_entity_2 in valid_entities_list:
                                        print(valid_entity)
                                        if valid_entity != valid_entity_2: # Create a pair between two different entities
                                            pair_check_id1 = valid_entity + "_" + valid_entity_2
                                            pair_check_id2 = valid_entity_2 + "_" + valid_entity

                                            if pair_check_id1 not in pair_check and pair_check_id2 not in pair_check : # Prevent duplicate pairs
                                                pair_count += 1
                                                pair_id = sentence_id + ".p" + str(pair_count)
                                                pair_check.append(pair_check_id1)
                                                pair_check.append(pair_check_id2)

                                                new_pair = ET.SubElement(new_sentence, "pair")
                                                new_pair.set("id", pair_id)
                                                new_pair.set("e1", valid_entity), new_pair.set("e2", valid_entity_2)
                                                new_pair.set("ddi", "false")

                        #Create an .xml output file
                        ET.ElementTree(new_root).write("./bolstm/converted_chebi_craft/" + file_id + ".xml", xml_declaration=True)



bc5cdr_medic_list = ["bc5cdr_medic_train", "bc5cdr_medic_dev", "bc5cdr_medic_test", "bc5cdr_medic_all"]
bc5cdr_chemicals_list = ["bc5cdr_chemicals_train", "bc5cdr_chemicals_dev", "bc5cdr_chemicals_test", "bc5cdr_chemicals_all"]



def import_cdr_relations_pubtator(corpus_ontology, subset):
    """Import chemical-disease interactions from BC5CDR corpus in PubTator format into dict.
    
    Requires:
        corpus_ontology: is str representing the dataset
        subset: is str, either "train", "dev", "test" or "all"

    Ensures:
        extracted_relations: is dict, each key an ontology concept, values are related concepts
    """

    corpus_dir = "BioCreative-V-CDR-Corpus/CDR_Data/CDR.Corpus.v010516/"
    filenames = list()
    extracted_relations, extracted_relations_temp  = dict(), dict()
    
    if subset == "train":
        filenames.append("CDR_TrainingSet.PubTator.txt")
    
    elif subset == "dev":
        filenames.append("CDR_DevelopmentSet.PubTator.txt")
    
    elif subset == "test":
        filenames.append("CDR_TestSet.PubTator.txt")
    
    elif subset == "all":
        filenames.append("CDR_TrainingSet.PubTator.txt")
        filenames.append("CDR_DevelopmentSet.PubTator.txt")
        filenames.append("CDR_TestSet.PubTator.txt")
  
    for filename in filenames:

        with open(corpus_dir + filename, 'r') as corpus_file:
            data = corpus_file.readlines()
            corpus_file.close()

            for line in data:
                line_data = line.split("\t")
           
                if len(line_data) == 4 and line_data[1] == "CID": # Chemical-disease Relation 
                    chemical_id = line_data[2]
                    disease_id = line_data[3].strip("\n")

                    if corpus_ontology in bc5cdr_medic_list:

                        if chemical_id in extracted_relations_temp.keys():
                            old_values = extracted_relations_temp[chemical_id]
                            old_values.append(disease_id) 
                            extracted_relations_temp[chemical_id] = old_values
                                
                        else:
                            new_values = [disease_id]
                            extracted_relations_temp[chemical_id] = new_values

                    elif corpus_ontology in bc5cdr_chemicals_list:

                        if disease_id in extracted_relations_temp.keys():
                            old_values = extracted_relations_temp[disease_id]
                            old_values.append(chemical_id) 
                            extracted_relations_temp[disease_id] = old_values
                                
                        else:
                            new_values = [chemical_id]
                            extracted_relations_temp[disease_id] = new_values

    # Two disease terms are related if they are associated with the same chemical
    # Two chemical terms are related if they are associated with the same disease

    for key in extracted_relations_temp.keys():
        values = extracted_relations_temp[key]
        
        for value_1 in values:
            
            for value_2 in values:            

                if value_1 != value_2:

                    if value_1 in extracted_relations.keys():
                        current_values = extracted_relations[value_1]
                            
                        if value_2 not in current_values:
                            current_values.append(value_2)
                            extracted_relations[value_1] = current_values
                        
                    elif value_1 not in extracted_relations.keys():
                        extracted_relations[value_1] = [value_2]
                        
                    if value_2 in extracted_relations.keys():
                        current_values = extracted_relations[value_2]
                            
                        if value_1 not in current_values:
                            current_values.append(value_1)
                            extracted_relations[value_2] = current_values
                        
                    elif value_2 not in extracted_relations.keys():
                        extracted_relations[value_2] = [value_1]
    
    return extracted_relations
                    
                    

def import_cdr_relations_bioc(corpus_ontology):
    """Import chemical-disease interactions from BC5CDR corpus in BioCreative format into dict
    
    Requires:
        corpus_ontology: is str representing the dataset
        subset: is str, either "train", "dev", "test" or "all"

    Ensures:
        extracted_relations: is dict, each key an ontology concept, values are related concepts
    """

    corpus_dir = "CDR.Corpus.v010516/"
    docs_list = os.listdir(corpus_dir)
    extracted_relations  = dict()
    extracted_relations_temp = dict()
    
    for idoc, file in enumerate(docs_list): 
        if file[-3:] == "xml":
            file_path = corpus_dir + file                        
            tree = ET.parse(file_path) 
            root = tree.getroot()

            for document in root: 
                
                if document.tag == "document":
                    
                    for subelement in document:
                                
                        if subelement.tag == "relation":
                            chemical_id, disease_id = str(), str()
                            
                            for subelement2 in subelement:
                                if subelement2.attrib["key"] == "Chemical": # disease or chemical
                                    chemical_id = subelement2.text
                                
                                elif subelement2.attrib["key"] == "Disease":
                                    disease_id = subelement2.text
                            
                            if corpus_ontology in bc5cdr_medic_list:

                                if chemical_id in extracted_relations_temp.keys():
                                    old_values = extracted_relations_temp[chemical_id]
                                    old_values.append(disease_id) 
                                    extracted_relations_temp[chemical_id] = old_values
                                
                                else:
                                    new_values = [disease_id]
                                    extracted_relations_temp[chemical_id] = new_values
                            
                            elif corpus_ontology in bc5cdr_chemicals_list:

                                if disease_id in extracted_relations_temp.keys():
                                    old_values = extracted_relations_temp[disease_id]
                                    old_values.append(chemical_id) 
                                    extracted_relations_temp[disease_id] = old_values
                                
                                else:
                                    new_values = [chemical_id]
                                    extracted_relations_temp[disease_id] = new_values

    # Two disease terms are related if they are associated with the same chemical
    # Two chemical terms are related if they are associated with the same disease

    for key in extracted_relations_temp.keys():
        values = extracted_relations_temp[key]
        
        for value_1 in values:
            
            for value_2 in values:            

                if value_1 != value_2:

                    if value_1 in extracted_relations.keys():
                        current_values = extracted_relations[value_1]
                            
                        if value_2 not in current_values:
                            current_values.append(value_2)
                            extracted_relations[value_1] = current_values
                        
                    elif value_1 not in extracted_relations.keys():
                        extracted_relations[value_1] = [value_2]
                        
                    if value_2 in extracted_relations.keys():
                        current_values = extracted_relations[value_2]
                            
                        if value_1 not in current_values:
                            current_values.append(value_1)
                            extracted_relations[value_2] = current_values
                        
                    elif value_2 not in extracted_relations.keys():
                        extracted_relations[value_2] = [value_1]
                        
    return extracted_relations




