"""
Data Export Manager - Export conversations and data in multiple formats
Supports: PDF, JSON, CSV, TXT
"""

import json
import csv
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path
import io

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("[WARNING] reportlab not available - PDF export disabled")


class ExportManager:
    """Manages data exports in multiple formats"""
    
    def __init__(self):
        """Initialize export manager"""
        self.export_dir = Path("exports")
        self.export_dir.mkdir(exist_ok=True)
    
    def export_to_json(
        self,
        data: List[Dict],
        filename: Optional[str] = None
    ) -> str:
        """
        Export data to JSON
        
        Args:
            data: List of dictionaries to export
            filename: Optional filename (auto-generated if None)
            
        Returns:
            Path to exported file
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"export_{timestamp}.json"
        
        filepath = self.export_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        
        return str(filepath)
    
    def export_to_csv(
        self,
        data: List[Dict],
        filename: Optional[str] = None
    ) -> str:
        """
        Export data to CSV
        
        Args:
            data: List of dictionaries to export
            filename: Optional filename (auto-generated if None)
            
        Returns:
            Path to exported file
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"export_{timestamp}.csv"
        
        filepath = self.export_dir / filename
        
        if not data:
            # Create empty CSV with headers
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["No data available"])
            return str(filepath)
        
        # Get all unique keys from all dictionaries
        fieldnames = set()
        for item in data:
            fieldnames.update(item.keys())
        fieldnames = sorted(list(fieldnames))
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for item in data:
                # Convert all values to strings
                row = {k: str(v) if v is not None else '' for k, v in item.items()}
                writer.writerow(row)
        
        return str(filepath)
    
    def export_to_txt(
        self,
        data: List[Dict],
        filename: Optional[str] = None
    ) -> str:
        """
        Export data to plain text
        
        Args:
            data: List of dictionaries to export
            filename: Optional filename (auto-generated if None)
            
        Returns:
            Path to exported file
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"export_{timestamp}.txt"
        
        filepath = self.export_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("DATA EXPORT\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            
            for i, item in enumerate(data, 1):
                f.write(f"Entry {i}:\n")
                f.write("-" * 80 + "\n")
                for key, value in item.items():
                    f.write(f"{key}: {value}\n")
                f.write("\n")
        
        return str(filepath)
    
    def export_to_pdf(
        self,
        data: List[Dict],
        title: str = "Data Export",
        filename: Optional[str] = None
    ) -> Optional[str]:
        """
        Export data to PDF
        
        Args:
            data: List of dictionaries to export
            title: PDF title
            filename: Optional filename (auto-generated if None)
            
        Returns:
            Path to exported file or None if reportlab not available
        """
        if not REPORTLAB_AVAILABLE:
            return None
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"export_{timestamp}.pdf"
        
        filepath = self.export_dir / filename
        
        # Create PDF
        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Container for PDF content
        story = []
        
        # Define styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor='#5865F2',
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        # Add title
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 0.2 * inch))
        
        # Add generation date
        date_text = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        story.append(Paragraph(date_text, styles['Normal']))
        story.append(Spacer(1, 0.3 * inch))
        
        # Add data
        for i, item in enumerate(data, 1):
            # Entry header
            entry_title = Paragraph(f"<b>Entry {i}</b>", styles['Heading2'])
            story.append(entry_title)
            story.append(Spacer(1, 0.1 * inch))
            
            # Entry content
            for key, value in item.items():
                text = f"<b>{key}:</b> {str(value)}"
                story.append(Paragraph(text, styles['Normal']))
                story.append(Spacer(1, 0.05 * inch))
            
            story.append(Spacer(1, 0.2 * inch))
            
            # Page break every 5 entries
            if i % 5 == 0 and i < len(data):
                story.append(PageBreak())
        
        # Build PDF
        doc.build(story)
        
        return str(filepath)
    
    def export_conversations(
        self,
        conversations: List[Dict],
        format: str = "json"
    ) -> Optional[str]:
        """
        Export conversations in specified format
        
        Args:
            conversations: List of conversation dictionaries
            format: Export format (json, csv, txt, pdf)
            
        Returns:
            Path to exported file or None if failed
        """
        format = format.lower()
        
        if format == "json":
            return self.export_to_json(conversations)
        elif format == "csv":
            return self.export_to_csv(conversations)
        elif format == "txt":
            return self.export_to_txt(conversations)
        elif format == "pdf":
            return self.export_to_pdf(conversations, title="Conversation Export")
        else:
            raise ValueError(f"Unsupported format: {format}. Use: json, csv, txt, pdf")


