from __future__ import print_function
from asyncio.windows_events import NULL
from math import pi, gcd, ceil

import os.path
import json
from turtle import up
import requests
from  urllib.parse import quote

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

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

    CLEAR_COLORS = ['Verde', 'Rojo', 'Fiusha', 'Cobalto', 'Blanco', 'Nude', 'Beige', 'Mica Camel', 'LIla', 'Camel']
    DARK_COLORS = ['Negro']
    PRODUCTION_LOT =[1,2,3,3,2,1]

    bearer = getMagentoAuth(MAGENTO_SITE, MAGENTO_ADMIN_USER, MAGENTO_ADMIN_PASSWORD)
    if bearer is None:
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

        total_pieces = 0
        pieces_by_size = {}
        pieces_by_color = {}
        dark_pieces = {}
        clear_pieces = {}
        items = getMagentoOrderItems(MAGENTO_SITE, bearer,str(9))
        for i in items['items']:
            sku = i['sku']
            size = sku.split('-')[2] 
            color = sku.split('-')[1]           
                #parent_item_id = i['parent_item_id']
            qty_ordered = i['qty_ordered']
            total_pieces = total_pieces + qty_ordered
            qty_backordered = 0
            try:
                qty_backordered = i['qty_backordered']
            except:
                pass
            print(f'SKU: {sku}, Qty: {qty_ordered}')
            if size not in pieces_by_size:
                pieces_by_size[size] = 0
            if color not in pieces_by_color:
                pieces_by_color[color] = 0
            """   
            if color in CLEAR_COLORS:
                clear_pieces +=qty_ordered
            if color in DARK_COLORS:
                dark_pieces +=qty_ordered
            """
            if color in CLEAR_COLORS:
                if size not in clear_pieces:
                    clear_pieces[size] =0
                clear_pieces[size] += qty_ordered
            else:
                if size not in dark_pieces:
                    dark_pieces[size] =0
                dark_pieces[size] += qty_ordered

            pieces_by_size[size] = pieces_by_size[size]+qty_ordered
            pieces_by_color[color] = pieces_by_color[color]+qty_ordered
            #print(size)
            print(f'Total pieces: {total_pieces}')
            print(f'Clear pieces: {clear_pieces}')
            print(f'Dark pieces: {dark_pieces}')
        print(pieces_by_size)
        print(pieces_by_color)
        print(f'Total pieces: {total_pieces}')
        print(f'Clear pieces: {clear_pieces}')
        print(f'Dark pieces: {dark_pieces}')
        darks = dark_pieces.values()
        clears = clear_pieces.values()
        dark_gcd = gcd(*darks)
        clear_gcd = gcd(*clears)
        print(f'GCD Clear: {clear_gcd}, GCD Dark: {dark_gcd}')
       
        lot = PRODUCTION_LOT
        cuts_clear = getCutNumbers(clears, lot)
        cuts_dark = getCutNumbers(darks, lot)
        print(f'Cuts Clear: {cuts_clear}, Cuts Darks: {cuts_dark}')


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
        return None

def getMagentoStockItem(url, bearer, sku):
    url = url+quote('/index.php/rest/V1/products/'+sku)
    header = {"Authorization": "Bearer "+bearer}
    response = requests.get(url, headers=header)
    if response.status_code == 200:
        return response.json()
    else:
        message = response.json()['message']
        print(f'Error getting product, message: {message} \nsku: {sku}  \nurl: {url}')
        return None

def updateMagentoStockItemQty(url, bearer, product, qty):
    sku = product["sku"]
    item_id = str(product['extension_attributes']['stock_item']["item_id"])
    url = url+quote('/index.php/rest/V1/products/' + sku + '/stockItems/' + item_id)
    header = {'Authorization': 'Bearer '+bearer, 'content-type': 'application/json'}
    response = requests.get(url, headers=header)
    update = {"stockItem":{"qty": qty, "is_in_stock": "true"}}
    response = requests.put(url, headers=header, data=json.dumps(update))
    if response.status_code != 200:
        message = response.json()['message']
        print(f'Error updating product, message: {message} \nsku: {sku}  \nurl: {url} \ndata : {json.dumps(update)}')
        return None

def getMagentoOrderItems(url, bearer, orderId):
    """
    url = url+quote('/index.php/rest/V1/orders/' + orderId )
    """
    url = url+ '/index.php/rest/V1/orders/items?' + \
    'searchCriteria[filter_groups][0][filters][0][field]=order_id&' + \
    'searchCriteria[filter_groups][0][filters][0][value]=' + orderId +'&' + \
    'searchCriteria[filter_groups][1][filters][0][field]=product_type&' + \
    'searchCriteria[filter_groups][1][filters][0][value]=simple&' + \
    'searchCriteria[filter_groups][1][filters][1][field]=product_type&' + \
    'searchCriteria[filter_groups][1][filters][1][value]=virtual'
    header = {'Authorization': 'Bearer '+bearer, 'content-type': 'application/json'}
    response = requests.get(url, headers=header)
    if response.status_code != 200:
        message = response.json()['message']
        print(f'Error updating product, message: {message}   \nurl: {url}')
        return None
    return response.json()

def getCutNumbers(requested, lot):
    n = list(map((lambda a,b: ceil(a/b)), requested, lot))
    return max(n)

if __name__ == '__main__':
    main()