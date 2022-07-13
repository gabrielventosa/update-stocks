from __future__ import print_function
from asyncio.windows_events import NULL

import os.path
import json
import requests

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# The ID and range of a sample spreadsheet.

def main():

    """Configuration"""
    with open('config.json', 'r') as f:
        config = json.load(f)
    SPREADSHEET_ID = config['SPREADSHEET_ID']
    SAMPLE_RANGE_NAME =  config['RANGE_NAME']
    MAGENTO_SITE = config['MAGENTO_SITE']
    MAGENTO_ADMIN_USER = config['MAGENTO_ADMIN_USER']
    MAGENTO_ADMIN_PASSWORD = config['MAGENTO_ADMIN_PASSWORD']

    bearer = getMagentoAuth(MAGENTO_SITE, MAGENTO_ADMIN_USER, MAGENTO_ADMIN_PASSWORD)
    if bearer == NULL:
        print ("Error loging in Magento")
        return
    


    """Sheets API
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('sheets', 'v4', credentials=creds)

        # Call the Sheets API
        sheet = service.spreadsheets()
        sheet_metadata = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        sheets = sheet_metadata.get('sheets', '')
        for s in sheets:
            title = s.get("properties", {}).get("title", "Sheet1")
            sheet_id = s.get("properties", {}).get("sheetId", 0)
            print('Model Name: %s' % title)

            result = sheet.values().get(spreadsheetId=SPREADSHEET_ID,
                                        range=title+"!"+SAMPLE_RANGE_NAME).execute()
            values = result.get('values', [])

            if not values:
                print('No data found.')
                continue
            else:
                    print('SKU, Qty')
                    for row in values:
                        if len(row) >=4:
                            # Print columns A and E, which correspond to indices 0 and 4.
                            sku = row[0]+"-"+row[1]+"-"+row[2]
                            magitem = getMagentoStockItem(MAGENTO_SITE, bearer, sku)
                            if (magitem):
                                qty = magitem['extension_attributes']['stock_item']['qty']
                                #print(f'Quantity in Magento Store: {qty}')
                                print (f'SKU: {sku}, Qty in sheet: {row[3]}, Qty in Magento: {qty}')
                            else:
                                print('Not Found in Magento')
                        else:
                            print('No qty')
    except HttpError as err:
        print(err)

def getMagentoAuth(url, user, password):
    url = url+'/index.php/rest/V1/integration/admin/token'
    auth = {"username": user, "password": password}
    response = requests.post(url, json=auth)
    if response.status_code == 200:
        return response.json()
    else:
        print("Error in authentication, error code: %s " % response.status_code)
        return NULL

def getMagentoStockItem(url, bearer, sku):
    url = url+'/index.php/rest/V1/products/'+sku
    header = {"Authorization": "Bearer "+bearer}
    response = requests.get(url, headers=header)
    if response.status_code == 200:
        return response.json()
    else:
        message = response.json()['message']
        print(f'Error getting product, message: {message} \nsku: {sku}  \nurl: {url}')
        return NULL

if __name__ == '__main__':
    main()