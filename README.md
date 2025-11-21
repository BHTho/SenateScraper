# SenateScraper
Scrapes US Senator Financial Disclosures (Research (i.e. non-commercial) Purposes Only)


Usage:


## Docker

Create a .env file, copying the format of the .env_example.

Enter your settings for the script then run:
```
docker-compose up --build
```

## Command Line

Create a virtual environment in the project directory and install the necessary packages

```
python -m venv venv
source ./venv/bin/activate
pip install -r requirements.txt
```

Ensure you have google chrome installed on your machine.

run the tool in the command line with the following arguments:

```
python main.py --start-date "YYY-MM-DD" --output-csv
```

By default the results are output in to "senate_disclosures.csv" in the project directory.

Alternatively you can upload the results to an AWS S3 bucket, but you will have to put your credentials in the .env file:

```
python main.py --start-date --output-aws
```

There are also additional flags you can set:
```
--verbose # adds additional print outputs for debugging
--visible # removes the headless setting so you can watch the scraping
```