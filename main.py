import requests
import yaml
from reportlab.lib.pagesizes import letter
from reportlab.platypus import BaseDocTemplate, PageTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Frame, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
from datetime import datetime

# Header function to add the current date and logo to each page
def header(canvas, doc):
    canvas.saveState()
    styles = getSampleStyleSheet()
    # Add logo  to the header
    logo = "images/LOCALlogo.jpg"
    # Adjust the position of the logo as needed
    canvas.drawImage(logo, doc.leftMargin, doc.height + doc.topMargin - 10, width=137.5*.5, height=75*.5)
    header_text = Paragraph(f"Report generated on: {datetime.now().strftime('%Y-%m-%d')}", styles['Normal'])
    w, h = header_text.wrap(doc.width, doc.topMargin)
    # Adjust the position of the header text as needed
    header_text.drawOn(canvas, doc.leftMargin + 150, doc.height + doc.topMargin - h)
    canvas.restoreState()

# Function to create the cover page
def create_cover_page(doc, styles):
    elements = []
    # Add the title and subtitle to the cover page
    cover_title = Paragraph("Monthly Usage Report", styles['Title'])
    cover_subtitle = Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d')}", styles['Normal'])
    # Add logo to the cover page
    logo = Image("images/logo.jpg", width=275, height=150)
    elements.append(Spacer(1, 0.5 * inch))
    # Add the elements to the cover page
    elements.append(logo)
    elements.append(Spacer(1, 0.5 * inch))
    # Add the title and subtitle to the cover page
    elements.append(cover_title)
    elements.append(Spacer(1, 0.5 * inch))
    # Add the subtitle to the cover page
    elements.append(cover_subtitle)
    elements.append(PageBreak())
    return elements

# Helper function to create tables with consistent styling
def create_table(data, header_color=colors.grey, text_color=colors.whitesmoke):
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), header_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), text_color),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold')
    ]))
    return table

# Load instance size configuration from a YAML file
def load_config(config_file='config.yaml'):
    with open(config_file, 'r') as file:
        return yaml.safe_load(file)

# Fetch data from New Relic's API using GraphQL queries with error handling
def fetch_new_relic_data(api_key):
    url = "https://api.newrelic.com/graphql"
    # Set the headers including the API key
    headers = {
        "Content-Type": "application/json",
        "API-Key": api_key
    }

    # First query to get system sample data
    query1 = """
    {
      actor {
        account(id: 4120837) {
          nrql(query: "SELECT average(cpuPercent), average(memoryUsedPercent), average(diskUtilizationPercent), average(diskFreePercent), average(diskTotalBytes),average(memoryUsedBytes),average(diskUsedBytes),latest(coreCount),latest(instanceType), average(loadAverageOneMinute), average(loadAverageFifteenMinute) FROM SystemSample SINCE 30 days ago FACET hostname") {
            results
          }
        }
      }
    }
    """
    try:
        # Send the first query
        response1 = requests.post(url, headers=headers, json={"query": query1})
        # Check for bad responses
        response1.raise_for_status()
        response_json1 = response1.json()
        # Check for errors in the response
        if 'errors' in response_json1:
            raise ValueError(f"API Error: {response_json1['errors']}")
    # Handle network errors
    except requests.exceptions.RequestException as e:
        print(f"Network error: {e}")
        return None, None
    # Handle API errors
    except ValueError as e:
        print(e)
        return None, None

    # Second query to get storage sample data
    query2 = """
    {
      actor {
        account(id: 4120837) {
          nrql(query: "FROM StorageSample SELECT latest(diskUsedPercent) as 'currentSize', predictLinear(diskUsedPercent, 1 week) as 'weekEstimateSize', predictLinear(diskUsedPercent, 1 month) as 'monthEstimateSize', predictLinear(diskUsedPercent, 3 months) as 'quarterEstimateSize' FACET hostname SINCE 30 days ago") {
            results
          }
        }
      }
    }
    """
    try:
        # Send the second query
        response2 = requests.post(url, headers=headers, json={"query": query2})
        # Raise an HTTPError for bad responses
        response2.raise_for_status()
        # Parse the JSON response
        response_json2 = response2.json()
        # Check for errors in the response
        if 'errors' in response_json2:
            raise ValueError(f"API Error: {response_json2['errors']}")
    # Handle network errors
    except requests.exceptions.RequestException as e:
        print(f"Network error: {e}")
        return response_json1, None
    # Handle API errors
    except ValueError as e:
        print(e)
        return response_json1, None
    # Return the response JSON objects
    return response_json1, response_json2

# Analyze usage data and suggest a lower allocation if possible
def analyze_usage(data, config):
    # Thresholds for CPU and memory utilization
    CPU_OVER_THRESHOLD = 80
    CPU_UNDER_THRESHOLD = 20
    MEMORY_OVER_THRESHOLD = 80
    MEMORY_UNDER_THRESHOLD = 20
    LOAD_OVER_FACTOR = 1.5

    analyzed_results = []
    # Iterate over the results and map the data for analysis
    for result in data['data']['actor']['account']['nrql']['results']:
        hostname = result['facet']
        current_cpu = int(result.get('latest.coreCount', 0))
        current_memory = result.get('average.memoryUsedBytes', 0) / (1024 ** 3)
        avg_cpu_util = result.get('average.cpuPercent', 0)
        avg_mem_util = result.get('average.memoryUsedPercent', 0)
        avg_load = result.get('average.loadAverageOneMinute', 0)
        current_instance_type = result.get('latest.instanceType', "Unknown")

        # Determine the status of the instance
        status = "Right-Sized"
        # Check if the instance is undersized or oversized
        if avg_cpu_util > CPU_OVER_THRESHOLD or avg_mem_util > MEMORY_OVER_THRESHOLD or avg_load > (LOAD_OVER_FACTOR * current_cpu):
            status = "Undersized"
        elif avg_cpu_util < CPU_UNDER_THRESHOLD and avg_mem_util < MEMORY_UNDER_THRESHOLD:
            status = "Oversized"

        best_match = None
        best_cost = float("inf")
        best_memory_match = None
        best_memory_cost = float("inf")

        # Find the best match for the instance sizes defined in the config
        for config_size in config['sizes']:
            config_cpu = config_size['cpu']
            config_memory = config_size['memory']
            config_cost = config_size['hourly_cost']
            # If is under or over sized, check if the config has a better size and calculate the cost savings
            if status == "Undersized" and config_cpu >= current_cpu and config_memory >= current_memory:
                if config_cost < best_cost:
                    best_match = config_size
                    best_cost = config_cost
            elif status == "Oversized" and config_cpu <= current_cpu and config_memory <= current_memory:
                if config_cost < best_cost:
                    best_match = config_size
                    best_cost = config_cost
            if status == "Undersized" and config_memory >= current_memory:
                if config_cost < best_memory_cost:
                    best_memory_match = config_size
                    best_memory_cost = config_cost
            elif status == "Oversized" and config_memory <= current_memory:
                if config_cost < best_memory_cost:
                    best_memory_match = config_size
                    best_memory_cost = config_cost

        # Append the analyzed result
        analyzed_results.append({
            "Hostname": hostname,
            "CPUUtilization": avg_cpu_util,
            "CurrentCores": current_cpu,
            "CurrentMemory": current_memory,
            "averageMemoryUtil": round(avg_mem_util, 2),
            "CPU": best_match['name'] if best_match else "No better match found",
            "Memory": best_memory_match['name'] if best_memory_match else "No better match found",
            "Savings": {
                "CPU": best_match['hourly_cost'] if best_match else 0,
                "Memory": best_memory_match['hourly_cost'] if best_memory_match else 0
            }
        })
    # Return the analyzed results
    return analyzed_results

# Forecast disk usage based on historical data
def forcast_usage(data, config):
    analyzed_results = []
    # Iterate over the results and map the data to
    for result in data['data']['actor']['account']['nrql']['results']:
        hostname = result['facet']
        currentSize = result['currentSize']
        current_instance_type = result.get('latest.instanceType', "Unknown")
        week_estimate = result['weekEstimateSize']
        month_estimate = result['monthEstimateSize']
        quarter_estimate = result['quarterEstimateSize']
        best_disk_match = None
        best_disk_cost = float("inf")

        # Find the best match for the disk size (Not Implemented in lieu of demonstrating the predictLinear for
        # forcaseing. This could be implemented in a similar way to the CPU and Memory analysis above)
        for config_size in config['sizes']:
            config_disk = config_size['disk']
            config_cost = config_size['hourly_cost']
            if config_disk >= currentSize:
                if config_cost < best_disk_cost:
                    best_disk_match = config_size
                    best_disk_cost = config_cost

        # Append the forecasted result into the data
        analyzed_results.append({
            "Hostname": hostname,
            "CurrentInstanceType": current_instance_type,
            "Disk": best_disk_match['name'] if best_disk_match else "No better match found",
            "Savings": {
                "Disk": best_disk_match['hourly_cost'] if best_disk_match else 0
            },
            "DiskUtilization": {
                "Current": currentSize,
                "WeekEstimate": week_estimate,
                "MonthEstimate": month_estimate,
                "QuarterEstimate": quarter_estimate
            }
        })
    # Return the analyzed results
    return analyzed_results

# Generate PDF report with the analyzed and forecasted data
def generate_pdf_report(results, forcastresults, output_file="report.pdf"):
    # Create a PDF document with a cover page and main content
    doc = BaseDocTemplate(output_file, pagesize=letter)
    # Define the frame for the content
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height - 2 * inch, id='normal')
    # Add the cover page template and main content template
    cover_template = PageTemplate(id='cover', frames=frame)  # Cover page template without header
    # Main content template with header
    main_template = PageTemplate(id='main', frames=frame, onPage=header)  # Main content template with header
    # Add the templates to the document
    doc.addPageTemplates([cover_template, main_template])

    elements = []
    styles = getSampleStyleSheet()

    # Add cover page
    elements.extend(create_cover_page(doc, styles))

    # Switch to main template for the rest of the document
    doc.handle_nextPageTemplate('main')

    # CPU Usage Analysis section
    elements.append(Paragraph("CPU Usage Analysis", styles['Title']))
    elements.append(Spacer(1, 12))
    # Create a table for the CPU data
    cpu_data = [["Hostname", "CPU %\n(Monthly)", "Recommended\nSize", "Est Savings\n(Hourly)", "Est Savings\n(Monthly)"]]
    for result in results:
        cpu_data.append([result["Hostname"], f"{result['CPUUtilization']:.2f}%", result["CPU"], f"${result['Savings'].get('CPU', 0):.2f}", f"${result['Savings'].get('CPU', 0) * 720:.2f}"])
    # Add the CPU data table to the elements
    elements.append(create_table(cpu_data))
    # Add a spacer for layout
    elements.append(Spacer(1, 24))
    # Add a page break to start a new section
    elements.append(PageBreak())

    # Memory Usage Analysis section
    elements.append(Paragraph("Memory Usage Analysis", styles['Title']))
    elements.append(Spacer(1, 12))
    # Create a table for the memory data
    memory_data = [["Hostname", "Mem Pct", "Recommended\nSize", "Est Savings\n(Hourly)", "Est Savings\n(Monthly)"]]
    for result in results:
        memory_data.append([result["Hostname"], f"{result['averageMemoryUtil']:.2f}%", result["Memory"], f"${result['Savings'].get('Memory', 0):.2f}", f"${result['Savings'].get('Memory', 0) * 720:.2f}"])
    # Add the memory data table to the elements
    elements.append(create_table(memory_data))
    elements.append(Spacer(1, 24))
    # Add a page break to start a new section
    elements.append(PageBreak())

    # Disk Utilization and Forecast section
    elements.append(Paragraph("Current Disk Utilization and Forecast", styles['Title']))
    elements.append(Spacer(1, 12))
    # Create a table for the disk utilization forecast data
    forcast = [["Hostname", "Current\nUtilization", "Week\nEstimate", "Month\nEstimate", "Quarter\nEstimate"]]
    for result in forcastresults:
        disk_util = result.get("DiskUtilization", {})
        week_estimate = min(max(disk_util.get('WeekEstimate', 0), 0), 100)
        month_estimate = min(max(disk_util.get('MonthEstimate', 0), 0), 100)
        quarter_estimate = min(max(disk_util.get('QuarterEstimate', 0), 0), 100)
        forcast.append([result["Hostname"], f"{disk_util.get('Current', 0):.2f}%", f"{week_estimate:.2f}%", f"{month_estimate:.2f}%", f"{quarter_estimate:.2f}%"])
    #
    table = create_table(forcast)
    # Add color coding to the disk utilization forecast table when thresholds are hit
    for row_idx, row in enumerate(forcast[1:], start=1):
        for col_idx, cell in enumerate(row[1:], start=1):
            value = float(cell.strip('%'))
            # If the value is over 90%, color it red, if over 80%, color it yellow
            if value > 90:
                table.setStyle(TableStyle([('BACKGROUND', (col_idx, row_idx), (col_idx, row_idx), colors.red)]))
            elif value > 80:
                table.setStyle(TableStyle([('BACKGROUND', (col_idx, row_idx), (col_idx, row_idx), colors.yellow)]))
    elements.append(table)
    # Add a spacer for layout
    elements.append(Spacer(1, 24))
    # build the PDF document with the elements
    doc.build(elements)
    # Print the success of the generated PDF report and location
    print(f"PDF Report generated: {output_file}")

# Main function to load config, fetch data, analyze it, and generate the PDF report
def main():
    # Load the configuration from the YAML file (config.yaml)
    config = load_config()
    # Fetch data from New Relic's API
    api_key = config['api_key']
    # Fetch data from New Relic's API (CPU and Memory usage data, and disk usage forecast data)
    data1, data2 = fetch_new_relic_data(api_key)
    # Check if the data was fetched successfully
    if data1 is None or data2 is None:
        print("Failed to fetch data from New Relic API.")
        return
    # Analyze the CPU and Memory usage data, and look for alternative configurations
    # (from options defined in config.yaml)
    analyzed_results = analyze_usage(data1, config)
    # Map the forcasted disk usage data (and potential to add sizing recommendations like CPU and Memory)
    forcast_results = forcast_usage(data2, config)
    # Generate the PDF report with the analyzed and forecasted data
    generate_pdf_report(analyzed_results, forcast_results)

if __name__ == "__main__":
    main()