from http.client import HTTPSConnection
from urllib.request import urlopen
from dotenv import dotenv_values
from detectIP import getIPv4, getIPv6
#read the credentials.env file

dotenv_filename = "credentials.env"

def mainDDNS(ipv4, ipv6):
    print(">> Starting ddns update..")

    url = dotenv_values(dotenv_filename)["URL"]

    token = dotenv_values(dotenv_filename)["TOKEN"]

    zone = dotenv_values(dotenv_filename)["ZONE"]

    #set the ip to the current ip of this device

    print("---------------------------")
    print(">> Initialized IPv4: " + ipv4)
    print("--                      ---")
    print(">> Initialized IPv6: " + ipv6)
    print("---------------------------")
    #make the get request
    if ipv6 != None:
        x = urlopen(url + "?hostname=" + zone + "&ipv4=" + ipv4 + "&ipv6="  + ipv6 + "&token=" + token)
    else:
        if connect():
            x = urlopen(url + "?hostname=" + zone + "&ipv4=" + ipv4 + "&token=" + token)
            response = str(x.read()).split("'")[1]
            print(">> "+ response)
        else:
            print(">> No internet")
        
def connect():
    global userHasInternet
    conn = HTTPSConnection("google.com", timeout=2)
    try:
        conn.request("HEAD", "/")
        userHasInternet = True
        return True
    except Exception:
        userHasInternet = False
        return False
    finally:
        conn.close()
        
if __name__ == "__main__":
    ipv4 = getIPv4()
    ipv6 = getIPv6()
    mainDDNS(ipv4, ipv6)