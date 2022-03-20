from distutils.log import info
from json import tool
from turtle import update
from dotenv import load_dotenv
import os
import requests
import json
import datetime
from dateutil.relativedelta import relativedelta
import time

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

WAX_ENDPOINTS = [
	"https://api.waxsweden.org",
	"https://wax.cryptolions.io",
	"https://wax.greymass.com",
	"https://wax.pink.gg",
];

ATOMIC_ENDPOINTS = [
	"https://aa.wax.blacklusion.io",
	"https://wax-atomic-api.eosphere.io",
	"https://wax.api.atomicassets.io",
	"https://wax.blokcrafters.io",
];

BLOCKCHAIN_ENDPOINTS = [
    "http://localhost:8001/" # you need to run my local api to run smart contracts
];

def get_account(contract, table, scope, bounds, tableIndex, index):
    if (index >= len(WAX_ENDPOINTS)):
        print("Accoubnt no working with actuals endpoints")
        return

    endpoint = WAX_ENDPOINTS[index]
    account_data = {
        "json": True,
        "code": contract,
        "scope": scope,
        "table": table,
        "lower_bound": bounds,
        "upper_bound": bounds,
        "index_position": tableIndex,
        "key_type": "i64",
        "limit": 100,
    }
    response = requests.post(endpoint + "/v1/chain/get_table_rows", data=json.dumps(account_data), headers={'content-type': 'application/json'})
    if response.status_code != 200:
        get_account(contract, scope, bounds, tableIndex, 1, index + 1)
    else:
        return (response.json())

def get_assets(asset_id, index):
    if (index >= len(WAX_ENDPOINTS)):
        raise ValueError("problem getting infos")

    response = requests.post(ATOMIC_ENDPOINTS[index] + "/atomicassets/v1/assets/" + asset_id, headers={'content-type': 'application/json'})
    if response.status_code != 200:
        get_assets(asset_id, index + 1)
    else:
        return (response.json())

def get_tools(inventory):
    tools_list = []
    for tools in inventory:
        if (tools != 0):
            tools_list.append(get_assets(tools, 0))
    return (tools_list)

def get_timer(account):
    last_mine = account["rows"][0]["last_mine"]
    return (datetime.datetime.fromtimestamp(last_mine) + relativedelta(minutes=int(os.getenv("MINING_TIME"))))

def update_inventory(account, key, index):
    if (index >= len(WAX_ENDPOINTS)):
        print("error while updating ressources")
        return
    endpoint_atomic = ATOMIC_ENDPOINTS[index]
    endpoint_wax = WAX_ENDPOINTS[index]

    # supply centers data
    gme = float(account["rows"][0]["energy"]) / 10000
    gmd = float(account["rows"][0]["goldmand"]) / 10000
    gmf = float(account["rows"][0]["food"]) / 10000
    gmm = float(account["rows"][0]["minerals"]) / 10000
    gmm_inventory = requests.post(endpoint_wax + "/v1/chain/get_currency_balance", data=json.dumps({"account": account["rows"][0]["miner"], "code": "goldmandiotk", "symbol": "GMM"}), headers={'content-type': 'application/json'})
    gme_inventory = requests.post(endpoint_wax + "/v1/chain/get_currency_balance", data=json.dumps({"account": account["rows"][0]["miner"], "code": "goldmandiotk", "symbol": "GME"}), headers={'content-type': 'application/json'})
    gmf_inventory = requests.post(endpoint_wax + "/v1/chain/get_currency_balance", data=json.dumps({"account": account["rows"][0]["miner"], "code": "goldmandiotk", "symbol": "GMF"}), headers={'content-type': 'application/json'})
    if gmm_inventory.status_code != 200 or gme_inventory.status_code != 200 or gmf_inventory.status_code != 200:
        update_inventory(account, key, index + 1)
    gmm_inventory = gmm_inventory.json()[0]
    gme_inventory = gme_inventory.json()[0]
    gmf_inventory = gmf_inventory.json()[0]

    hero = account["rows"][0]["hero"]
    headers = {'content-type': 'application/json'}
    response = requests.post(endpoint_atomic + "/atomicassets/v1/assets/" + hero, headers=headers)
    if response.status_code != 200:
        update_inventory(account, key, index + 1)

    race = response.json()["data"]["name"]
    if (race == "Alvars"):
        if (gme != 0):
            requests.post(BLOCKCHAIN_ENDPOINTS[0] + "/contract",
            data=json.dumps ({
                "pvkey": [key], "contract": [{ "account": "goldmandgame", "name": "withdraw","authorization": [{"actor": account["rows"][0]["miner"],"permission": "active",}],
                "data": {
                    "miner": account["rows"][0]["miner"],
                    "quantity": gme_inventory
                },}]}),
            headers={'content-type': 'application/json'})

    if (race == "Humans"):
        if (gmf != 0):
            requests.post(BLOCKCHAIN_ENDPOINTS[0] + "/contract",
            data=json.dumps ({
                "pvkey": [key], "contract": [{ "account": "goldmandgame", "name": "withdraw","authorization": [{"actor": account["rows"][0]["miner"],"permission": "active",}],
                "data": {
                    "miner": account["rows"][0]["miner"],
                    "quantity": gmf_inventory},
                }]}),
            headers={'content-type': 'application/json'})

    if (race == "Sevars"):
        if (gmm != 0):
            requests.post(BLOCKCHAIN_ENDPOINTS[0] + "/contract",
            data=json.dumps ({
                "pvkey": [key], "contract": [{ "account": "goldmandgame", "name": "withdraw","authorization": [{"actor": account["rows"][0]["miner"],"permission": "active",}],
                "data": {
                    "miner": account["rows"][0]["miner"],
                    "quantity": gmm_inventory},
                }]}),
            headers={'content-type': 'application/json'})

def mine(account, key):
    infos = json.dumps ({
        "pvkey": [key],
        "contract": [{
        "account": "goldmandgame",
        "name": "mine",
        "authorization": [{
            "actor": account["rows"][0]["miner"],
            "permission": "active",
        }],
        "data": {"miner": account["rows"][0]["miner"]},
        }]
    })
    contract = requests.post(BLOCKCHAIN_ENDPOINTS[0] + "/contract" , data=infos, headers={'content-type': 'application/json'})
    if contract.status_code != 200:
        print(contract.text)
        return

def checker():  

    # get account to work with
    account_name = os.getenv("ACCOUNT_NAME")
    account_key = os.getenv("PRIVATE_KEY")

    account = get_account("goldmandgame", "miners", "goldmandgame", account_name, 1, 0)
    mine_attemp = get_timer(account)

    print("[--------------------------------------------------]\n")
    if (datetime.datetime.now() > mine_attemp):
        print("mining ...\n")
        mine(account, account_key)
        account = get_account("goldmandgame", "miners", "goldmandgame", account_name, 1, 0)
        update_inventory(account, account_key, 0)
    else:
        update_inventory(account, account_key, 0)
        print("Nouvelle tentative de minage -> " + bcolors.WARNING + str(mine_attemp) + bcolors.ENDC + "\n")
    print("[--------------------------------------------------]\n")
    
if __name__ == "__main__":
    print("\n - {Running " + bcolors.OKCYAN + "magic's " + bcolors.ENDC + "bot for goldmand game} - \n")
    load_dotenv()
    while (1):
        checker()
        time.sleep(120)
        