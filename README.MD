# Monthly Usage Report Generator

This script generates a PDF report of monthly usage data fetched from New Relic's API. The report includes CPU, memory, and disk utilization analysis, along with recommendations for optimal instance sizes and cost savings.
This is a simple prototype and is meant to show how you can easily fetch data from New Relic's API and generating a PDF report. 
It can be extended to include more detailed analysis, additional metrics, and customization options.

**Note**: This script is for educational purposes only and should not be used in production environments 
without proper testing and validation. The script is provided as-is, without any warranties or guarantees.

## Features

- Fetches data from New Relic's API using GraphQL queries.
- Analyzes CPU and memory usage to suggest optimal instance sizes.
- Forecasts disk usage based on historical data.
- Generates a PDF report with a cover page, analysis sections, and a table of contents.
- Includes headers with logos and page numbers in the report.

## Setup

### Prerequisites

- Python 3.x
- `pip` (Python package installer)

### Installation

1. Clone the repository:

    ```sh
    git clone https://github.com/yourusername/your-repo.git
    cd your-repo
    ```

2. Install the required Python packages:

    ```sh
    pip install -r requirements.txt
    ```

3. Configure the `config.yaml` file:

    - Copy the example configuration file:

        ```sh
        cp config_example.yaml config.yaml
        ```

    - Edit `config.yaml` to include your New Relic API key and the path to your logo image:

        ```yaml
        api_key: <YOUR NR USER APIKEY>
        logoPath: "images/logo.jpg"
        sizes:
          - name: "t3.micro"
            cpu: 2
            memory: 1  # in GiB
            disk: 0   # EBS-Only
            hourly_cost: 0.0104
          # Add more instance sizes as needed
        ```

## Usage

1. Run the script:

    ```sh
    python main.py
    ```

2. The script will fetch data from New Relic, analyze it, and generate a PDF report named `report.pdf` in the current directory.

## How It Works

1. **Data Fetching**: The script uses the `requests` library to send GraphQL queries to New Relic's API and fetch system and storage sample data.

2. **Data Analysis**: The script analyzes the fetched data to determine the current utilization of CPU, memory, and disk. It then suggests optimal instance sizes based on predefined thresholds and configurations.

3. **PDF Generation**: The script uses the `reportlab` library to generate a PDF report. The report includes:
    - A cover page with a logo and title.
    - Sections for CPU and memory usage analysis, and disk utilization forecast.
    - Tables with recommendations and estimated cost savings.
    - Headers with logos and page numbers on each page (except the cover page).

## Example Configuration

Here is an example of the `config.yaml` file:

```yaml
api_key: <YOUR NR USER APIKEY>
logoPath: "images/logo.jpg"
sizes:
  - name: "t3.micro"
    cpu: 2
    memory: 1  # in GiB
    disk: 0   # EBS-Only
    hourly_cost: 0.0104
  - name: "t3.small"
    cpu: 2
    memory: 2  # in GiB
    disk: 0   # EBS-Only
    hourly_cost: 0.0208
  # Add more instance sizes as needed
```

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.