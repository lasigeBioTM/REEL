import orjson as json
import os
import xml.etree.ElementTree as ET
import sys

sys.path.append("./")


def parse_input_file(filepath):
    """Annotations format: {'doc_id: [(kb_id, annot1)]}"""
    
    annotations = {}

    with open(filepath, 'r') as input_file:
        in_annotations = json.loads(input_file.read())
        input_file.close()

        for doc_id in in_annotations.keys():
            doc_entities = in_annotations[doc_id]
            doc_entities_up = []

            for entity in doc_entities:
                doc_entities_up.append(('none', entity))
        
            annotations[doc_id] = doc_entities_up

        return annotations


def parse_cdr_annotations_pubtator(entity_type, subset):
    """Get each annotation in the BC5CDR corpus with documents in PubTator format.

    Requires:
        entity_type: is str, either "Chemical" or "Disease"
        subset: is str, either "train", "dev", "test" or "all"
    
    Ensures:
        annotations: is dict, each key is document str, values are list with all the annotations in document
    """
    
    corpus_dir = "BioCreative-V-CDR-Corpus/CDR_Data/CDR.Corpus.v010516/"    
    annotations = dict()
    filenames = list()
    
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
                document_id = line_data[0]
           
                if len(line_data) == 6 and line_data[4] == entity_type:
                    mesh_id = line_data[5].strip("\n")
                    
                    annotation_text = line_data[3]
                    annotation = (mesh_id, annotation_text)
            
                    if document_id in annotations.keys():
                        current_values = annotations[document_id]
                        current_values.append(annotation)
                        annotations[document_id] = current_values
                    
                    else:
                        annotations[document_id] = [annotation]
 
    return annotations



def parse_cdr_annotations_bioc(entity_type, subset):
    """Get each annotation in the BC5CDR corpus with documents in BioCreative format.

    Requires:
        entity_type: is str, either "Chemical" or "Disease"
        subset: is str, either "train", "dev", "test" or "all"
    
    Ensures:
        annotations: is dict, each key is document str, values are list with all the annotations in document
    """
    
    corpus_dir = "BioCreative-V-CDR-Corpus/CDR_Data/CDR_Data/CDR.Corpus.v010516/" 
    annotations = dict()
    valid_annotation_count, all_annotations= int(), int()
    filenames = list()
    
    if subset == "train":
        filenames = ["CDR_TrainingSet.BioC.xml"]
    elif subset == "dev":
        filenames = ["CDR_DevelopmentSet.BioC.xml"]
    elif subset == "test":
        filenames = ["CDR_TestSet.BioC.xml"]
    elif subset == "all":
        filenames == ["CDR_TrainingSet.BioC.xml", "CDR_DevelopmentSet.BioC.xml", "CDR_TestSet.BioC.xml"]
            
    for filename in filenames:
        file_path = corpus_dir + filename                     
        tree = ET.parse(file_path) 
        root = tree.getroot()

        for document in root: 
                
            if document.tag == "document":
                file_id = str()
                annotations_temp = list()
                    
                for subelement in document:
                                
                    if subelement.tag == "id":
                        file_id = subelement.text
                            
                    elif subelement.tag == "passage":
                
                        for subelement2 in subelement: # Iterate over each annotation in current passage                                
                                                               
                            if subelement2.tag == "annotation":
                                entity_text, mesh_unique_id, annotation_type = str(), str(), str()
                                    
                                for subelement3 in subelement2: # Retrieve the information about the annotation
                                        
                                    if subelement3.tag == "infon":
                                            
                                        if subelement3.attrib["key"] == "type": # disease or chemical
                                            annotation_type = subelement3.text
                                        elif subelement3.attrib["key"] == "MESH":
                                            mesh_unique_id = subelement3.text
                                        
                                    elif subelement3.tag == "text":
                                        entity_text = subelement3.text

                                if annotation_type == "Disease": #entity_type:
                                    all_annotations += 1
                                        
                                    if "|" not in mesh_unique_id: #Do not consider composite mentions
                                        #print((mesh_unique_id, entity_text))
                                        valid_annotation_count += 1
                                        annotations_temp.append((mesh_unique_id, entity_text))
                    
                annotations[file_id] = annotations_temp
   
    return annotations



def parse_craft_chebi_annotations():
    """Get each ChEBI annotation in ChEBI corpus."""
    
    corpus_dir = "./craft-3.0/ontology-concepts/CHEBI/CHEBI/brat/"
    docs_list = os.listdir(corpus_dir)

    annotations = dict()

    for idoc, file in enumerate(docs_list): 
        
        if file[-3:] == "ann":
            file_id = str(file[:-4])
            annotations_temp = list()

            file_content = open(corpus_dir + str(file), "r")
            document = file_content.readlines()
            file_content.close()
            
            # Parse each annotation
            for line in document: 
                annotation_text = line.split("\t")[2].strip("\n")
                chebi_id = line.split("\t")[1].split(" ")[0]#.replace("_", ":")

                annotations_temp.append((chebi_id, annotation_text))                

            annotations[file_id] = annotations_temp

    return annotations




