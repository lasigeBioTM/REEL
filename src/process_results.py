import sys

sys.path.append("./")



def process_results(corpus_ontology, link_mode):
    """ Process the results after the application of the PPR-IC model."""

    results_dict = dict()
    correct_answers_count, wrong_answers_count, total_answers, no_solution = int(), int(), int(), int()

    filename = "results/" + corpus_ontology + "/ppr_ic/" + link_mode + "/all_all"

    with open(filename, 'r') as results:
        data = results.readlines()
        results.close
    
    doc_id = str()
    temp_dict = dict()
    
    for line in data:
        
        if line != "\n":
            
            if line[0] == "=":
                results_dict[doc_id] = temp_dict
                global doc_id
                doc_id = line.strip("\n").split(" ")[1]
                temp_dict = dict()
            
            else:
                number_of_mentions = int(line.split("\t")[0])
                total_answers += 1 * number_of_mentions
                entity_text = line.split("\t")[1].split("=")[1]
                correct_answer = line.split("\t")[2]
                answer = line.split("\t")[3].strip("ANS=").strip("\n")
                temp_dict[entity_text] = "MESH:" + answer
             
                if answer == correct_answer:
                    correct_answers_count += number_of_mentions* 1
                
                else:
                    wrong_answers_count += number_of_mentions* 1

    results_dict[doc_id] = temp_dict

    
    # Import NIL count from baseline statistics file
    nil_filename = "results/" + corpus_ontology + "/baseline/"+ corpus_ontology + "_baseline_statistics"
    with open(nil_filename, "r") as nil_file:
        data = nil_file.readlines()
        nil_file.close()
    
        for line in data:
            if line[:21] == "Entities w/o solution":
                no_solution += int(line.split(":")[1].strip(" "))

    # Calculate statistics to output
    precision = correct_answers_count/total_answers
    recall = correct_answers_count/(correct_answers_count + no_solution)
    micro_f1_score = 2*(precision*recall)/(precision + recall)
        
    statistics_str = "\nTotal unique entities: " + str(total_answers + no_solution)
    statistics_str += "\nEntities w/o solution (FN): " + str(no_solution)
    statistics_str += "\nWrong disambiguations (FP): " + str(total_answers-correct_answers_count)
    statistics_str += "\nCorrect disambiguations (TP): " + str(correct_answers_count)
    statistics_str += "\nPrecision: " + str(precision)
    statistics_str += "\nRecall: " + str(recall)
    statistics_str += "\nMicro F1-score: " + str(micro_f1_score)
    print(statistics_str)

    statistics_filename = "results/" + corpus_ontology + "/ppr_ic/"+ link_mode + "/" + corpus_ontology + "_ppr_ic_" + link_mode + "_statistics"
        
    with open(statistics_filename, "w") as statistics_file:
        statistics_file.write(statistics_str)
        statistics_file.close()
    
    return results_dict            



if __name__ == "__main__":
    corpus_ontology = str(sys.argv[1])
    link_mode = str(sys.argv[3])
    
    process_results(corpus_ontology, link_mode)
  