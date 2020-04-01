#!/usr/bin/env bash


################### Pre-processing or 'baseline' model application ###################

# Pre-process the corpus to create a candidates file for each document in corpus and apply 'baseline' model

python3 src/pre_process.py $1 $2 $3 


################### PPR-IC and REEL models ###################

# Build a disambiguation graph from each candidates file: the nodes are the candidates and relations are added according to link_mode

if [ $2 != 'baseline' ]
then
  javac ppr_for_ned_all.java
  java ppr_for_ned_all $1 $2 $3 
  python3 src/process_results.py $1 $2 $3
fi

# Results file will be in directory results/<corpus_ontology>/<model>/<link_mode>


