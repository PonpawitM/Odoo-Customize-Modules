import logging
from odoo import models, api
import requests
import json
from xml.etree import ElementTree as ET

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id and len(self.partner_id.name) == 13 and self.partner_id.name.isdigit():
            vat_number = self.partner_id.name

            # Check if a contact with this VAT number already exists
            existing_partner = self.env['res.partner'].search([('vat', '=', vat_number)], limit=1)
            if existing_partner:
                self.partner_id = existing_partner
                return

            try:
                # Construct the SOAP envelope
                soap_envelope = f"""<?xml version="1.0" encoding="utf-8"?>
                <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                  <soap:Body>
                    <Service xmlns="https://rdws.rd.go.th/JserviceRD3/vatserviceRD3">
                      <username>anonymous</username>
                      <password>anonymous</password>
                      <TIN>{vat_number}</TIN>
                      <Name></Name>
                      <ProvinceCode>0</ProvinceCode>
                      <BranchNumber>0</BranchNumber>
                      <AmphurCode>0</AmphurCode>
                    </Service>
                  </soap:Body>
                </soap:Envelope>"""

                headers = {
                    'Content-Type': 'text/xml; charset=utf-8',
                    'SOAPAction': 'https://rdws.rd.go.th/JserviceRD3/vatserviceRD3/Service'
                }

                response = requests.post(
                    'https://rdws.rd.go.th/jsonRD/vatserviceRD3.asmx',
                    data=soap_envelope,
                    headers=headers
                )

                # Log the API response for debugging
                logging.info(f"API Response: {response.text}")

                if response.status_code == 200:
                    # Parse the XML response to extract the JSON string
                    root = ET.fromstring(response.content)
                    
                    # Correct namespaces for the SOAP and ServiceResponse
                    ns = {
                        'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                        'ns1': 'https://rdws.rd.go.th/JserviceRD3/vatserviceRD3'
                    }
                    
                    # Extract ServiceResult from the response
                    service_result_element = root.find('.//ns1:ServiceResult', ns)
                    
                    if service_result_element is not None:
                        # Convert the JSON string to a Python dictionary
                        data = json.loads(service_result_element.text)
                        
                        # Update the VAT field
                        self.partner_id.vat = data.get('NID', [vat_number])[0]
                        
                        # Filter out the "-" values and construct the street and street2 fields
                        street_parts = [
                            data.get('BuildingName', [None])[0],
                            data.get('FloorNumber', [None])[0],
                            data.get('VillageName', [None])[0],
                            data.get('RoomNumber', [None])[0]
                        ]
                        street2_parts = [
                            data.get('HouseNumber', [None])[0],
                            data.get('MooNumber', [None])[0],
                            data.get('SoiName', [None])[0],
                            data.get('StreetName', [None])[0],
                            data.get('Thambol', [None])[0]
                        ]

                        # Remove any parts that are "-" or None
                        self.partner_id.street = ' '.join(filter(lambda x: x and x != '-', street_parts))
                        self.partner_id.street2 = ' '.join(filter(lambda x: x and x != '-', street2_parts))
                        
                        # Update other address details
                        branch_name = data.get('BranchName', [None])[0]
                        amphur_name = data.get('Amphur', [None])[0]
                        postcode = data.get('PostCode', [None])[0]
                        province_name = data.get('Province', [None])[0]

                        if branch_name:
                            self.partner_id.name = branch_name
                            self.partner_id.city = amphur_name if amphur_name else ''
                            self.partner_id.zip = postcode if postcode else ''
                            self.partner_id.state_id = self.env['res.country.state'].search([('name', '=', province_name)], limit=1).id if province_name else False
                            self.partner_id.country_id = self.env['res.country'].search([('code', '=', 'TH')], limit=1).id
                        else:
                            self.partner_id = False
                            return {
                                'warning': {
                                    'title': "VAT Number Not Found",
                                    'message': "No customer found with the provided VAT number."
                                }
                            }
                    else:
                        logging.warning(f"No ServiceResult found in the response: {ET.tostring(root, encoding='unicode')}")
                        self.partner_id = False
                        return {
                            'warning': {
                                'title': "API Error",
                                'message': "No valid data returned from the API."
                            }
                        }
                else:
                    self.partner_id = False
                    return {
                        'warning': {
                            'title': "API Error",
                            'message': "Failed to fetch data from the API."
                        }
                    }
            except Exception as e:
                logging.error(f"Error during API call: {e}")
                self.partner_id = False
                return {
                    'warning': {
                        'title': "API Error",
                        'message': f"An error occurred while fetching data: {e}"
                    }
                }
