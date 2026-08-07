from pathlib import Path

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer


output = Path("zyrabit-context/video-demo/contrato-servicios-demo.pdf")
output.parent.mkdir(parents=True, exist_ok=True)

styles = getSampleStyleSheet()
body = styles["BodyText"]
heading = styles["Heading1"]

story = []
for page in range(1, 151):
    story.append(Paragraph(f"Contrato de Servicios - Página {page}", heading))
    if page == 124:
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph("Cláusula 12.4 - Rescisión anticipada", heading))
        story.append(Paragraph(
            "Si el Cliente rescinde el contrato antes del término pactado sin causa "
            "atribuible al Proveedor, pagará una penalización equivalente a tres meses "
            "del cargo mensual promedio de los últimos seis meses, dentro de los 30 días "
            "naturales posteriores a la notificación de rescisión.",
            body,
        ))
    else:
        story.append(Paragraph(
            "Documento sintético para demostración local. Esta página contiene condiciones "
            "operativas y comerciales de referencia para el flujo de indexación.",
            body,
        ))
    if page < 150:
        story.append(PageBreak())

SimpleDocTemplate(
    str(output), pagesize=LETTER, leftMargin=0.85 * inch, rightMargin=0.85 * inch,
    topMargin=0.8 * inch, bottomMargin=0.8 * inch,
).build(story)
print(output)
