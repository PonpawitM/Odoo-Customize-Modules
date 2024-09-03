{
    'name': 'Partner VAT API Integration',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Automatically fetch customer details using VAT number and update partner information',
    'description': """
        This module integrates with the Thai Revenue Department's API to automatically fetch customer details
        based on a VAT number entered in the Sales Order. It prevents duplicate entries by checking if a contact
        with the same VAT number already exists. If found, the existing contact is used.
        The module also formats and updates the partner's address fields.
    """,
    'author': 'Ponpawit Metajiraroj',
    'depends': ['sale', 'contacts'],
    'installable': True,
    'application': False,
}
