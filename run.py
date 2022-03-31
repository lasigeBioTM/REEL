import argparse
import os
from src.pre_process import pre_process
from src.process_results import process_results

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--run_label", type=str, required=False, default="run_1")
    parser.add_argument("-model", type=str, required=True, default='baseline',
        choices = ['baseline', 'ppr_ic'], 
        help="The base model to link the entities: 'baseline' (it chooses  the\
            best candidate for each entity according to Leveshtein distance), \
            'ppr_ic' (it generates a list of top-k candidates for each entity \
            and then applies the PPR algorithm and the Information content to \
            choose the best candidate)")
    parser.add_argument("--link_mode", type=str, required=False, default='none',
        choices = ['none', 'kb_link', 'corpus_link', 'kb_corpus_link'],
        help = "How to add edges in the disambiguation graphs if ppr_ic model \
        is being applied: 'none' (when model = 'baseline'), 'kb_link' (two \
        nodes in the disambiguation graph are connected if they are directly \
        linked in the respective ontology, 'corpus_link' (two nodes in the \
        disambiguation graph are connected if they appear in the extracted \
        relations set, 'kb_corpus_link' : concatenation of above link modes")
    parser.add_argument("--dataset", type=str, required=False, 
        choices = ['craft_chebi', "bc5cdr_medic_train", "bc5cdr_medic_dev", 
            "bc5cdr_medic_test", "bc5cdr_medic_all", "bc5cdr_chemicals_train", 
            "bc5cdr_chemicals_dev", "bc5cdr_chemicals_test", 
            "bc5cdr_chemicals_all"],
            help = "The source dataset containing entities to be linked to the \
            respective target ontology")
    parser.add_argument("--input_file", type=str, required=False,
        help= "Read json input file containing the entities to be linked. \
        Format of the file: {'doc_id': 'entity_text_1', 'entity_text_2'}")
    parser.add_argument("-target_kb", type=str, required=True,
        choices = ['chebi', 'ctd_chem', 'medic'],
        help= "If there is an input file, this argument specifies the target \
            KB to where the entities must be matched")
    
    parser.add_argument("--out_dir", type=str,required=False)
    args = parser.parse_args()

    #------------------------------------------------------------------------------
    #               Pre-processing or 'baseline' model application
    #------------------------------------------------------------------------------
    pre_process(args.model, run_label=args.run_label, link_mode=args.link_mode, 
        dataset=args.dataset, input_file=args.input_file, target_kb=args.target_kb)

    #------------------------------------------------------------------------------
    #                                 REEL model
    #------------------------------------------------------------------------------

    # Build a disambiguation graph from each candidates file: the nodes are the candidates 
    # and relations are added according to link_mode

    if args.model != "baseline":
        comm = ''

        if args.input_file != None:
            comm = 'java ppr_for_ned_all {} {} {}'.format(args.run_label, args.model, args.link_mode)
            os.system(comm)
            process_results(args.target_kb, args.link_mode, run_label=args.run_label, input_file=args.input_file, out_dir=args.out_dir)

        elif args.dataset:
            comm = 'java ppr_for_ned_all {} {} {}'.format(args.dataset, args.model, args.link_mode)
            os.system(comm)
            process_results(args.target_kb, args.link_mode, dataset= args.dataset, out_dir=args.out_dir)

