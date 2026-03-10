import logging
from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class MaventaConfig(models.Model):
    """Configuration model for Maventa API integration"""

    def get_oauth2_token_and_invoices(self):
        """Get OAuth2 token and fetch invoices from Maventa API"""
        import requests
        BASE_URL = "https://ax-stage.maventa.com"
        TOKEN_URL = f"{BASE_URL}/oauth2/token"
        CLIENT_ID = self.client_id
        CLIENT_SECRET = self.client_secret
        VENDOR_API_KEY = self.vendor_api_key
        data = {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "vendor_api_key": VENDOR_API_KEY,
            "grant_type": "client_credentials",
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        resp = requests.post(TOKEN_URL, data=data, headers=headers, timeout=30)
        resp.raise_for_status()
        token = resp.json()["access_token"]
        # Esimerkki suojatusta kutsusta:
        invoices_url = f"{BASE_URL}/v1/invoices"
        auth_headers = {"Authorization": f"Bearer {token}"}
        invoices = requests.get(invoices_url, headers=auth_headers, timeout=30)
        _logger.info(f"Invoices response: {invoices.status_code} {invoices.text}")
        return invoices.status_code, invoices.text
    
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
        default="https://masend.maventa.com/api/v1",
        help="Base URL for Maventa API",
    )
    
    client_secret = fields.Char(
        string="Client Secret",
        required=True,
        help="Yrityksen käyttäjän API-avain (User API key)",
    )
    
    vendor_api_key = fields.Char(
        string="Vendor API Key",
        required=True,
        help="Sovelluksen API-avain (Software/Vendor API key)",
    )
    
    client_id = fields.Char(
        string="Client ID",
        required=True,
        help="Yrityksen tunniste (Company UUID)",
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
    
    @api.constrains("client_secret", "vendor_api_key")
    def _check_credentials(self):
        for record in self:
            if not record.client_secret or not record.vendor_api_key:
                raise ValidationError(
                    "Client Secret and Vendor API Key are required for Maventa configuration."
                )
    
    def test_connection(self):
        """Test the connection to Maventa API"""
        self.ensure_one()
        
        try:
            import requests
            # Käytetään oikeaa OAuth2-token endpointia
            token_url = f"{self.api_base_url}/oauth2/token"
            data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "vendor_api_key": self.vendor_api_key,
                "grant_type": "client_credentials",
            }
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            _logger.info(f"DEBUG: Lähetettävä token_url: {token_url}")
            _logger.info(f"DEBUG: Lähetettävä data: {data}")
            _logger.info(f"DEBUG: Lähetettävä headers: {headers}")
            response = requests.post(token_url, data=data, headers=headers, timeout=30)
            if response.status_code == 200:
                token = response.json().get("access_token")
                self.connection_status = "connected"
                self.connection_error = ""
                self.last_connection_test = fields.Datetime.now()
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "Connection Test Successful",
                        "message": f"Successfully connected to Maventa API. Token: {token}",
                        "type": "success",
                    },
                }
            else:
                error_msg = f"API returned status {response.status_code}: {response.text}"
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

