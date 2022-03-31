# REEL: Relation Extraction for Entity Linking 

Model for biomedical Named Entity Linking improved by Relation Extraction

## Reference
- Ruas, P., Lamurias, A. & Couto, F.M. Linking chemical and disease entities to ontologies by integrating PageRank with extracted relations from literature. J Cheminform 12, 57 (2020). [https://doi.org/10.1186/s13321-020-00461-4](https://doi.org/10.1186/s13321-020-00461-4)

------------------------------------------------------------------------------
## Table of contents:
- [1. Setup](#Setup)
  - [1.1. Docker](#docker)
  - [1.2. Data](#data)
- [2. Usage](#usage)
  - [2.1. Apply the REEL model on custom input](#custom)
  - [2.1. Apply the REEL model on evaluation dataset](#dataset)

-----------------------------------------------------------------------------
## 1. Setup<a name="Setup"></a>

### 1.1. Docker<a name="docker"></a>

Build the Docker image from the Dockerfile:

```
docker build . --tag reel_image
```

Then run a docker container:

```
docker run -v $(pwd):/reel/ --name reel -it reel_image bash
```


### 1.2. Data<a name="data"></a>

To download all the ontology and corpora files:

```
chmod +x get_data.sh
./get_data.sh
```

------------------------------------------------------------------------------

## 2. Usage<a name="usage"></a>

### 2.1. Apply the REEL model on custom input<a name="input"></a>

If you have the ouput of a NER tool first store it in a json file with the same
format as 'sample_input.json': 

```
{
 "doc_1": ["hypertension", "diabetes mellitus", "diazepam", "GABA"],
 "doc_2": ["myocarditis", "heart failure", "acetaminophen"],
 "doc_3": ["hepatitis", "caffeine", "adrenaline"]
}
```

Then apply the REEL model to link the inputed entities to ChEBI concepts:

```
python run.py --run_label sample_run --input_file sample_input.json -target_kb chebi -model ppr_ic --link_mode corpus_kb_link 
```

The output will be in the file 'sample_run_results.json':

```
{
"doc_1":{"diazepam":"CHEBI:49575", "gaba":"CHEBI:35621"},
"doc_2":{"acetaminophen":"CHEBI:22160"},
"doc_3":{"adrenaline":"CHEBI:33568", "caffeine":"CHEBI:27732"}
}
```

There are 3 target knowledge bases available: ['chebi'](https://www.ebi.ac.uk/chebi/), ['medic'](http://ctdbase.org/voc.go;jsessionid=2772F41749EC369798B9854B9C40D648?type=disease) and ['ctd-chem'](http://ctdbase.org/voc.go?type=chem).


To see more info about the input arguments:

```
python run.py -h
```

If instead you want to apply the baseline model run on the same input file:

```
python run.py --input_file sample_entities.json --target_kb chebi -model baseline 
```

### 2.2. Apply the REEL model on evaluation dataset<a name="dataset"></a>


To evaluate the REEL model on the dataset CRAFT-ChEBI run:

```
python run.py --dataset craft_chebi -model ppr_ic --link_mode corpus_link -target_kb chebi
```

The results are outputted to a file located in 'results/craft_chebi/ppr_ic/corpus_link' and printed in the terminal:

```
Total unique entities: 1679
Entities w/o solution (FN): 299
Wrong disambiguations (FP): 119
Correct disambiguations (TP): 1261
Precision: 0.913768115942029
Recall: 0.8083333333333333
Micro F1-score: 0.8578231292517008
```

Available datasets:
- 'craft_chebi' (target_kb = chebi)
- 'bc5cdr_medic_all' (target_kb = medic)
- 'bc5cdr_medic_train' (target_kb = medic)
- 'bc5cdr_medic_dev' (target_kb = medic)
- 'bc5cdr_medic_test' (target_kb = medic)
- 'bc5cdr_chemicals_all' (target_kb = ctd_chemicals)
- 'bc5cdr_chemicals_train' (target_kb = ctd_chemicals)
- 'bc5cdr_chemicals_dev' (target_kb = ctd_chemicals)
- 'bc5cdr_chemicals_test' (target_kb = ctd_chemicals)

