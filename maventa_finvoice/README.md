# Maventa Finvoice Module for Odoo 19

This Odoo 19 Enterprise module enables sending electronic invoices in Finvoice format through the Maventa operator's API.

## Features

- **Maventa API Integration**: Connect to Maventa's invoice transmission service
- **Finvoice Format Generation**: Automatically generate invoices in Finvoice XML format
- **Easy Invoice Sending**: Send invoices to customers via the Maventa network
- **Batch Transmission**: Send to multiple recipients simultaneously
- **Status Tracking**: Real-time tracking of invoice delivery status
- **Error Handling**: Comprehensive error logging and reporting
- **Auto-send**: Optional automatic sending when invoices are validated
- **Test Mode**: Support for Maventa sandbox environment

## Installation

1. Download and extract this module to your Odoo `addons` directory
2. Install required Python packages:
   ```bash
   pip install requests lxml
   ```
3. In Odoo, go to Apps and search for "Maventa Finvoice"
4. Click Install

## Configuration

### Setting up Maventa API Connection

1. Go to **Accounting > Maventa Finvoice > Configuration > Maventa API Configuration**
2. Click "Create" to add a new configuration
3. Fill in the following fields:
   - **Company**: Select the company this configuration applies to
   - **Maventa API Base URL**: Usually `https://masend.maventa.com/api/v1`
   - **API Username**: Your Maventa API username
   - **API Password**: Your Maventa API password
   - **Customer ID**: Your organization ID at Maventa
   - **Sender ID (DUNS/Y-tunnus)**: Your organization's identifier
   - **Test Mode**: Check this to use Maventa's sandbox environment

4. Click "Test Connection" to verify your credentials

## Usage

### Sending a Finvoice Invoice

1. Create and validate a customer invoice as normal
2. Once the invoice is in "Posted" status, click the **"Send Finvoice"** button
3. In the wizard that opens:
   - Select the recipient partner
   - Verify or enter the recipient's ID (Y-tunnus/DUNS)
   - Optionally add more recipients for bulk sending
4. Click "Send Finvoice"

### Automatic Sending

To automatically send invoices as Finvoice when they are validated:

1. Go to Maventa API Configuration
2. Check the "Automatically Send Invoices" option
3. Save

### Checking Invoice Status

1. On any invoice that was sent as Finvoice, click "Check Finvoice Status"
2. The status will be updated from Maventa's system

### Viewing Transmission Logs

1. Go to **Accounting > Maventa Finvoice > Finvoice Transmission Logs**
2. View details of all sent invoices
3. Click a log entry to see:
   - Full XML content
   - API responses
   - Error messages
   - Delivery status

## Finvoice Format

This module generates Finvoice 3.2.2 format XML documents containing:

- Invoice metadata (ID, dates, type)
- Supplier/seller information
- Customer/buyer information  
- Line items with descriptions and prices
- Monetary totals (subtotal, tax, total due)

## Error Handling

If invoice sending fails:

1. Check the **Finvoice Logs** for detailed error messages
2. Verify the recipient's ID is correct
3. Test the Maventa connection in the Configuration
4. Check that the invoice has all required information

## API Compatibility

- Odoo 19.0+
- Python 3.8+
- Maventa API v1

## Dependencies

- `requests` - HTTP library for API calls
- `lxml` - XML processing

## License

LGPL-3

## Support

For issues related to:
- **Odoo** - Contact your Odoo provider
- **Maventa API** - Contact Maventa Support
- **This Module** - Contact your system administrator

## Additional Information

### Invoice Status Values

- **Not Sent**: Invoice hasn't been sent as Finvoice yet
- **Pending**: Finvoice is being processed  
- **Sent**: Finvoice has been successfully transmitted to Maventa
- **Delivered**: Recipient has confirmed receipt
- **Failed**: Transmission failed, check error message

### Supported Invoice Types

- Customer Invoices (out_invoice)
- Customer Refunds (out_refund)

Vendor invoices cannot be sent as Finvoice through this module.
