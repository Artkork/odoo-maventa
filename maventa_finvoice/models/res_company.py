from odoo import fields, models


class ResCompany(models.Model):
    """Extend res.company with Maventa configuration relation"""

    _inherit = "res.company"

    maventa_config_ids = fields.One2many(
        "maventa.config",
        "company_id",
        string="Maventa Configurations",
    )
