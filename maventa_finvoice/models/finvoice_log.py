import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class FinvoiceLog(models.Model):
    """Log records for Finvoice sending"""
    
    _name = "finvoice.log"
    _description = "Finvoice Sending Log"
    _rec_name = "invoice_id"
    _order = "create_date DESC"
    
    invoice_id = fields.Many2one(
        "account.move",
        string="Invoice",
        required=True,
        ondelete="cascade",
    )
    
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        ondelete="cascade",
    )
    
    recipient_id = fields.Char(
        string="Recipient ID",
        required=True,
    )
    
    recipient_name = fields.Char(
        string="Recipient Name",
    )
    
    # Status
    status = fields.Selection(
        [
            ("draft", "Draft"),
            ("pending", "Pending"),
            ("sent", "Sent"),
            ("delivered", "Delivered"),
            ("failed", "Failed"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="draft",
        required=True,
    )
    
    # Maventa tracking
    maventa_id = fields.Char(
        string="Maventa ID",
        readonly=True,
        help="Internal ID from Maventa API",
    )
    
    # Timestamps
    sent_date = fields.Datetime(
        string="Sent Date",
        readonly=True,
    )
    
    delivery_date = fields.Datetime(
        string="Delivery Date",
        readonly=True,
    )
    
    # Error handling
    error_message = fields.Text(
        string="Error Message",
    )
    
    last_status_check = fields.Datetime(
        string="Last Status Check",
        readonly=True,
    )
    
    # XML Content
    finvoice_xml = fields.Text(
        string="Finvoice XML",
        help="Generated Finvoice XML content",
    )
    
    # API Response
    api_response = fields.Text(
        string="API Response",
        readonly=True,
    )
    
    # Notes
    notes = fields.Text(
        string="Notes",
    )
    
    @api.model
    def create_log(self, invoice, recipient_id, recipient_name, status="pending"):
        """Create a new log entry for invoice sending"""
        
        return self.create({
            "invoice_id": invoice.id,
            "company_id": invoice.company_id.id,
            "recipient_id": recipient_id,
            "recipient_name": recipient_name,
            "status": status,
        })
    
    def update_as_sent(self, maventa_id, api_response_text=None):
        """Update log as sent"""
        
        self.write({
            "status": "sent",
            "maventa_id": maventa_id,
            "sent_date": fields.Datetime.now(),
            "api_response": api_response_text,
            "error_message": "",
        })
    
    def update_as_failed(self, error_message, api_response_text=None):
        """Update log as failed"""
        
        self.write({
            "status": "failed",
            "error_message": error_message,
            "api_response": api_response_text,
            "sent_date": fields.Datetime.now(),
        })
    
    def update_delivery_status(self, status, delivery_date=None):
        """Update delivery status from Maventa"""
        
        values = {"last_status_check": fields.Datetime.now()}
        
        if status == "delivered":
            values["status"] = "delivered"
            values["delivery_date"] = delivery_date or fields.Datetime.now()
        elif status == "failed":
            values["status"] = "failed"
        
        self.write(values)
    
    def check_status_from_maventa(self):
        """Check current status from Maventa API"""
        
        self.ensure_one()
        
        if not self.maventa_id:
            return False
        
        try:
            from .finvoice_handler import FinvoiceHandler
            
            config = self.invoice_id.company_id.maventa_config_ids.filtered(
                lambda c: c.active
            )
            
            if not config:
                _logger.warning(
                    f"No Maventa configuration for company {self.company_id.name}"
                )
                return False
            
            handler = FinvoiceHandler(config[0])
            status_data = handler.get_delivery_status(self.maventa_id)
            
            if status_data:
                status = status_data.get("status", "").lower()
                self.update_delivery_status(status)
                return True
            
            return False
            
        except Exception as e:
            _logger.exception(f"Error checking Maventa status: {str(e)}")
            return False
