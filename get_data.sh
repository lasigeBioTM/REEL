
################### Corpora ###################

#1. Download BC5CDR corpus
git clone https://github.com/JHnlp/BioCreative-V-CDR-Corpus.git
cd BioCreative-V-CDR-Corpus
unzip CDR_Data.zip
unzip BC5CDR_Evaluation-0.0.3.zip
cd ..

#2. Download CRAFT corpus v3.0
wget https://github.com/UCDenver-ccp/CRAFT/releases/download/3.0/craft-3.0.zip
unzip craft-3.0.zip


################### Ontologies ###################

#1. Download CTD_diseases (MEDIC) vocabulary
wget ctdbase.org/reports/CTD_diseases.obo.gz
gunzip -k CTD_diseases.obo.gz

#2. Download CTD_chemicals vocabulary
wget ctdbase.org/reports/CTD_chemicals.tsv.gz
gunzip -k CTD_chemicals.tsv.gz

#3. Download ChEBI ontology
wget ftp://ftp.ebi.ac.uk/pub/databases/chebi/archive/rel179/ontology/chebi.obo




