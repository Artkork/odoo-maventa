from odoo import api, fields, models
from odoo.exceptions import UserError


class FinvoiceSendWizard(models.TransientModel):
    """Wizard to send Finvoice invoices"""
    
    _name = "finvoice.send.wizard"
    _description = "Send Finvoice Wizard"
    
    invoice_id = fields.Many2one(
        "account.move",
        string="Invoice",
        required=True,
        readonly=True,
    )
    
    partner_id = fields.Many2one(
        "res.partner",
        string="Recipient Partner",
        required=True,
    )
    
    recipient_id = fields.Char(
        string="Recipient ID (DUNS/Y-tunnus)",
        required=True,
        help="The recipient's identifier",
    )
    
    additional_recipients = fields.Many2many(
        "res.partner",
        string="Additional Recipients",
        help="Send to multiple recipients",
    )
    
    method = fields.Selection(
        [
            ("single", "Send to Single Recipient"),
            ("multiple", "Send to Multiple Recipients"),
        ],
        string="Send Method",
        default="single",
    )
    
    notes = fields.Text(
        string="Notes",
        help="Internal notes about this transmission",
    )
    
    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        """Auto-fill recipient ID from partner"""
        
        if self.partner_id:
            # Try to use VAT/ref as recipient ID
            recipient_id = self.partner_id.ref or self.partner_id.vat or ""
            if recipient_id:
                self.recipient_id = recipient_id.replace("-", "")
    
    @api.onchange("method")
    def _onchange_method(self):
        """Clear additional recipients when switching to single"""
        
        if self.method == "single":
            self.additional_recipients = False
    
    def action_send_finvoice(self):
        """Send Finvoice to selected recipients"""
        
        self.ensure_one()
        
        if not self.invoice_id:
            raise UserError("No invoice selected")
        
        # Build list of recipients
        recipients = []
        
        if self.method == "single":
            recipients.append((self.partner_id, self.recipient_id))
        else:
            recipients.append((self.partner_id, self.recipient_id))
            for partner in self.additional_recipients:
                recipient_id = partner.ref or partner.vat or ""
                if recipient_id:
                    recipients.append((partner, recipient_id.replace("-", "")))
        
        if not recipients:
            raise UserError("No valid recipients selected")
        
        # Send Finvoice
        sent_count = self.invoice_id.send_finvoice_to_partners(recipients)
        
        # Create notification
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Finvoice Sent",
                "message": f"Successfully sent Finvoice to {sent_count} recipient(s)",
                "type": "success",
            },
        }
