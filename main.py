import requests
import yaml
import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Table, TableStyle,
                                 Paragraph, Spacer, PageBreak, Frame, Image, HRFlowable)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from datetime import datetime, timedelta

# Define colors to match the example reports
HEADER_BLUE = colors.HexColor('#4A90A4')
LIGHT_BLUE_ROW = colors.HexColor('#E8F4F8')
WHITE_ROW = colors.white
TEXT_DARK = colors.HexColor('#333333')


def get_date_range(days):
    """Calculate the date range for the report."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    return start_date, end_date


def format_date_range(start_date, end_date, days):
    """Format the date range string for display."""
    return f"{start_date.strftime('%b %d, %Y')} - {end_date.strftime('%b %d, %Y')}  {days} days"


def create_page_header(canvas, doc, config, report_title):
    """
    Create the header for each page with:
    - Logo and resource pool name on the left
    - Report title and date range on the right
    - Horizontal line separator
    """
    canvas.saveState()

    # Get configuration values
    logo_path = config.get('logoPath', 'images/logo.jpg')
    pool_name = config.get('resource_pool_name', 'Resource Pool')
    days = config.get('report_days', 30)
    start_date, end_date = get_date_range(days)

    page_width = letter[0]
    left_margin = doc.leftMargin
    right_margin = doc.rightMargin
    top_y = doc.height + doc.topMargin + 20

    # Draw logo on the left (if exists)
    logo_width = 50
    logo_height = 50
    if os.path.exists(logo_path):
        try:
            canvas.drawImage(logo_path, left_margin, top_y - logo_height,
                           width=logo_width, height=logo_height, preserveAspectRatio=True)
        except:
            pass

    # Draw resource pool name below/beside logo
    canvas.setFont('Helvetica', 10)
    canvas.setFillColor(TEXT_DARK)
    canvas.drawString(left_margin + logo_width + 10, top_y - 25, pool_name)

    # Draw report title on the right (right-aligned)
    canvas.setFont('Helvetica-Bold', 16)
    title_width = canvas.stringWidth(report_title, 'Helvetica-Bold', 16)
    canvas.drawString(page_width - right_margin - title_width, top_y - 15, report_title)

    # Draw date range on the right
    canvas.setFont('Helvetica', 10)
    date_range = format_date_range(start_date, end_date, days)
    date_width = canvas.stringWidth(date_range, 'Helvetica', 10)
    canvas.drawString(page_width - right_margin - date_width, top_y - 30, date_range)

    # Draw report generated timestamp
    generated_text = f"Report Generated: {datetime.now().strftime('%m/%d/%y, %I:%M %p')}"
    gen_width = canvas.stringWidth(generated_text, 'Helvetica', 10)
    canvas.drawString(page_width - right_margin - gen_width, top_y - 45, generated_text)

    # Draw horizontal line separator
    line_y = top_y - 55
    canvas.setStrokeColor(colors.HexColor('#CCCCCC'))
    canvas.setLineWidth(1)
    canvas.line(left_margin, line_y, page_width - right_margin, line_y)

    canvas.restoreState()


def create_header_function(config, report_title):
    """Factory function to create a header function with specific title."""
    def header(canvas, doc):
        create_page_header(canvas, doc, config, report_title)
    return header


def create_styled_table(data, col_widths=None, has_header=True):
    """
    Create a table with styling matching the example reports:
    - Light grey header with bold text
    - Alternating light blue and white rows
    - No grid lines (or very subtle ones)
    """
    table = Table(data, colWidths=col_widths)

    style_commands = [
        # Header styling
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F0F0F0')),
        ('TEXTCOLOR', (0, 0), (-1, 0), TEXT_DARK),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),

        # Body styling
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 6),

        # Alignment
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (-1, 0), (-1, -1), 'RIGHT'),  # Last column right-aligned (savings)
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),

        # Subtle grid
        ('LINEBELOW', (0, 0), (-1, 0), 0.5, colors.HexColor('#CCCCCC')),
    ]

    # Add alternating row colors
    if has_header:
        for i in range(1, len(data)):
            if i % 2 == 0:
                style_commands.append(('BACKGROUND', (0, i), (-1, i), LIGHT_BLUE_ROW))
            else:
                style_commands.append(('BACKGROUND', (0, i), (-1, i), WHITE_ROW))

    table.setStyle(TableStyle(style_commands))
    return table


def create_summary_page(cpu_savings, memory_savings, storage_savings, config, styles):
    """
    Create the summary page with icons for each category and total savings.
    """
    elements = []

    # Total savings
    total_savings = cpu_savings + memory_savings + storage_savings

    # Total Potential Savings header
    total_style = ParagraphStyle(
        'TotalSavings',
        parent=styles['Normal'],
        fontSize=14,
        fontName='Helvetica-Bold',
        textColor=TEXT_DARK,
        spaceAfter=20
    )
    elements.append(Paragraph(f"Total Potential Savings ${total_savings:,.2f}", total_style))
    elements.append(Spacer(1, 20))

    # Category items with icons
    categories = [
        ("CPU", cpu_savings, config.get('icons', {}).get('cpu')),
        ("Memory", memory_savings, config.get('icons', {}).get('memory')),
        ("Storage", storage_savings, config.get('icons', {}).get('storage')),
        ("Abandoned VM Images", 0.00, None),
        ("Powered Off VMs", 0.00, None),
        ("Unused Template Images", 0.00, None),
        ("Snapshots", 0.00, None),
        ("Potential Zombie VMs", 0.00, None),
    ]

    category_style = ParagraphStyle(
        'Category',
        parent=styles['Normal'],
        fontSize=12,
        fontName='Helvetica-Bold',
        textColor=TEXT_DARK,
        leftIndent=60
    )

    for name, savings, icon_path in categories:
        # Add icon if available and exists
        if icon_path and os.path.exists(icon_path):
            try:
                icon = Image(icon_path, width=40, height=40)
                elements.append(icon)
            except:
                pass

        elements.append(Paragraph(f"{name} ${savings:,.2f}", category_style))
        elements.append(Spacer(1, 15))

    return elements


def create_cpu_report_page(results, config, styles):
    """
    Create the CPU Optimization Report page with:
    - Total Potential Savings header
    - Table with VM, Utilization, Peak Utilization, Recommendations, Savings
    """
    elements = []

    # Calculate total CPU savings
    total_savings = sum(r.get('Savings', {}).get('CPU_Monthly', 0) for r in results)

    # Total Potential Savings header
    total_style = ParagraphStyle(
        'TotalSavings',
        parent=styles['Normal'],
        fontSize=14,
        fontName='Helvetica-Bold',
        textColor=TEXT_DARK,
        spaceAfter=20
    )
    elements.append(Paragraph(f"Total Potential Savings ${total_savings:,.2f}", total_style))
    elements.append(Spacer(1, 12))

    # Create table data
    table_data = [["Virtual Machine", "Utilization", "Peak Utilization", "CPU Recommendations", "Saving($/Month)"]]

    for result in results:
        hostname = result.get('Hostname', '')
        cpu_percent = result.get('CPUUtilization', 0)
        cpu_used_mhz = result.get('CPUUsedMHz', 0)
        cpu_total_mhz = result.get('CPUTotalMHz', 0)
        peak_util = result.get('PeakCPU', 0)
        current_cores = result.get('CurrentCores', 0)
        recommended_cores = result.get('RecommendedCores', current_cores)
        monthly_savings = result.get('Savings', {}).get('CPU_Monthly', 0)

        # Format utilization string like "5.57% (555.9 MHz of 10 GHz)"
        if cpu_total_mhz > 1000:
            total_str = f"{cpu_total_mhz/1000:.1f} GHz"
        else:
            total_str = f"{cpu_total_mhz:.1f} MHz"

        if cpu_used_mhz > 1000:
            used_str = f"{cpu_used_mhz/1000:.1f} GHz"
        else:
            used_str = f"{cpu_used_mhz:.1f} MHz"

        utilization = f"{cpu_percent:.2f}% ({used_str} of {total_str})"

        # Format peak utilization
        if peak_util > 1000:
            peak_str = f"{peak_util/1000:.1f} GHz"
        else:
            peak_str = f"{peak_util:.1f} MHz"

        # Format recommendation
        if recommended_cores != current_cores:
            recommendation = f"Decrease CPU Allocation from {current_cores} to {recommended_cores}"
        else:
            recommendation = "Right-sized"

        table_data.append([
            f"    {hostname}",  # Indent for icon space
            utilization,
            peak_str,
            recommendation,
            f"{monthly_savings:.2f}"
        ])

    # Create and add table
    col_widths = [1.5*inch, 1.6*inch, 1.1*inch, 2.2*inch, 1.1*inch]
    table = create_styled_table(table_data, col_widths)
    elements.append(table)

    return elements, total_savings


def create_memory_report_page(results, config, styles):
    """
    Create the Memory Optimization Report page.
    """
    elements = []

    # Calculate total Memory savings
    total_savings = sum(r.get('Savings', {}).get('Memory_Monthly', 0) for r in results)

    # Total Potential Savings header
    total_style = ParagraphStyle(
        'TotalSavings',
        parent=styles['Normal'],
        fontSize=14,
        fontName='Helvetica-Bold',
        textColor=TEXT_DARK,
        spaceAfter=20
    )
    elements.append(Paragraph(f"Total Potential Savings ${total_savings:,.2f}", total_style))
    elements.append(Spacer(1, 12))

    # Create table data
    table_data = [["Virtual Machine", "Utilization", "Peak Utilization", "Memory Recommendations", "Saving($/Month)"]]

    for result in results:
        hostname = result.get('Hostname', '')
        mem_percent = result.get('averageMemoryUtil', 0)
        mem_used_gb = result.get('MemoryUsedGB', 0)
        mem_total_gb = result.get('MemoryTotalGB', 0)
        peak_util_gb = result.get('PeakMemoryGB', mem_used_gb)
        recommended_mem = result.get('RecommendedMemoryGB', mem_total_gb)
        monthly_savings = result.get('Savings', {}).get('Memory_Monthly', 0)

        # Format utilization string like "74.99% (3 GB of 4 GB)"
        utilization = f"{mem_percent:.2f}% ({mem_used_gb:.1f} GB of {mem_total_gb:.1f} GB)"

        # Format peak utilization
        peak_str = f"{peak_util_gb:.1f} GB"

        # Format recommendation
        if recommended_mem != mem_total_gb:
            recommendation = f"Decrease Memory Allocation from {mem_total_gb:.1f} GB to {recommended_mem:.1f} GB"
        else:
            recommendation = "Right-sized"

        table_data.append([
            f"    {hostname}",
            utilization,
            peak_str,
            recommendation,
            f"{monthly_savings:.2f}"
        ])

    # Create and add table
    col_widths = [1.3*inch, 1.5*inch, 1.0*inch, 2.5*inch, 1.2*inch]
    table = create_styled_table(table_data, col_widths)
    elements.append(table)

    return elements, total_savings


def create_storage_report_page(storage_results, config, styles):
    """
    Create the Storage Optimization Report page with hierarchical VM/drive structure.
    """
    elements = []

    # Calculate total Storage savings
    total_savings = sum(r.get('Savings', {}).get('Storage_Monthly', 0) for r in storage_results)

    # Total Potential Savings header
    total_style = ParagraphStyle(
        'TotalSavings',
        parent=styles['Normal'],
        fontSize=14,
        fontName='Helvetica-Bold',
        textColor=TEXT_DARK,
        spaceAfter=20
    )
    elements.append(Paragraph(f"Total Potential Savings ${total_savings:,.2f}", total_style))
    elements.append(Spacer(1, 12))

    # Create cell style for wrapping text
    cell_style = ParagraphStyle(
        'CellStyle',
        parent=styles['Normal'],
        fontSize=9,
        leading=11
    )

    # Create table data with Paragraph objects for text wrapping
    table_data = [["Virtual Machine", "Utilization", "Storage Recommendations", "Modify Recommendation", "Saving($/Month)"]]

    # Group storage by hostname
    storage_by_host = {}
    for result in storage_results:
        hostname = result.get('Hostname', '')
        mount_point = result.get('MountPoint', '/')
        if hostname not in storage_by_host:
            storage_by_host[hostname] = []
        storage_by_host[hostname].append(result)

    for hostname, drives in storage_by_host.items():
        # Add hostname row
        total_used = sum(d.get('DiskUsedGB', 0) for d in drives)
        total_size = sum(d.get('DiskTotalGB', 0) for d in drives)
        if total_size > 0:
            total_percent = (total_used / total_size) * 100
        else:
            total_percent = 0

        table_data.append([
            Paragraph(f"&nbsp;&nbsp;{hostname}", cell_style),
            Paragraph(f"{total_percent:.2f}% ({total_used:.1f} GB of {total_size:.1f} GB)", cell_style),
            "",
            "",
            ""
        ])

        # Add drive rows
        for drive in drives:
            mount = drive.get('MountPoint', '/')
            used_gb = drive.get('DiskUsedGB', 0)
            total_gb = drive.get('DiskTotalGB', 0)
            if total_gb > 0:
                percent = (used_gb / total_gb) * 100
            else:
                percent = 0
            recommended_size = drive.get('RecommendedSizeGB', total_gb)
            monthly_savings = drive.get('Savings', {}).get('Storage_Monthly', 0)

            # Format recommendation
            if recommended_size != total_gb and recommended_size > 0:
                recommendation = Paragraph(f"Change size of {mount} from {total_gb:.1f} GB to {recommended_size:.0f} GB", cell_style)
                modify_rec = Paragraph("Credentials required.", cell_style)
            else:
                recommendation = ""
                modify_rec = ""

            table_data.append([
                Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{mount}", cell_style),
                Paragraph(f"{percent:.2f}% ({used_gb:.1f} GB of {total_gb:.1f} GB)", cell_style),
                recommendation,
                modify_rec,
                f"{monthly_savings:.2f}"
            ])

    # Create and add table with wider columns
    col_widths = [1.1*inch, 1.6*inch, 2.0*inch, 1.3*inch, 1.0*inch]
    table = create_styled_table(table_data, col_widths)
    elements.append(table)

    return elements, total_savings


def load_config(config_file='config.yaml'):
    """Load configuration from a YAML file."""
    with open(config_file, 'r') as file:
        return yaml.safe_load(file)


def fetch_new_relic_data(api_key, account_id):
    """
    Fetch data from New Relic's API using GraphQL queries.
    Returns system metrics and storage metrics.
    """
    url = "https://api.newrelic.com/graphql"
    headers = {
        "Content-Type": "application/json",
        "API-Key": api_key
    }

    # Query for system metrics including peak utilization
    query1 = f"""
    {{
      actor {{
        account(id: {account_id}) {{
          nrql(query: "SELECT average(cpuPercent), max(cpuPercent) as 'peakCpuPercent', average(memoryUsedPercent), max(memoryUsedPercent) as 'peakMemoryPercent', average(diskUtilizationPercent), average(diskFreePercent), average(diskTotalBytes), average(memoryUsedBytes), average(memoryTotalBytes), average(diskUsedBytes), latest(coreCount), latest(instanceType), average(loadAverageOneMinute), average(loadAverageFifteenMinute), average(processorCount) FROM SystemSample SINCE 30 days ago FACET hostname") {{
            results
          }}
        }}
      }}
    }}
    """

    try:
        response1 = requests.post(url, headers=headers, json={"query": query1})
        response1.raise_for_status()
        response_json1 = response1.json()
        if 'errors' in response_json1:
            raise ValueError(f"API Error: {response_json1['errors']}")
    except requests.exceptions.RequestException as e:
        print(f"Network error: {e}")
        return None, None
    except ValueError as e:
        print(e)
        return None, None

    # Query for storage data with mount points
    query2 = f"""
    {{
      actor {{
        account(id: {account_id}) {{
          nrql(query: "FROM StorageSample SELECT latest(diskUsedPercent) as 'currentPercent', latest(diskUsedBytes) as 'diskUsedBytes', latest(diskTotalBytes) as 'diskTotalBytes', latest(mountPoint) as 'mountPoint', predictLinear(diskUsedPercent, 1 week) as 'weekEstimate', predictLinear(diskUsedPercent, 1 month) as 'monthEstimate', predictLinear(diskUsedPercent, 3 months) as 'quarterEstimate' FACET hostname, mountPoint SINCE 30 days ago") {{
            results
          }}
        }}
      }}
    }}
    """

    try:
        response2 = requests.post(url, headers=headers, json={"query": query2})
        response2.raise_for_status()
        response_json2 = response2.json()
        if 'errors' in response_json2:
            raise ValueError(f"API Error: {response_json2['errors']}")
    except requests.exceptions.RequestException as e:
        print(f"Network error: {e}")
        return response_json1, None
    except ValueError as e:
        print(e)
        return response_json1, None

    return response_json1, response_json2


def analyze_usage(data, config):
    """
    Analyze CPU and Memory usage data and generate recommendations.
    Returns results formatted for the new report style.
    """
    CPU_OVER_THRESHOLD = 80
    CPU_UNDER_THRESHOLD = 20
    MEMORY_OVER_THRESHOLD = 80
    MEMORY_UNDER_THRESHOLD = 20

    analyzed_results = []

    for result in data['data']['actor']['account']['nrql']['results']:
        hostname = result.get('facet', 'Unknown')

        # CPU metrics
        current_cores = int(result.get('latest.coreCount', 0) or result.get('average.processorCount', 2))
        avg_cpu_percent = result.get('average.cpuPercent', 0) or 0
        peak_cpu_percent = result.get('peakCpuPercent', avg_cpu_percent) or avg_cpu_percent

        # Estimate MHz values (assuming ~2.5 GHz per core as typical)
        mhz_per_core = 2500
        cpu_total_mhz = current_cores * mhz_per_core
        cpu_used_mhz = (avg_cpu_percent / 100) * cpu_total_mhz
        peak_cpu_mhz = (peak_cpu_percent / 100) * cpu_total_mhz

        # Memory metrics
        mem_used_bytes = result.get('average.memoryUsedBytes', 0) or 0
        mem_total_bytes = result.get('average.memoryTotalBytes', 0) or 0
        avg_mem_percent = result.get('average.memoryUsedPercent', 0) or 0
        peak_mem_percent = result.get('peakMemoryPercent', avg_mem_percent) or avg_mem_percent

        mem_used_gb = mem_used_bytes / (1024 ** 3)
        mem_total_gb = mem_total_bytes / (1024 ** 3) if mem_total_bytes > 0 else (mem_used_gb / (avg_mem_percent / 100) if avg_mem_percent > 0 else 4)
        peak_mem_gb = (peak_mem_percent / 100) * mem_total_gb

        # Determine recommendations
        recommended_cores = current_cores
        recommended_mem_gb = mem_total_gb
        cpu_monthly_savings = 0
        mem_monthly_savings = 0

        # CPU recommendation logic
        if avg_cpu_percent < CPU_UNDER_THRESHOLD and current_cores > 1:
            # Oversized - recommend fewer cores
            recommended_cores = max(1, int(current_cores * (peak_cpu_percent / 100 * 1.5)))
            if recommended_cores < current_cores:
                # Calculate savings (simplified - would need actual pricing data)
                cpu_monthly_savings = (current_cores - recommended_cores) * 10  # $10/core/month estimate

        # Memory recommendation logic
        if avg_mem_percent < MEMORY_UNDER_THRESHOLD and mem_total_gb > 1:
            # Oversized - recommend less memory
            recommended_mem_gb = max(1, peak_mem_gb * 1.3)  # Add 30% buffer
            if recommended_mem_gb < mem_total_gb:
                # Calculate savings (simplified)
                mem_monthly_savings = (mem_total_gb - recommended_mem_gb) * 5  # $5/GB/month estimate

        analyzed_results.append({
            "Hostname": hostname,
            "CPUUtilization": avg_cpu_percent,
            "CPUUsedMHz": cpu_used_mhz,
            "CPUTotalMHz": cpu_total_mhz,
            "PeakCPU": peak_cpu_mhz,
            "CurrentCores": current_cores,
            "RecommendedCores": recommended_cores,
            "averageMemoryUtil": avg_mem_percent,
            "MemoryUsedGB": mem_used_gb,
            "MemoryTotalGB": mem_total_gb,
            "PeakMemoryGB": peak_mem_gb,
            "RecommendedMemoryGB": recommended_mem_gb,
            "Savings": {
                "CPU_Monthly": cpu_monthly_savings,
                "Memory_Monthly": mem_monthly_savings
            }
        })

    return analyzed_results


def analyze_storage(data, config):
    """
    Analyze storage data and generate recommendations.
    Returns results formatted for the new report style with mount points.
    """
    storage_results = []

    if data is None:
        return storage_results

    for result in data['data']['actor']['account']['nrql']['results']:
        facet = result.get('facet', ['Unknown', '/'])
        if isinstance(facet, list):
            hostname = facet[0] if len(facet) > 0 else 'Unknown'
            mount_point = facet[1] if len(facet) > 1 else '/'
        else:
            hostname = facet
            mount_point = '/'

        disk_used_bytes = result.get('diskUsedBytes', 0) or 0
        disk_total_bytes = result.get('diskTotalBytes', 0) or 0
        current_percent = result.get('currentPercent', 0) or 0

        disk_used_gb = disk_used_bytes / (1024 ** 3)
        disk_total_gb = disk_total_bytes / (1024 ** 3)

        # Recommendation logic
        recommended_size_gb = disk_total_gb
        storage_monthly_savings = 0

        # If utilization is low, recommend smaller disk
        if current_percent < 30 and disk_total_gb > 50:
            # Recommend size that would give ~70% utilization
            recommended_size_gb = max(disk_used_gb * 1.5, 50)  # Minimum 50GB or 150% of used
            if recommended_size_gb < disk_total_gb:
                # Calculate savings (simplified - $0.10/GB/month estimate)
                storage_monthly_savings = (disk_total_gb - recommended_size_gb) * 0.10

        storage_results.append({
            "Hostname": hostname,
            "MountPoint": mount_point,
            "DiskUsedGB": disk_used_gb,
            "DiskTotalGB": disk_total_gb,
            "DiskPercent": current_percent,
            "RecommendedSizeGB": recommended_size_gb,
            "WeekEstimate": result.get('weekEstimate', current_percent),
            "MonthEstimate": result.get('monthEstimate', current_percent),
            "QuarterEstimate": result.get('quarterEstimate', current_percent),
            "Savings": {
                "Storage_Monthly": storage_monthly_savings
            }
        })

    return storage_results


def generate_pdf_report(results, storage_results, config, output_file="report.pdf"):
    """
    Generate the PDF report with all sections matching the example format.
    """
    from reportlab.platypus import NextPageTemplate

    doc = BaseDocTemplate(output_file, pagesize=letter,
                          leftMargin=0.5*inch, rightMargin=0.5*inch,
                          topMargin=1*inch, bottomMargin=0.5*inch)

    # Create frames for different page types
    frame = Frame(doc.leftMargin, doc.bottomMargin,
                  doc.width, doc.height - 0.5*inch, id='normal')

    # Page templates for different report sections
    summary_header = create_header_function(config, "VM Resources Optimization Report")
    cpu_header = create_header_function(config, "CPU Optimization Report")
    memory_header = create_header_function(config, "Memory Optimization Report")
    storage_header = create_header_function(config, "Storage Optimization Report")

    summary_template = PageTemplate(id='summary', frames=frame, onPage=summary_header)
    cpu_template = PageTemplate(id='cpu', frames=frame, onPage=cpu_header)
    memory_template = PageTemplate(id='memory', frames=frame, onPage=memory_header)
    storage_template = PageTemplate(id='storage', frames=frame, onPage=storage_header)

    doc.addPageTemplates([summary_template, cpu_template, memory_template, storage_template])

    elements = []
    styles = getSampleStyleSheet()

    # Generate report sections and collect savings
    cpu_elements, cpu_savings = create_cpu_report_page(results, config, styles)
    memory_elements, memory_savings = create_memory_report_page(results, config, styles)
    storage_elements, storage_savings = create_storage_report_page(storage_results, config, styles)

    # Summary page (first) - starts with summary template
    summary_elements = create_summary_page(cpu_savings, memory_savings, storage_savings, config, styles)
    elements.extend(summary_elements)

    # CPU page - switch template BEFORE adding content
    elements.append(NextPageTemplate('cpu'))
    elements.append(PageBreak())
    elements.extend(cpu_elements)

    # Memory page - switch template BEFORE adding content
    elements.append(NextPageTemplate('memory'))
    elements.append(PageBreak())
    elements.extend(memory_elements)

    # Storage page - switch template BEFORE adding content
    elements.append(NextPageTemplate('storage'))
    elements.append(PageBreak())
    elements.extend(storage_elements)

    # Build the PDF
    doc.build(elements)
    print(f"PDF Report generated: {output_file}")


def generate_demo_data():
    """Generate sample data for demo/testing purposes."""
    demo_results = [
        {
            "Hostname": "AFMSyncService - AK",
            "CPUUtilization": 5.57,
            "CPUUsedMHz": 555.9,
            "CPUTotalMHz": 10000,
            "PeakCPU": 2200,
            "CurrentCores": 4,
            "RecommendedCores": 2,
            "averageMemoryUtil": 45.0,
            "MemoryUsedGB": 3.6,
            "MemoryTotalGB": 8.0,
            "PeakMemoryGB": 4.2,
            "RecommendedMemoryGB": 8.0,
            "Savings": {"CPU_Monthly": 20.0, "Memory_Monthly": 0.0}
        },
        {
            "Hostname": "APRSERVER106 - SC",
            "CPUUtilization": 2.93,
            "CPUUsedMHz": 292.4,
            "CPUTotalMHz": 10000,
            "PeakCPU": 3700,
            "CurrentCores": 4,
            "RecommendedCores": 3,
            "averageMemoryUtil": 62.0,
            "MemoryUsedGB": 4.96,
            "MemoryTotalGB": 8.0,
            "PeakMemoryGB": 5.5,
            "RecommendedMemoryGB": 8.0,
            "Savings": {"CPU_Monthly": 10.0, "Memory_Monthly": 0.0}
        },
        {
            "Hostname": "ESGAGS10",
            "CPUUtilization": 2.27,
            "CPUUsedMHz": 95,
            "CPUTotalMHz": 4200,
            "PeakCPU": 1500,
            "CurrentCores": 2,
            "RecommendedCores": 1,
            "averageMemoryUtil": 74.99,
            "MemoryUsedGB": 3.0,
            "MemoryTotalGB": 4.0,
            "PeakMemoryGB": 3.0,
            "RecommendedMemoryGB": 3.7,
            "Savings": {"CPU_Monthly": 10.0, "Memory_Monthly": 1.5}
        },
        {
            "Hostname": "londoncw",
            "CPUUtilization": 7.26,
            "CPUUsedMHz": 724,
            "CPUTotalMHz": 10000,
            "PeakCPU": 4400,
            "CurrentCores": 4,
            "RecommendedCores": 3,
            "averageMemoryUtil": 55.0,
            "MemoryUsedGB": 8.8,
            "MemoryTotalGB": 16.0,
            "PeakMemoryGB": 10.0,
            "RecommendedMemoryGB": 16.0,
            "Savings": {"CPU_Monthly": 10.0, "Memory_Monthly": 0.0}
        },
        {
            "Hostname": "spider",
            "CPUUtilization": 8.47,
            "CPUUsedMHz": 2500,
            "CPUTotalMHz": 29900,
            "PeakCPU": 5200,
            "CurrentCores": 12,
            "RecommendedCores": 3,
            "averageMemoryUtil": 35.0,
            "MemoryUsedGB": 11.2,
            "MemoryTotalGB": 32.0,
            "PeakMemoryGB": 14.0,
            "RecommendedMemoryGB": 32.0,
            "Savings": {"CPU_Monthly": 90.0, "Memory_Monthly": 0.0}
        },
    ]

    demo_storage = [
        {
            "Hostname": "londoncw",
            "MountPoint": "C:\\",
            "DiskUsedGB": 111.3,
            "DiskTotalGB": 149.5,
            "DiskPercent": 74.44,
            "RecommendedSizeGB": 129,
            "Savings": {"Storage_Monthly": 2.05}
        },
        {
            "Hostname": "londoncw",
            "MountPoint": "E:\\",
            "DiskUsedGB": 57.9,
            "DiskTotalGB": 200.0,
            "DiskPercent": 28.95,
            "RecommendedSizeGB": 67,
            "Savings": {"Storage_Monthly": 13.30}
        },
        {
            "Hostname": "ESGAGS10",
            "MountPoint": "C:\\",
            "DiskUsedGB": 45.0,
            "DiskTotalGB": 100.0,
            "DiskPercent": 45.0,
            "RecommendedSizeGB": 100.0,
            "Savings": {"Storage_Monthly": 0.0}
        },
    ]

    return demo_results, demo_storage


def main():
    """Main function to orchestrate report generation."""
    import sys

    # Check for --demo flag
    demo_mode = '--demo' in sys.argv

    # Load configuration
    config = load_config()

    if demo_mode:
        print("Running in DEMO mode with sample data...")
        analyzed_results, storage_results = generate_demo_data()
    else:
        # Get API key and account ID
        api_key = config.get('api_key')
        account_id = config.get('account_id', 4120837)

        if not api_key or api_key == '<YOUR NR USER APIKEY>':
            print("Error: Please set your New Relic API key in config.yaml")
            print("Tip: Use --demo flag to generate a sample report without API access")
            return

        # Fetch data from New Relic
        print("Fetching data from New Relic API...")
        system_data, storage_data = fetch_new_relic_data(api_key, account_id)

        if system_data is None:
            print("Failed to fetch system data from New Relic API.")
            print("Tip: Use --demo flag to generate a sample report without API access")
            return

        # Analyze the data
        print("Analyzing usage data...")
        analyzed_results = analyze_usage(system_data, config)
        storage_results = analyze_storage(storage_data, config)

    # Generate the report
    print("Generating PDF report...")
    output_file = config.get('output_file', 'optimization_report.pdf')
    generate_pdf_report(analyzed_results, storage_results, config, output_file)

    print(f"Report generation complete! Output: {output_file}")


if __name__ == "__main__":
    main()
