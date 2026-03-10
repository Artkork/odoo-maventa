import logging
from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class MaventaConfig(models.Model):
    """Configuration model for Maventa API integration"""
    
    _name = "maventa.config"
    _description = "Maventa Configuration"
    _rec_name = "company_id"

    _company_id_unique = models.Constraint(
        "UNIQUE(company_id)",
        "A Maventa configuration already exists for this company.",
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        ondelete="cascade",
    )
    
    # API Configuration
    api_base_url = fields.Char(
        string="Maventa API Base URL",
        required=True,
        default="https://ax-stage.maventa.com/api/v1/invoices",
        help="Base URL for Maventa API",
    )
    
    api_username = fields.Char(
        string="API Username",
        required=True,
        help="Maventa API username",
    )
    
    api_password = fields.Char(
        string="API Password",
        required=True,
        help="Maventa API password",
    )
    
    api_customer_id = fields.Char(
        string="Customer ID",
        required=True,
        help="Your organization ID at Maventa",
    )
    
    # Invoice Configuration
    sender_id = fields.Char(
        string="Sender ID (DUNS/Y-tunnus)",
        required=True,
        help="Your organization identifier (DUNS or Y-tunnus)",
    )
    
    sender_name = fields.Char(
        string="Sender Name",
        required=False,
        help="Your organization name (auto-filled from company if empty)",
    )
    
    # Features
    auto_send_invoices = fields.Boolean(
        string="Automatically Send Invoices",
        default=False,
        help="Send invoices automatically when validated",
    )
    
    test_mode = fields.Boolean(
        string="Test Mode",
        default=True,
        help="Use Maventa test/sandbox environment",
    )
    
    # Status
    last_connection_test = fields.Datetime(
        string="Last Connection Test",
        readonly=True,
    )
    
    connection_status = fields.Selection(
        [("connected", "Connected"), ("error", "Error"), ("unknown", "Unknown")],
        string="Connection Status",
        default="unknown",
        readonly=True,
    )
    
    connection_error = fields.Text(
        string="Connection Error",
        readonly=True,
    )
    
    active = fields.Boolean(default=True)
    
    @api.constrains("api_username", "api_password")
    def _check_credentials(self):
        for record in self:
            if not record.api_username or not record.api_password:
                raise ValidationError(
                    "API username and password are required for Maventa configuration."
                )
    
    def test_connection(self):
        """Test the connection to Maventa API"""
        self.ensure_one()
        
        try:
            import requests
            
            url = f"{self.api_base_url}/api/v1/invoices"
            response = requests.post(
                url,
                auth=(self.api_username, self.api_password),
                timeout=10,
            )
            
            if response.status_code == 200:
                self.connection_status = "connected"
                self.connection_error = ""
                self.last_connection_test = fields.Datetime.now()
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "Connection Test Successful",
                        "message": "Successfully connected to Maventa API",
                        "type": "success",
                    },
                }
            else:
                error_msg = f"API returned status {response.status_code}"
                self.connection_status = "error"
                self.connection_error = error_msg
                self.last_connection_test = fields.Datetime.now()
                raise ValidationError(error_msg)
                
        except Exception as e:
            error_msg = str(e)
            self.connection_status = "error"
            self.connection_error = error_msg
            self.last_connection_test = fields.Datetime.now()
            _logger.error(f"Maventa connection test failed: {error_msg}")
            raise ValidationError(f"Connection test failed: {error_msg}")
