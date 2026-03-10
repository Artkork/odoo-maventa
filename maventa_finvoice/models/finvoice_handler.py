import base64
import logging
import requests
from datetime import datetime
from lxml import etree
from io import BytesIO

from odoo import fields

_logger = logging.getLogger(__name__)


class FinvoiceHandler:
    """Handler for Finvoice generation and Maventa API integration"""
    
    FINVOICE_VERSION = "3.2.2"
    XMLNS = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
    
    def __init__(self, maventa_config):
        self.config = maventa_config
        self.api_session = requests.Session()
        self.api_session.auth = (
            maventa_config.client_secret,
            maventa_config.vendor_api_key,
        )
    
    def _get_endpoint(self, path):
        """Build API endpoint URL"""
        base_url = self.config.api_base_url
        if self.config.test_mode:
            base_url = base_url.replace(
                "masend.maventa.com", "test.maventa.com"
            )
        return f"{base_url}{path}"
    
    def generate_finvoice_xml(self, invoice):
        """Generate Finvoice XML from account.move"""
        
        # Create root Invoice element
        invoice_root = etree.Element(
            "Invoice",
            xmlns=self.XMLNS,
        )
        
        # Document metadata
        id_elem = etree.SubElement(invoice_root, "ID")
        id_elem.text = invoice.name
        
        issue_date = etree.SubElement(invoice_root, "IssueDate")
        issue_date.text = invoice.invoice_date.isoformat()
        
        due_date = etree.SubElement(invoice_root, "DueDate")
        due_date.text = invoice.invoice_date_due.isoformat()
        
        type_elem = etree.SubElement(invoice_root, "InvoiceTypeCode")
        type_elem.text = "380"  # Commercial invoice
        
        # Supplier (Seller)
        supplier = etree.SubElement(invoice_root, "AccountingSupplierParty")
        supplier_party = etree.SubElement(supplier, "Party")
        self._add_party_info(
            supplier_party,
            self.config.sender_id,
            self.config.sender_name or self.config.company_id.name,
        )
        
        # Customer (Buyer)
        customer = etree.SubElement(invoice_root, "AccountingCustomerParty")
        customer_party = etree.SubElement(customer, "Party")
        customer_id = invoice.partner_id.ref or invoice.partner_id.name
        self._add_party_info(
            customer_party,
            customer_id,
            invoice.partner_id.name,
        )
        
        # Line items
        lines_element = etree.SubElement(invoice_root, "InvoiceLines")
        for line in invoice.invoice_line_ids:
            self._add_invoice_line(lines_element, line)
        
        # Totals
        totals = etree.SubElement(invoice_root, "LegalMonetaryTotal")
        self._add_monetary_total(totals, invoice)
        
        return etree.tostring(
            invoice_root,
            pretty_print=True,
            encoding="utf-8",
            xml_declaration=True,
        )
    
    def _add_party_info(self, party_element, party_id, party_name):
        """Add party (supplier/customer) information"""
        
        # Party ID
        identification = etree.SubElement(party_element, "PartyIdentification")
        party_id_elem = etree.SubElement(identification, "ID")
        party_id_elem.text = party_id.upper()
        
        # Party Name
        name_elem = etree.SubElement(party_element, "PartyName")
        name_text = etree.SubElement(name_elem, "Name")
        name_text.text = party_name[:200]  # Max 200 chars
        
        # Legal Entity
        legal_entity = etree.SubElement(party_element, "PartyLegalEntity")
        registration_elem = etree.SubElement(legal_entity, "RegistrationName")
        registration_elem.text = party_name[:200]
    
    def _add_invoice_line(self, lines_element, line):
        """Add invoice line item"""
        
        line_elem = etree.SubElement(lines_element, "InvoiceLine")
        
        # Line ID
        line_id = etree.SubElement(line_elem, "ID")
        line_id.text = str(line.id)
        
        # Quantity
        quantity = etree.SubElement(line_elem, "InvoicedQuantity")
        quantity.text = str(line.quantity)
        
        # Description
        description = etree.SubElement(line_elem, "Description")
        description.text = line.name[:1000]
        
        # Unit price
        price_elem = etree.SubElement(line_elem, "UnitPriceAmount")
        price_elem.text = f"{line.price_unit:.2f}"
        
        # Line amount
        amount = etree.SubElement(line_elem, "LineExtensionAmount")
        amount.text = f"{line.price_subtotal:.2f}"
    
    def _add_monetary_total(self, totals_element, invoice):
        """Add monetary totals"""
        
        # Subtotal
        subtotal = etree.SubElement(totals_element, "TaxExclusiveAmount")
        subtotal.text = f"{invoice.amount_untaxed:.2f}"
        
        # Tax
        tax_elem = etree.SubElement(totals_element, "TaxInclusiveAmount")
        tax_elem.text = f"{invoice.amount_total:.2f}"
        
        # Prepaid
        prepaid = etree.SubElement(totals_element, "PrepaidAmount")
        prepaid.text = "0.00"
        
        # Amount due
        payable = etree.SubElement(totals_element, "PayableAmount")
        payable.text = f"{invoice.amount_total:.2f}"
    
    def send_invoice_to_maventa(self, invoice_xml, recipient_id, invoice_record):
        """Send Finvoice to recipient via Maventa"""
        
        try:
            # Encode XML to base64
            xml_content = base64.b64encode(invoice_xml).decode("utf-8")
            
            # Prepare request payload
            payload = {
                "recipient": recipient_id,
                "filename": f"invoice_{invoice_record.name}.xml",
                "content": xml_content,
                "format": "finvoice",
            }
            
            # Send to Maventa
            endpoint = self._get_endpoint("/send")
            response = self.api_session.post(
                endpoint,
                json=payload,
                timeout=30,
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                return {
                    "success": True,
                    "maventa_id": result.get("id"),
                    "status": result.get("status"),
                    "response": result,
                }
            else:
                error_msg = response.text or f"HTTP {response.status_code}"
                _logger.error(
                    f"Maventa API error for invoice {invoice_record.name}: {error_msg}"
                )
                return {
                    "success": False,
                    "error": error_msg,
                    "status_code": response.status_code,
                }
                
        except Exception as e:
            error_msg = f"Failed to send invoice: {str(e)}"
            _logger.exception(error_msg)
            return {
                "success": False,
                "error": error_msg,
            }
    
    def get_delivery_status(self, maventa_id):
        """Check invoice delivery status from Maventa"""
        
        try:
            endpoint = self._get_endpoint(f"/delivery/{maventa_id}")
            response = self.api_session.get(endpoint, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                _logger.warning(
                    f"Could not fetch status for {maventa_id}: HTTP {response.status_code}"
                )
                return None
                
        except Exception as e:
            _logger.exception(f"Error fetching delivery status: {str(e)}")
            return None
    
    def validate_finvoice_xml(self, xml_content):
        """Validate Finvoice XML structure"""
        
        try:
            xml_root = etree.fromstring(xml_content)
            
            # Check required elements
            required_fields = ["ID", "IssueDate", "DueDate", "AccountingSupplierParty"]
            for field in required_fields:
                if xml_root.find(field) is None:
                    return False, f"Missing required field: {field}"
            
            return True, "Valid"
            
        except etree.XMLSyntaxError as e:
            return False, f"XML Syntax Error: {str(e)}"
        except Exception as e:
            return False, f"Validation error: {str(e)}"
