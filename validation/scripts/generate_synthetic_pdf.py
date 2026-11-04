#!/usr/bin/env python3
"""
QA Validation Script - Synthetic PDF Generator with PII.

Generates a PDF containing:
- Technical plant data (valve pressures, etc.)
- Synthetic PII: credit cards, emails, RFC, CURP, SSN

Usage:
    python validation/scripts/generate_synthetic_pdf.py [output_path]
"""
import sys
import os

# Minimal dependency: reportlab (already in env or install with `uv pip install reportlab`)
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
except ImportError:
    print("❌ reportlab not found. Install with: uv pip install reportlab")
    sys.exit(1)


SYNTHETIC_CONTENT = """
=== INFORME TÉCNICO ZYRABIT - DATOS DE PLANTA ===

Autor: Ing. Juan García
Empresa: Zyrabit Industrial Solutions
Fecha: 2026-06-10

--- PARÁMETROS OPERATIVOS ---
Válvula A = 285 PSI  (normal)
Válvula B = 340 PSI  (atención: sobre límite nominal 320 PSI)
Válvula C = 310 PSI  (normal)
Temperatura Caldera 1 = 87.4°C
Temperatura Caldera 2 = 91.2°C  (revisar regulador)
Presión de Vapor Principal = 6.8 bar

--- PERSONAL AUTORIZADO ---
Nombre: Carlos Rodríguez Martínez
Email: c.rodriguez@zyrabit-plant.com
Teléfono: +52 55 1234-5678
RFC: ROMC800514XY3
CURP: ROMC800514HDFXXX01

Nombre: Ana López Fuentes
Email: ana.lopez@zyrabit-plant.com
SSN: 123-45-6789
Número de Tarjeta: 4532-1234-5678-9012
CVV: 456
Vencimiento: 12/28

Nombre: Supervisor externo
Tarjeta Empresa: 5425-2334-3010-9903
Email contacto: supervisor.ext@proveedor.mx

--- NOTAS DE MANTENIMIENTO ---
El sistema de monitoreo continuo requiere revisión antes del 2026-07-01.
El contrato de mantenimiento con proveedor externo expira el 2026-12-31.
El acceso al panel está restringido al personal con credenciales nivel 3.

--- FIN DEL INFORME ---
"""


def generate_pdf(output_path: str) -> None:
    """Generates PDF with technical data and synthetic PII."""
    p = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4
    
    # Title
    p.setFont("Helvetica-Bold", 16)
    p.drawString(72, height - 72, "Technical Report - Zyrabit SLM PII Validation")
    
    # Content line by line
    p.setFont("Courier", 9)
    y_pos = height - 110
    for line in SYNTHETIC_CONTENT.strip().split("\n"):
        if y_pos < 72:
            p.showPage()
            p.setFont("Courier", 9)
            y_pos = height - 72
        p.drawString(72, y_pos, line[:100])  # truncate long lines
        y_pos -= 14

    p.save()
    print(f"✅ PDF generated at: {output_path}")
    print(f"   Size: {os.path.getsize(output_path):,} bytes")
    print("\n🔍 PDF contains:")
    print("   - 2 emails")
    print("   - 2 credit card numbers")
    print("   - 1 SSN (Social Security Number)")
    print("   - 1 RFC, 1 CURP")
    print("   - Technical data: valve pressures, temperatures")


if __name__ == "__main__":
    output = sys.argv[1] if len(sys.argv) > 1 else "/tmp/synthetic_pii_test.pdf"
    generate_pdf(output)
