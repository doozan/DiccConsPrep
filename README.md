Script to parse Emile Slager's [Diccionario español de construcciones preposicionales](https://zenodo.org/records/3712926) and convert it to StarDict, Aard2/slob, and JSON formats.

# Credits
[Diccionario español de construcciones preposicionales](https://zenodo.org/records/3712926), CC-BY Emile Slager (2020)

# Building

Pre-built dictionary files are available for download [here](releases), but if you want to build it yourself, here's how:

# Required packages
pdftotext

# Building the JSON data
```
wget "https://zenodo.org/records/3712926/files/DiccConsPrep.pdf?download=1" -O "DiccConsPrep.pdf"
pdftotext -layout DiccConsPrep.pdf DiccConsPrep.txt
./convert.py "DiccConsPrep.txt" --json > DiccConsPrep.json
```

# Building the dictionaries
```
python3 -m venv dic_convert
source dic_convert/bin/activate
pip install pyglossary
pip install git+https://github.com/doozan/enwiktionary_wordlist.git

# get form/lemma database (so the dictionary can show "hablar" when searching for "hablamos")
wget https://raw.githubusercontent.com/doozan/spanish_data/refs/heads/master/es_allforms.csv

wget https://github.com/doozan/DiccConsPrep/raw/master/convert.py -o convert.py
python3 convert.py "DiccConsPrep.txt" > DiccConsPrep.data

wordlist_to_dictunformat \
    DiccConsPrep.data \
    es_allforms.csv \
    --ul \
    --name "ConsPrep (es-es)" \
    --description "Diccionario español de construcciones preposicionales. Emile Slager (2020) CC-BY" \
    > DiccConsPrep.dictunformat

pyglossary --ui=none DiccConsPrep.dictunformat DiccConsPrep.slob
pyglossary --ui=none DiccConsPrep.dictunformat DiccConsPrep.ifo
```
