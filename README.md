# REEL: Relation Extraction for Entity Linking 

Model for biomedical Named Entity Linking improved by Relation Extraction


## Dependencies
- [BO-LSTM](https://github.com/lasigeBioTM/BOLSTM)
- fuzzywuzzy
- obonet
- OpenJDK >= 8
- networkx
- python3 >= 3.5
- python-Levenshtein
- spacy

Or use the Dockerfile to setup the experimental environment.
 

## Usage

### 1. Getting the data
To download all the ontology and corpora files:

```

./get_data.sh

```


### 2. Applying the 'baseline' model (does not require pre-processing)

To simply apply the 'baseline' model (does not require the candidates files):

```

./run.sh [dataset] baseline none

```

Arg:

1. [dataset] - the options are: 
  - 'craft_chebi'
  - 'bc5cdr_medic_all'
  - 'bc5cdr_medic_train'
  - 'bc5cdr_medic_dev' 
  - 'bc5cdr_medic_test'
  - 'bc5cdr_chemicals_all'
  - 'bc5cdr_chemicals_train'
  - 'bc5cdr_chemicals_dev'
  - 'bc5cdr_chemicals_test'


### 3. Applying the PPR-IC or the REEL model 

To apply either the PPR-IC or the REEL model it is necessary to parse the annotations from the chosen dataset and create the candidates files. The disambiguation graph is built according to the information present in the candidates files and the chosen link_mode. The Personalised PageRank (PPR) algorithm is applied over the graph to rank the candidate nodes. The script *run.sh* performs both the pre-processing and the PPR steps:


```

./run.sh [dataset] [model] [link_mode]

```

Args:

1. [dataset] 

2. [model] - either 'baseline' or 'ppr_ic'

3. [link_mode] - How to add edges in the disambiguation graphs (link mode):
- 'none' : when model = 'baseline' there is no disambiguation graph
- 'kb\_link' : two nodes in the disambiguation graph are connected if they are directly linked in the respective ontology
- 'corpus\_link' : two nodes in the disambiguation graph are connected if they appear in the extracted relations set	
- 'corpus\_kb\_link' : concatenation of above link modes

The argument conjugations 'ppr-ic' + 'corpus_link' and 'ppr-ic' + 'kb_corpus_link' constitutes the two variations of the REEL model.

Example:

```

./run craft_chebi ppr_ic corpus_link

```

This script imports the output from BO-LSTM (a relation extraction tool) in the file 'full_model_temp.chebicraftresults.txt', creates the candidates files for each corpus document in the ´candidates/craft\_chebi/corpus\_link´ dir, applies the PPR algorithm and returns the results in a file located in 'results/craft\_chebi/ppr_ic/corpus\_link' dir and in the terminal:

```
Total unique entities: 1679
Entities w/o solution (FN): 299
Wrong disambiguations (FP): 119
Correct disambiguations (TP): 1261
Precision: 0.913768115942029
Recall: 0.8083333333333333
Micro F1-score: 0.8578231292517008
```
