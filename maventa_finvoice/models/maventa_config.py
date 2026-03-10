import logging
from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class MaventaConfig(models.Model):
    """Configuration model for Maventa API integration"""
    token = "eyJ0eXAiOiJKV1QiLCJraWQiOiIyZGZjYTlmMTE4ZWRlNThmYmZiMjM0ZTIxZDQ0MTY1ODVjNzc3NjZjMDY4OTk4MDdkYTgwNTlhMTRmODRlNjgyIiwiYWxnIjoiUlM1MTIifQ.eyJpZGVudGl0eSI6InVzZXIiLCJ1c2VyX2lkIjoiYjMxMDVlZmItMWRhMy00MTNiLWI2YTMtN2JjYTgwMDg2ZjY4IiwiY29tcGFueV9pZCI6IjY3OWQ2N2Q2LTQ1NWQtNGZjYy1iNWJhLTYzZjI1YzNjNDVkNSIsInNjb3BlIjpbImV1aTpvcGVuIiwiY29tcGFueTpyZWFkIiwiY29tcGFueTp3cml0ZSIsImxvb2t1cCIsInJlY2VpdmFibGVzOmFzc2lnbm1lbnRzIiwiZG9jdW1lbnQ6c2VuZCIsImRvY3VtZW50OnJlY2VpdmUiLCJpbnZvaWNlOnJlY2VpdmUiLCJpbnZvaWNlOnNlbmQiLCJhbmFseXNpcyJdLCJ2ZW5kb3JfaWQiOiJiMGJlYjRlZS02NmUxLTQzYWItODdhMy1iYzliY2Y2MzRmNGYiLCJleHAiOjE3NzMxNTUwMzJ9.NTJFggmVBjw6ORd1uLBPA6Dd9PE-ZCIb3lRh5HfBqhrpeCnKhWIeLSPFN413zuQrJ96MkbaMx2ltt3FCC0iGUySmVwNgiSdww8gIK5l1RUftdPDc1-Wltrs6iXTYutPJylZLNWKJkWw-o6N6UxGQLPAyLvkmpplmPL_02qJFONIJsp8AU1LfJ4X8u7sfo3k05L3ys7SHy46wm90mR-3KX6buA9v6U-1bAHsScylfmwNS0KddFqPH0iopyoSqsK1v-utjvFyWbumMzTT4p5pUyoptpyixey3sG-pBStO34jZ1UgXVO0jBtLjW5kuh-RE7BQNdESbbC3xYyDKg3DbXwQ"
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
                auth=(token),
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
