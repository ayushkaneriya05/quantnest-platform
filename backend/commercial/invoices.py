"""Owned, printable immutable invoices. Escape every stored customer value."""
from html import escape
from django.http import HttpResponse


def render_invoice_html(invoice):
    data = invoice.snapshot
    def value(name, fallback=""):
        return escape(str(data.get(name, fallback)))
    def money(name):
        return f'{data.get(name, 0)/100:,.2f} {escape(str(data.get("currency", "INR")))}'
    buyer = data.get("buyer", {})
    html = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(invoice.number)}</title><style>body{{font:16px system-ui;color:#172033;background:#fff;margin:3rem auto;padding:1rem;max-width:760px}}header{{display:flex;justify-content:space-between;gap:1rem}}dl{{display:grid;grid-template-columns:1fr 1fr;gap:1rem}}dd{{text-align:right;margin:0}}hr{{border:0;border-top:1px solid #cbd5e1}}small{{color:#475569}}@media print{{body{{margin:0}}}}</style></head><body><header><h1>{value("seller", "QuantNest")}</h1><div><h2>Invoice</h2><p>{escape(invoice.number)}</p><p>{invoice.issued_at.strftime("%d %b %Y %H:%M UTC")}</p></div></header><hr><h3>Buyer</h3><p>{escape(str(buyer.get("name", "")))}<br>{value("buyer_email")}<br>{escape(str(buyer.get("address", "")))}</p><p>Buyer tax identifier: {escape(str(buyer.get("tax_id") or "Not supplied"))}</p><p>Seller tax identifier: {value("seller_tax_id", "Not applicable") or "Not applicable"}</p><h3>{value("plan", value("kind", "Software service"))}</h3><p>Period: {value("period_start", "As agreed")} — {value("period_end", "As agreed")}</p><dl><dt>Base amount</dt><dd>{money("base_minor")}</dd><dt>Applicable tax</dt><dd>{money("tax_minor")}</dd><dt><strong>Captured total</strong></dt><dd><strong>{money("total_minor")}</strong></dd></dl><hr><small>Payment record: {escape(invoice.payment.provider_id)}. This invoice records the captured payment. Workspace, Custom Development and Private terms remain separate. Use your browser's Print action to save a PDF.</small></body></html>'''
    response = HttpResponse(html, content_type="text/html; charset=utf-8")
    response["Cache-Control"] = "private, no-store"
    response["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'"
    response["X-Content-Type-Options"] = "nosniff"
    return response
