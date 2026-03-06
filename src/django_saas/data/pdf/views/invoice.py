# views.py
import base64
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML

from django_saas.core.utils import make_qr_b64, make_barcode_b64, png_bytes_to_b64, PDF


def invoice_pdf(request, invoice_id: int):
    # Normalmente você busca no DB
    # invoice = Invoice.objects.get(id=invoice_id)
    # Exemplo de dados (substituir por dados reais)
    company = {
        "name": "Minha Empresa Lda",
        "address": "Rua X, Luanda, Angola",
        "nif": "5000000000",
        "phone": "+244 900 000 000",
        "email": "finance@empresa.co.ao",
    }

    customer = {
        "name": "Cliente Exemplo",
        "nif": "4000000000",
        "address": "Rua Y, Benguela, Angola",
        "email": "cliente@email.com",
        "phone": "+244 999 999 999",
    }

    doc = {
        "type": "FATURA",
        "number": "FT 2026/000123",
        "date": "2026-02-05",
        "due_date": "2026-02-10",
        "currency": "AOA",
        "payment_method": "Transferência",
        "reference": "REF-001",
        "notes": "Obrigado pela preferência.",
    }

    lines = [
        {"name":"Produto A", "sku":"A-001", "note":"", "qty":2, "unit_price":"10.000,00", "vat_rate":14, "total":"22.800,00"},
        {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
        {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
        {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
        {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
        {"name":"Produto A", "sku":"A-001", "note":"", "qty":2, "unit_price":"10.000,00", "vat_rate":14, "total":"22.800,00"},
        {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
        {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
        {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
        {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
        {"name":"Produto A", "sku":"A-001", "note":"", "qty":2, "unit_price":"10.000,00", "vat_rate":14, "total":"22.800,00"},
        {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
        {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
        {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
        {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
        {"name":"Produto A", "sku":"A-001", "note":"", "qty":2, "unit_price":"10.000,00", "vat_rate":14, "total":"22.800,00"},
        {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
        {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
        {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
        {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
        {"name":"Produto A", "sku":"A-001", "note":"", "qty":2, "unit_price":"10.000,00", "vat_rate":14, "total":"22.800,00"},
        {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
        {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
        {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
        {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
        {"name":"Produto A", "sku":"A-001", "note":"", "qty":2, "unit_price":"10.000,00", "vat_rate":14, "total":"22.800,00"},
        {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
        {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
        {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
        {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
        {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
        {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
        {"name":"Serviço B", "sku":"S-100", "note":"Mensal", "qty":1, "unit_price":"50.000,00", "vat_rate":14, "total":"57.000,00"},
    ]

    totals = {
        "subtotal": "60.000,00",
        "vat_total": "8.400,00",
        "discount_total": "0,00",
        "grand_total": "68.400,00",
    }

    # Logo (opcional): leia um PNG e converta para base64
    # Exemplo simples: se tiveres um ficheiro logo.png no disco:
    logo_b64 = None
    # with open("/caminho/logo.png", "rb") as f:
    #     logo_b64 = png_bytes_to_b64(f.read())

    # QR + barcode (base64)
    qr_b64 = make_qr_b64(f"{doc['type']}|{doc['number']}|TOTAL:{totals['grand_total']}")
    barcode_b64 = make_barcode_b64(doc["number"])

    return PDF("pdf/invoice.html", request,  company= company, customer= customer, doc= doc, lines= lines, totals= totals, logo_b64= logo_b64, qr_b64= qr_b64, barcode_b64= barcode_b64,)
