## Github Open Source Contributor tracker and health Monitor

## ETL Pipeline
It is built on an ETL pipeline
-Extraction: It extract data via an API key of Github(Github REST API)
-Transform : IT transforms the data into usefull stats using pandas and padalyts
-Load : It loads Data into a data base

## Dependencies
requests
pandas
numpy
matplotlib
seaborn
jupyter

- To install them first create a virtual environment
1. python3 -m venv .venv
2. source .venv/bin/activate

Now install them .Bash.
python -m pip install -r requirements.txt