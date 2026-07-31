import io
from datetime import datetime
from typing import Any, Dict, List, Optional
import pandas as pd


def _normalize_report_data(report_data: Any, *args, **kwargs) -> Dict[str, Any]:
    if isinstance(report_data, dict):
        return report_data
    # If positional args were passed (patient, metrics, medicines, alerts, ai_recs, trends)
    patient = report_data if report_data is not None else {}
    metrics = args[0] if len(args) > 0 else {}
    medicines = args[1] if len(args) > 1 else []
    alerts = args[2] if len(args) > 2 else []
    ai = args[3] if len(args) > 3 else []
    trends = args[4] if len(args) > 4 else []
    return {
        "patient": patient,
        "metrics": metrics,
        "medicines": medicines,
        "alerts": alerts,
        "ai": ai,
        "trends": trends,
    }


def generate_html_report(report_data: Any, *args, report_title: str = "Patient Health & Activity Report", **kwargs) -> str:
    """Generate a clean HTML report string suitable for browser printing or saving."""
    data = _normalize_report_data(report_data, *args, **kwargs)
    patient = data.get("patient", {}) or {}
    metrics = data.get("metrics", {}) or {}
    medicines = data.get("medicines", [])
    trends = data.get("trends", [])
    ai_recs = data.get("ai", [])
    alerts = data.get("alerts", [])
    
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Format medicines list
    med_rows = ""
    if isinstance(medicines, pd.DataFrame):
        med_list = medicines.to_dict(orient="records")
    elif isinstance(medicines, list):
        med_list = medicines
    else:
        med_list = []

    if med_list:
        for m in med_list:
            if not isinstance(m, dict):
                continue
            name = m.get("Medicine") or m.get("medicine_name") or m.get("name") or "N/A"
            dosage = m.get("Dosage") or m.get("dosage") or "N/A"
            time_slot = m.get("Time") or m.get("time") or "N/A"
            status = m.get("Status") or m.get("status") or "N/A"
            status_color = "#16a34a" if "taken" in str(status).lower() else ("#dc2626" if "missed" in str(status).lower() else "#d97706")
            med_rows += f"""
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #e2e8f0;">{name}</td>
                <td style="padding: 8px; border-bottom: 1px solid #e2e8f0;">{dosage}</td>
                <td style="padding: 8px; border-bottom: 1px solid #e2e8f0;">{time_slot}</td>
                <td style="padding: 8px; border-bottom: 1px solid #e2e8f0; font-weight: bold; color: {status_color};">{status}</td>
            </tr>
            """
    else:
        med_rows = "<tr><td colspan='4' style='padding: 8px; color: #64748b;'>No medicine records found.</td></tr>"

    # Format AI recommendations
    ai_items = ""
    if ai_recs:
        for rec in ai_recs:
            ai_items += f"<li style='margin-bottom: 6px;'>{rec}</li>"
    else:
        ai_items = "<li>Patient parameters are within normal ranges. Continue prescribed routine.</li>"

    # Format health history trends
    history_rows = ""
    if isinstance(trends, pd.DataFrame):
        trend_list = trends.to_dict(orient="records")
    elif isinstance(trends, list):
        trend_list = trends
    else:
        trend_list = []

    if trend_list:
        for t in trend_list[-10:]: # last 10 records
            if not isinstance(t, dict):
                continue
            time_val = str(t.get("time") or t.get("timestamp") or "N/A")
            hr = t.get("heart_rate") or t.get("heartRate") or "N/A"
            spo2 = t.get("spo2") or t.get("spO2") or "N/A"
            temp = t.get("temperature") or t.get("temp") or "N/A"
            bp = t.get("blood_pressure") or t.get("bp") or "N/A"
            history_rows += f"""
            <tr>
                <td style="padding: 6px 8px; border-bottom: 1px solid #f1f5f9;">{time_val}</td>
                <td style="padding: 6px 8px; border-bottom: 1px solid #f1f5f9;">{hr} bpm</td>
                <td style="padding: 6px 8px; border-bottom: 1px solid #f1f5f9;">{spo2}%</td>
                <td style="padding: 6px 8px; border-bottom: 1px solid #f1f5f9;">{temp}°C</td>
                <td style="padding: 6px 8px; border-bottom: 1px solid #f1f5f9;">{bp}</td>
            </tr>
            """
    else:
        history_rows = "<tr><td colspan='5' style='padding: 8px; color: #64748b;'>No health history records.</td></tr>"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>{report_title}</title>
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; color: #1e293b; background: #fff; }}
            .header {{ border-bottom: 2px solid #2563eb; padding-bottom: 12px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }}
            .header h1 {{ margin: 0; color: #1e3a8a; font-size: 24px; }}
            .header .meta {{ font-size: 13px; color: #64748b; text-align: right; }}
            .section {{ margin-bottom: 24px; background: #f8fafc; padding: 16px; border-radius: 8px; border: 1px solid #e2e8f0; }}
            .section-title {{ font-size: 16px; font-weight: bold; color: #1d4ed8; margin-bottom: 12px; border-bottom: 1px solid #cbd5e1; padding-bottom: 4px; }}
            .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; }}
            .card {{ background: #fff; padding: 10px 14px; border-radius: 6px; border: 1px solid #e2e8f0; }}
            .card .label {{ font-size: 12px; color: #64748b; text-transform: uppercase; font-weight: 600; }}
            .card .value {{ font-size: 16px; font-weight: bold; color: #0f172a; margin-top: 4px; }}
            table {{ width: 100%; border-collapse: collapse; background: #fff; font-size: 14px; margin-top: 8px; }}
            th {{ background: #eff6ff; color: #1e40af; text-align: left; padding: 8px; border-bottom: 2px solid #bfdbfe; font-size: 13px; }}
            ul {{ margin: 4px 0; padding-left: 20px; color: #334155; }}
            .footer {{ margin-top: 30px; font-size: 12px; color: #94a3b8; text-align: center; border-top: 1px solid #e2e8f0; padding-top: 10px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <div>
                <h1>Smart Medicine Box - {report_title}</h1>
                <div style="font-size: 14px; color: #475569; margin-top: 4px;">Patient Health & Activity Summary</div>
            </div>
            <div class="meta">
                <div><strong>Generated:</strong> {now_str}</div>
                <div><strong>Source:</strong> Firebase Live Data</div>
            </div>
        </div>

        <!-- Patient Profile -->
        <div class="section">
            <div class="section-title">Patient Profile Details</div>
            <div class="grid">
                <div class="card"><div class="label">Patient Name</div><div class="value">{patient.get('name') or patient.get('full_name') or 'N/A'}</div></div>
                <div class="card"><div class="label">Patient ID</div><div class="value">{patient.get('patient_id') or patient.get('id') or 'N/A'}</div></div>
                <div class="card"><div class="label">Age / Gender</div><div class="value">{patient.get('age') or 'N/A'} yrs / {patient.get('gender') or 'N/A'}</div></div>
                <div class="card"><div class="label">Blood Group</div><div class="value">{patient.get('blood_group') or 'N/A'}</div></div>
                <div class="card"><div class="label">Primary Condition</div><div class="value">{patient.get('disease') or patient.get('existing_diseases') or 'None specified'}</div></div>
                <div class="card"><div class="label">Attending Doctor</div><div class="value">{patient.get('doctor_name') or 'N/A'}</div></div>
            </div>
        </div>

        <!-- Latest Vitals -->
        <div class="section">
            <div class="section-title">Current Vital Signs</div>
            <div class="grid">
                <div class="card"><div class="label">Heart Rate</div><div class="value" style="color: #2563eb;">{metrics.get('heart_rate', 'N/A')} bpm</div></div>
                <div class="card"><div class="label">SpO₂ Level</div><div class="value" style="color: #059669;">{metrics.get('spo2', 'N/A')} %</div></div>
                <div class="card"><div class="label">Body Temperature</div><div class="value" style="color: #d97706;">{metrics.get('temperature', 'N/A')} °C</div></div>
                <div class="card"><div class="label">Blood Pressure</div><div class="value">{metrics.get('blood_pressure', 'N/A')}</div></div>
                <div class="card"><div class="label">Overall Health Score</div><div class="value" style="color: #7c3aed;">{metrics.get('health_score', 'N/A')} / 100</div></div>
            </div>
        </div>

        <!-- Medicines Schedule -->
        <div class="section">
            <div class="section-title">Medication Schedule & Adherence</div>
            <table>
                <thead>
                    <tr>
                        <th>Medicine</th>
                        <th>Dosage</th>
                        <th>Scheduled Time</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {med_rows}
                </tbody>
            </table>
        </div>

        <!-- Health History Readings -->
        <div class="section">
            <div class="section-title">Recent Health History Readings</div>
            <table>
                <thead>
                    <tr>
                        <th>Timestamp</th>
                        <th>Heart Rate</th>
                        <th>SpO₂</th>
                        <th>Temperature</th>
                        <th>Blood Pressure</th>
                    </tr>
                </thead>
                <tbody>
                    {history_rows}
                </tbody>
            </table>
        </div>

        <!-- AI Recommendations -->
        <div class="section" style="background: #f0fdf4; border-color: #bbf7d0;">
            <div class="section-title" style="color: #15803d;">AI Clinical Recommendations & Insights</div>
            <ul>
                {ai_items}
            </ul>
        </div>

        <div class="footer">
            Generated automatically by Smart Medicine Box System with AI Monitoring. Confidential Medical Document.
        </div>
    </body>
    </html>
    """
    return html_content


def generate_pdf_report(report_data: Any, *args, report_title: str = "Patient Health Report", **kwargs) -> bytes:
    """Generate a PDF binary report using ReportLab, falling back gracefully if needed."""
    data = _normalize_report_data(report_data, *args, **kwargs)
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Heading1'],
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#1e3a8a"),
            spaceAfter=4
        )
        subtitle_style = ParagraphStyle(
            'DocSubtitle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor("#64748b"),
            spaceAfter=12
        )
        section_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading2'],
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#1d4ed8"),
            spaceBefore=10,
            spaceAfter=6
        )
        body_style = ParagraphStyle(
            'Body',
            parent=styles['Normal'],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#1e293b")
        )
        bold_label_style = ParagraphStyle(
            'BoldLabel',
            parent=body_style,
            fontName='Helvetica-Bold'
        )

        elements = []
        elements.append(Paragraph(f"Smart Medicine Box - {report_title}", title_style))
        elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Source: Firebase Live Data", subtitle_style))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#2563eb"), spaceAfter=10))

        # Patient Profile Section
        elements.append(Paragraph("1. Patient Profile Information", section_style))
        patient = data.get("patient", {}) or {}
        p_table_data = [
            [Paragraph("Full Name:", bold_label_style), Paragraph(str(patient.get("name") or patient.get("full_name") or "N/A"), body_style), Paragraph("Patient ID:", bold_label_style), Paragraph(str(patient.get("patient_id") or patient.get("id") or "N/A"), body_style)],
            [Paragraph("Age / Gender:", bold_label_style), Paragraph(f"{patient.get('age', 'N/A')} yrs / {patient.get('gender', 'N/A')}", body_style), Paragraph("Blood Group:", bold_label_style), Paragraph(str(patient.get("blood_group") or "N/A"), body_style)],
            [Paragraph("Doctor:", bold_label_style), Paragraph(str(patient.get("doctor_name") or "N/A"), body_style), Paragraph("Hospital:", bold_label_style), Paragraph(str(patient.get("hospital_name") or "N/A"), body_style)],
            [Paragraph("Condition:", bold_label_style), Paragraph(str(patient.get("disease") or patient.get("existing_diseases") or "None specified"), body_style), Paragraph("Device Serial:", bold_label_style), Paragraph(str(patient.get("device_serial_number") or "N/A"), body_style)],
        ]
        t_prof = Table(p_table_data, colWidths=[100, 170, 90, 180])
        t_prof.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
            ('PADDING', (0,0), (-1,-1), 4),
        ]))
        elements.append(t_prof)
        elements.append(Spacer(1, 10))

        # Vitals Section
        elements.append(Paragraph("2. Current Vital Signs & Health Score", section_style))
        metrics = data.get("metrics", {}) or {}
        v_table_data = [
            [Paragraph("Heart Rate", bold_label_style), Paragraph("SpO2", bold_label_style), Paragraph("Body Temperature", bold_label_style), Paragraph("Blood Pressure", bold_label_style), Paragraph("Health Score", bold_label_style)],
            [
                Paragraph(f"{metrics.get('heart_rate', 'N/A')} bpm", body_style),
                Paragraph(f"{metrics.get('spo2', 'N/A')} %", body_style),
                Paragraph(f"{metrics.get('temperature', 'N/A')} °C", body_style),
                Paragraph(str(metrics.get('blood_pressure') or 'N/A'), body_style),
                Paragraph(f"{metrics.get('health_score', 'N/A')} / 100", body_style)
            ]
        ]
        t_vitals = Table(v_table_data, colWidths=[108, 108, 108, 108, 108])
        t_vitals.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#eff6ff")),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#bfdbfe")),
            ('PADDING', (0,0), (-1,-1), 6),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ]))
        elements.append(t_vitals)
        elements.append(Spacer(1, 10))

        # Medication Schedule Section
        elements.append(Paragraph("3. Medication Schedule & Adherence", section_style))
        medicines = data.get("medicines", [])
        if isinstance(medicines, pd.DataFrame):
            med_list = medicines.to_dict(orient="records")
        elif isinstance(medicines, list):
            med_list = medicines
        else:
            med_list = []

        med_table_data = [
            [Paragraph("Medicine Name", bold_label_style), Paragraph("Dosage", bold_label_style), Paragraph("Scheduled Time", bold_label_style), Paragraph("Status", bold_label_style)]
        ]
        if med_list:
            for m in med_list:
                if not isinstance(m, dict):
                    continue
                name = str(m.get("Medicine") or m.get("medicine_name") or m.get("name") or "N/A")
                dosage = str(m.get("Dosage") or m.get("dosage") or "N/A")
                time_slot = str(m.get("Time") or m.get("time") or "N/A")
                status = str(m.get("Status") or m.get("status") or "N/A")
                med_table_data.append([
                    Paragraph(name, body_style),
                    Paragraph(dosage, body_style),
                    Paragraph(time_slot, body_style),
                    Paragraph(status, body_style)
                ])
        else:
            med_table_data.append([Paragraph("No medicine records.", body_style), Paragraph("-", body_style), Paragraph("-", body_style), Paragraph("-", body_style)])

        t_meds = Table(med_table_data, colWidths=[180, 120, 120, 120])
        t_meds.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f8fafc")),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
            ('PADDING', (0,0), (-1,-1), 4),
        ]))
        elements.append(t_meds)
        elements.append(Spacer(1, 10))

        # Health History Trends
        elements.append(Paragraph("4. Health History & Trends", section_style))
        trends = data.get("trends", [])
        if isinstance(trends, pd.DataFrame):
            trend_list = trends.to_dict(orient="records")
        elif isinstance(trends, list):
            trend_list = trends
        else:
            trend_list = []

        history_table_data = [
            [Paragraph("Timestamp", bold_label_style), Paragraph("Heart Rate", bold_label_style), Paragraph("SpO2", bold_label_style), Paragraph("Temp", bold_label_style), Paragraph("Blood Pressure", bold_label_style)]
        ]
        if trend_list:
            for t in trend_list[-7:]:  # last 7 items
                if not isinstance(t, dict):
                    continue
                time_val = str(t.get("time") or t.get("timestamp") or "N/A")
                hr = f"{t.get('heart_rate') or t.get('heartRate') or 'N/A'} bpm"
                spo2 = f"{t.get('spo2') or t.get('spO2') or 'N/A'} %"
                temp = f"{t.get('temperature') or t.get('temp') or 'N/A'} °C"
                bp = str(t.get("blood_pressure") or t.get("bp") or "N/A")
                history_table_data.append([
                    Paragraph(time_val, body_style),
                    Paragraph(hr, body_style),
                    Paragraph(spo2, body_style),
                    Paragraph(temp, body_style),
                    Paragraph(bp, body_style)
                ])
        else:
            history_table_data.append([Paragraph("No health history recorded.", body_style), Paragraph("-", body_style), Paragraph("-", body_style), Paragraph("-", body_style), Paragraph("-", body_style)])

        t_hist = Table(history_table_data, colWidths=[150, 95, 95, 95, 105])
        t_hist.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f8fafc")),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
            ('PADDING', (0,0), (-1,-1), 4),
        ]))
        elements.append(t_hist)
        elements.append(Spacer(1, 10))

        # AI Recommendations Section
        elements.append(Paragraph("5. AI Recommendations & Health Advisory", section_style))
        ai_recs = data.get("ai", [])
        if ai_recs:
            for rec in ai_recs:
                elements.append(Paragraph(f"• {rec}", body_style))
                elements.append(Spacer(1, 3))
        else:
            elements.append(Paragraph("• Vitals and adherence levels are within normal limits. Maintain regular checkups.", body_style))

        elements.append(Spacer(1, 15))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=6))
        elements.append(Paragraph("Smart Medicine Box System - Automated Firebase Data Export - Confidential", ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.HexColor("#94a3b8"), alignment=1)))

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()
    except Exception:
        html_str = generate_html_report(data, report_title)
        return html_str.encode('utf-8')
