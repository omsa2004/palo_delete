import requests
import json
import urllib3
import re
from getpass import getpass
from IPy import IP
import logging
from logging.handlers import RotatingFileHandler

#-----------------------------------------------#
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger('BlockIP')
logger.setLevel(logging.INFO)

handler = RotatingFileHandler("./Logs/log.log", maxBytes=5000, backupCount=10)
handler.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s - %(filename)s - %(levelname)s - %(message)s")

handler.setFormatter(formatter)
logger.addHandler(handler)

willBeDeletedAddresses=[]
Iplist =[]


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


def GetIP_list(ip_address,key,Address_device_group_name,Iplist):
    list_address_url = f'https://{ip_address}/restapi/v10.1/Objects/Addresses?location=device-group&device-group={Address_device_group_name}'
    list_address_payload = {}
    headers = {
        'X-PAN-KEY': key
            }
    response = requests.get(list_address_url, headers=headers, data=list_address_payload, verify=False)
    if response.status_code == 200:
            def getname(item,address):
                try:
                    if re.search(item,address["ip-netmask"]):
                        willBeDeletedAddresses.append(address["@name"])
                except:
                    pass

            for item in Iplist:
                try:
                    x=list(filter(lambda address: getname(item,address),response.json()["result"]["entry"]))
                except:
                    pass
    else:
        logger.warning(f'{response.json()["details"][0]["causes"][0]["description"]}')
    logger.info(f'found these addresses {willBeDeletedAddresses} in the {Address_device_group_name}')



def delete_from_address_group(ip_address, key,devicegroup, AddressGroup_name,willBeDeletedAddresses):
    del_from_group_url = f'https://{ip_address}/restapi/v10.1/Objects/AddressGroups?location=device-group&device-group={devicegroup}&name={AddressGroup_name}'
    del_from_group_payload = ""
    headers = {
    'Content-Type': 'application/json',
    'X-PAN-KEY': key
    }
    response = requests.get(del_from_group_url, headers=headers, verify=False)
    if response.status_code == 200:
        try:
            existingTags = response.json()["result"]["entry"][0]['tag']['member']
            del_from_group_payload = json.dumps({
            "entry": {
                "@name": AddressGroup_name,
                "static": {
                "member": list(set(response.json()["result"]["entry"][0]['static']['member']) - set(willBeDeletedAddresses))
                },
                "tag": {
                    "member": existingTags
                }
            }
            })

        except:
            del_from_group_payload = json.dumps({
            "entry": {
                "@name": AddressGroup_name,
                "static": {
                "member": list(set(response.json()["result"]["entry"][0]['static']['member']) - set(willBeDeletedAddresses))
                }
            }
            })
    
        response = requests.put(del_from_group_url, headers=headers,data=del_from_group_payload, verify=False)
        if response.status_code == 200:
            logger.info(f'{willBeDeletedAddresses} deleted from {AddressGroup_name}')
            return True
        else:
            logger.error(f"Failed to add delete address to the device group {AddressGroup_name}")
            return False
    else:
        logger.error("Failed to get existing addresses objects to group")
        return False



def delete_address_objects(ip_address, key, Address_device_group_name,address):

    del_address_url = f'https://{ip_address}/restapi/v10.1/Objects/Addresses?location=device-group&device-group={Address_device_group_name}&name={address}'
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
    with open("TobeDeleted.txt","r+") as f:
        lines = f.readlines()
        if lines:
            for  line in lines:
                try:
                    if IP(line.strip()):
                        Iplist.append(str(line.strip()))
                except:
                    logger.warning(f"Line {line}, is not a valid IP")
                    continue
            f.truncate(0)
    for DeviceGroup in AddressGroup_device_group_name:        
        GetIP_list(firewall_ip, API_Key,DeviceGroup,Iplist)

    if willBeDeletedAddresses !=[]:
        
        for DeviceGroup in AddressGroup_device_group_name:
            for addressGroup in AddressGroup_name:
                logger.info(f'Checking {DeviceGroup} address group {addressGroup} for the IPs that will be removed')
                delete_from_address_group(firewall_ip, API_Key, DeviceGroup,addressGroup, willBeDeletedAddresses)

        for address in willBeDeletedAddresses:
            for DeviceGroup in AddressGroup_device_group_name:
                logger.info(f'removing {address} from {DeviceGroup}')
                delete_address_objects(firewall_ip, API_Key, DeviceGroup,address)
        
    else: 
        logger.info(f'TobeDeleted.txt has no valid IPs')




            
if __name__ == "__main__":


    username = input("Enter Username:")

    if not username:
        print("you didn't enter a valid hostname")
    if username:
        password = getpass(f"Enter Password of the user {username}: ")
    
    firewall_ip = "panorama.bswhealth.org/"
    Address_device_group_name=["TXPLA-HPPLAN-MER-FW","Shared"] # this is where the address device group located 
    AddressGroup_device_group_name = ["TXPLA-HPPLAN-MER-FW","Shared"] # this is where the address group device group located 
    AddressGroup_name = ["SNOW-MID-SERVERS"] # address group name
    API_Key = login_firewall(firewall_ip, username, password)
    if API_Key:
        ReadIPs()
