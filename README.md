# 🤖 SenateScraper

**Scrapes US Senator Financial Disclosures (Research (i.e. Non-commercial) Purposes Only)**

This tool automates the retrieval of publicly available U.S. Senator financial disclosure data.

---

## 🚀 Getting Started

You can run **SenateScraper** using either Docker or directly via the Command Line. Both methods require you to first set up a configuration file.

### 1. Configuration (`.env` file)

Before running the scraper, you must create a configuration file named **`.env`** in the project root directory.

* **Copy the example:** Duplicate the provided `.env_example` file and rename it to `.env`.
* **Enter your settings:** Configure any necessary parameters, especially for the optional AWS S3 upload feature.

If you're going to upload to AWS, you'll need to ensure your DynamoDB table is set up and that you have all the credentials.

---

## 🐳 Usage with Docker (Recommended)

This is the recommended method as it encapsulates all dependencies, including the necessary web browser, without requiring a local installation of Chrome.

1.  **Ensure Docker is running** on your machine.
2.  **Configure your `.env` file** (as described above).
3.  **Run the service** from the project root directory:

```
docker-compose up --build
```
* The scraper will run based on the parameters set internally in the Docker setup (typically reading from your `.env`).

---

## 💻 Usage with Command Line

This method requires a local Python environment and a specific browser installation.

### 1. Prerequisites and Setup

1.  **Install Google Chrome:** Ensure **Google Chrome** is installed on your machine, as the scraper uses a Chrome driver.

2.  **Create and activate a virtual environment:**
```
python -m venv venv
source ./venv/bin/activate
```
3.  **Install dependencies:**
```
pip install -r requirements.txt
```

### 2. Execution Options

Run the script using `python main.py`, followed by the required start date and your desired output option.

#### A. Output to Local CSV (Default)

The results will be saved to a file named `senate_disclosures.csv` in the project directory.

```
python run.py --start-date "MM-DD-YYY" --output-csv
```

#### B. Upload to AWS S3 Bucket

The results will be uploaded directly to the S3 bucket configured in your **`.env`** file. You must have your AWS credentials (e.g., `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) configured in the `.env` file for this to work.

```
python run.py --start-date "YYYY-MM-DD" --output-aws
```

---

## ⚙️ Additional Flags

You can append these optional flags to any of the command-line execution options above:

| Flag | Description |
| :--- | :--- |
| `--verbose` | Adds additional print outputs to the console, useful for **debugging** issues. |
| `--visible` | Removes the default **headless** setting for the web browser, allowing you to **watch the scraping process** in real-time. |