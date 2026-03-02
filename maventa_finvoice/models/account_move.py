import logging
from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    """Extend account.move with Finvoice capabilities"""
    
    _inherit = "account.move"
    
    finvoice_status = fields.Selection(
        [
            ("not_sent", "Not Sent"),
            ("pending", "Pending"),
            ("sent", "Sent"),
            ("delivered", "Delivered"),
            ("failed", "Failed"),
        ],
        string="Finvoice Status",
        default="not_sent",
        readonly=True,
        help="Status of Finvoice transmission",
    )
    
    finvoice_logs = fields.One2many(
        "finvoice.log",
        "invoice_id",
        string="Finvoice Logs",
        readonly=True,
    )
    
    finvoice_recipients = fields.Many2many(
        "res.partner",
        string="Finvoice Recipients",
        help="Partners to send this invoice as Finvoice",
    )
    
    send_finvoice = fields.Boolean(
        string="Send as Finvoice",
        default=False,
    )
    
    finvoice_error = fields.Text(
        string="Finvoice Error",
        readonly=True,
    )
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to initialize Finvoice status"""
        
        result = super().create(vals_list)
        
        # Initialize variables for auto-send feature
        for move in result:
            if move.company_id.maventa_config_ids:
                config = move.company_id.maventa_config_ids.filtered(
                    lambda c: c.active
                )
                if config and config[0].auto_send_invoices:
                    move.send_finvoice = True
        
        return result
    
    def action_post(self):
        """Post invoice and optionally send Finvoice"""
        
        result = super().action_post()
        
        # Auto-send Finvoice if configured
        for move in self:
            if (
                move.move_type in ["out_invoice", "out_refund"]
                and move.send_finvoice
                and move.partner_id
            ):
                try:
                    move._send_finvoice_automatically()
                except Exception as e:
                    _logger.warning(
                        f"Auto-send Finvoice failed for {move.name}: {str(e)}"
                    )
        
        return result
    
    def _send_finvoice_automatically(self):
        """Send Finvoice automatically on invoice validation"""
        
        self.ensure_one()
        
        config = self.company_id.maventa_config_ids.filtered(lambda c: c.active)
        if not config:
            _logger.warning(
                f"No active Maventa configuration for company {self.company_id.name}"
            )
            return
        
        # Use partner ID or name as recipient
        recipient_id = self.partner_id.ref or self.partner_id.vat or ""
        if not recipient_id:
            _logger.warning(
                f"No valid recipient ID for partner {self.partner_id.name}"
            )
            return
        
        self.send_finvoice_to_partners(
            [(self.partner_id, recipient_id)],
            silent=True,
        )
    
    def action_send_finvoice(self):
        """Action to open send wizard"""
        
        if self.move_type not in ["out_invoice", "out_refund"]:
            raise UserError("Only customer invoices can be sent as Finvoice")
        
        return {
            "type": "ir.actions.act_window",
            "name": "Send Finvoice",
            "res_model": "finvoice.send.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_invoice_id": self.id,
                "default_partner_id": self.partner_id.id,
            },
        }
    
    def send_finvoice_to_partners(self, recipients, silent=False):
        """Send Finvoice to specified partners
        
        Args:
            recipients: List of tuples (partner, recipient_id)
            silent: If True, don't raise exceptions during send
        """
        
        self.ensure_one()
        
        if self.move_type not in ["out_invoice", "out_refund"]:
            raise UserError("Only customer invoices can be sent as Finvoice")
        
        config = self.company_id.maventa_config_ids.filtered(lambda c: c.active)
        if not config:
            raise UserError(
                "No active Maventa configuration found for this company"
            )
        
        config = config[0]
        
        try:
            from .finvoice_handler import FinvoiceHandler
            
            handler = FinvoiceHandler(config)
            
            # Generate Finvoice XML
            finvoice_xml = handler.generate_finvoice_xml(self)
            
            # Validate XML
            is_valid, validation_msg = handler.validate_finvoice_xml(finvoice_xml)
            if not is_valid:
                error_msg = f"Invalid Finvoice XML: {validation_msg}"
                self.finvoice_error = error_msg
                if not silent:
                    raise UserError(error_msg)
                return
            
            # Send to each recipient
            sent_count = 0
            for partner, recipient_id in recipients:
                # Create log entry
                log = self.env["finvoice.log"].create_log(
                    self,
                    recipient_id,
                    partner.name,
                    status="pending",
                )
                log.finvoice_xml = finvoice_xml.decode("utf-8")
                
                # Send via Maventa
                result = handler.send_invoice_to_maventa(
                    finvoice_xml,
                    recipient_id,
                    self,
                )
                
                if result["success"]:
                    log.update_as_sent(
                        result.get("maventa_id"),
                        str(result.get("response")),
                    )
                    sent_count += 1
                    _logger.info(
                        f"Finvoice {self.name} sent to {partner.name} "
                        f"(Maventa ID: {result.get('maventa_id')})"
                    )
                else:
                    error_msg = result.get("error", "Unknown error")
                    log.update_as_failed(
                        error_msg,
                        str(result.get("response")),
                    )
                    _logger.error(
                        f"Failed to send Finvoice {self.name} to {partner.name}: {error_msg}"
                    )
            
            # Update invoice status
            if sent_count == len(recipients):
                self.finvoice_status = "sent"
                self.finvoice_error = ""
            elif sent_count > 0:
                self.finvoice_status = "sent"
                self.finvoice_error = f"Sent to {sent_count}/{len(recipients)} recipients"
            else:
                self.finvoice_status = "failed"
                self.finvoice_error = "Failed to send to any recipient"
            
            return sent_count
            
        except Exception as e:
            error_msg = f"Error sending Finvoice: {str(e)}"
            self.finvoice_error = error_msg
            _logger.exception(error_msg)
            
            if not silent:
                raise UserError(error_msg)
    
    def action_check_finvoice_status(self):
        """Check status of sent Finvoice invoices"""
        
        self.ensure_one()
        
        logs = self.finvoice_logs.filtered(lambda l: l.maventa_id)
        
        if not logs:
            raise UserError("No Finvoice records found for this invoice")
        
        updated_count = 0
        for log in logs:
            if log.check_status_from_maventa():
                updated_count += 1
        
        # Update main invoice status based on logs
        if logs:
            statuses = logs.mapped("status")
            if "delivered" in statuses:
                self.finvoice_status = "delivered"
            elif "sent" in statuses:
                self.finvoice_status = "sent"
            elif "failed" in statuses:
                self.finvoice_status = "failed"
        
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Status Updated",
                "message": f"Updated status for {updated_count} record(s)",
                "type": "success",
            },
        }
