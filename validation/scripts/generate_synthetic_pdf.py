#!/usr/bin/env python3
"""
Script de Validación QA - Generador de PDF Sintético con PII.

Genera un PDF que contiene:
- Datos técnicos reales (presiones de válvulas, etc.)
- PII sintético: tarjetas de crédito, correos, números de seguridad social

Uso:
    python validation/scripts/generate_synthetic_pdf.py [output_path]
"""
import sys
import os
from pathlib import Path

# Dependencia mínima: reportlab (ya en el entorno o instalar con `uv pip install reportlab`)
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
except ImportError:
    print("❌ reportlab no encontrado. Instalar con: uv pip install reportlab")
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
    """Genera el PDF con datos técnicos y PII sintético."""
    p = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4
    
    # Título
    p.setFont("Helvetica-Bold", 16)
    p.drawString(72, height - 72, "Informe Técnico - Validación PII Zyrabit SLM")
    
    # Contenido línea por línea
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
    print(f"✅ PDF generado en: {output_path}")
    print(f"   Tamaño: {os.path.getsize(output_path):,} bytes")
    print("\n🔍 El PDF contiene:")
    print("   - 2 correos electrónicos")
    print("   - 2 números de tarjeta de crédito")
    print("   - 1 SSN (Social Security Number)")
    print("   - 1 RFC, 1 CURP")
    print("   - Datos técnicos: presiones de válvulas, temperaturas")


if __name__ == "__main__":
    output = sys.argv[1] if len(sys.argv) > 1 else "/tmp/synthetic_pii_test.pdf"
    generate_pdf(output)
