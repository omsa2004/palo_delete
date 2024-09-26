import requests
import os
import json
import urllib3
import re
from getpass import getpass
import time
import logging
from logging.handlers import RotatingFileHandler

#-----------------------------------------------#
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger('DeletedIP')
logger.setLevel(logging.INFO)

handler = RotatingFileHandler("./Logs/log.log", maxBytes=5000, backupCount=10)
handler.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s - %(filename)s - %(levelname)s - %(message)s")

handler.setFormatter(formatter)
logger.addHandler(handler)



toBeRemPath = "./toBeRemoved/"
willBeDeletedAddresses = []




def login_firewall(ip_address, user, password):
    login_url = f'https://{ip_address}/api/?type=keygen'
    login_payload = {
        'user': user,
        'password': password
    }
    response = requests.post(login_url, data=login_payload, verify=False)
    if response.status_code == 200:
        logger.info("API Key generated successfully")
        clean = re.compile("<.*?>")
        return re.sub(clean,"",response.text)
    else:
        logger.error("Login Failed, Check user and password")
        return None


def CheckIP (ip_address, key,deviceGroup, groupName,address):
    list_address_url = f'https://{ip_address}/restapi/v10.1/Objects/AddressGroups?location=device-group&device-group={deviceGroup}&name={groupName}'
    headers = {
    'Content-Type': 'application/json',
    'X-PAN-KEY': key
    }
    response = requests.get(list_address_url, headers=headers, verify=False)
    if response.status_code == 200:

            try:
                logger.info(f'checking if {address} in {groupName} located in {deviceGroup}')
                X = list(filter(lambda item: item == address,response.json()["result"]["entry"][0]['static']['member']))
                if X != []:
                    return True
                else:
                    return False

            except:
                logger.warning(f'Failed to filter {groupName} in {deviceGroup}')


    else:
        logger.warning(f'{response.json()["details"][0]["causes"][0]["description"]}')


def delete_from_address_group(ip_address, key,devicegroup, groupName,address):
    del_from_group_url = f'https://{ip_address}/restapi/v10.1/Objects/AddressGroups?location=device-group&device-group={devicegroup}&name={groupName}'
    del_from_group_payload = ""
    headers = {
    'Content-Type': 'application/json',
    'X-PAN-KEY': key
    }
    response = requests.get(del_from_group_url, headers=headers, verify=False)
    if response.status_code == 200:

        iplist = response.json()["result"]["entry"][0]['static']['member']
        iplist.remove(address)
        try:
            existingTags = response.json()["result"]["entry"]['tag']['member']
            del_from_group_payload = json.dumps({
            "entry": {
                "@name": groupName,
                "static": {
                "member": iplist
                },
                "tag": {
                    "member": existingTags
                }
            }
            })

        except:
            del_from_group_payload = json.dumps({
            "entry": {
                "@name": groupName,
                "static": {
                "member": iplist
                }
            }
            })
  
        response = requests.put(del_from_group_url, headers=headers,data=del_from_group_payload, verify=False)
        if response.status_code == 200:
            logger.info(f'{address} deleted from {groupName}')
            return True
        else:
            logger.error(f"Failed to add delete address to the device group {groupName}")
            return False
    else:
        logger.error("Failed to get existing addresses objects to group")
        return False



def delete_address_objects(ip_address, key, groupName,address):

    del_address_url = f'https://{ip_address}/restapi/v10.1/Objects/Addresses?location=device-group&device-group={groupName}&name={address}'
    del_address_payload = {}
    headers = {
        'X-PAN-KEY': key
            }
    response = requests.delete(del_address_url, headers=headers, data=del_address_payload, verify=False)
    if response.status_code == 200:
        logger.info(f'Address {address} has been removed successfully')
    else:
        logger.warning(response.json()["details"][0]["causes"][0]["description"])






def ReadIPs():
    global willBeDeletedAddresses
    numberOfAddress =0
    GroupIndex= 0
    numberOfGroup = 0
    AdresssIndex =0
    for fileindex,file in enumerate(os.listdir(toBeRemPath)) :
        willBeDeletedAddresses = []
        if file.endswith(".csv"):
            with open(toBeRemPath+file,"r+") as f:
                for index,line in enumerate(f):
                    spaceAndCommas = re.sub((r'(,){2,}'),',',(re.sub(r"(,\s+)", ',', line)))
                    cleantxt = re.sub((r'(")'),'',spaceAndCommas).rstrip(',')
                    if re.findall(r'Address \(', cleantxt):
                        numberOfAddress = int(re.search('([1-9])',cleantxt.strip()).group(1))
                        AdresssIndex = index

                    if (numberOfAddress>0) & (index > AdresssIndex):
                        numberOfAddress -= 1
                        willBeDeletedAddresses.append((cleantxt.split(",")[0],cleantxt.split(",")[2]))

                    if re.findall(r'Address Group \(', cleantxt):
                        numberOfGroup = int(re.search('([1-9])',cleantxt.strip()).group(1))
                        GroupIndex = index

                    if (numberOfGroup>0) & (index > GroupIndex):
                        groupName =cleantxt.split(",")[0]
                        deviceGroup=cleantxt.split(",")[2]
                        numberOfGroup -= 1
                        for address in willBeDeletedAddresses:
                            if CheckIP (firewall_ip,API_Key,deviceGroup,groupName,address[0]):
                                delete_from_address_group(firewall_ip, API_Key,deviceGroup, groupName,address[0])

                            else:
                                logger.info(f" didn't find {address[0]} in {groupName} located in {deviceGroup}")
                                pass
        for address in willBeDeletedAddresses:
            delete_address_objects(firewall_ip, API_Key, address[1],address[0])
        timestamp = time.strftime('%b%d_%y_%I%M%p')
        newname = f'Completed_{timestamp}({str(fileindex)}).csv'
        os.rename(f"{toBeRemPath}{file}",f"./Completed/{newname}")

if __name__ == "__main__":


    username = input("Enter Username:")
    if not username:
        print("you didn't enter a valid username")
    if username:
        password = getpass(f"Enter Password of the user {username}: ")

    firewall_ip = "panorama.bswhealth.org/"
    API_Key = login_firewall(firewall_ip, username, password)
    if API_Key:
        ReadIPs()