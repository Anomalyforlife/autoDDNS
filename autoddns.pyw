from http.client import HTTPSConnection
from time import sleep
from urllib.request import urlopen
from infi.systray import SysTrayIcon
from datetime import datetime
from threading import Thread
from sys import exit
from tkinter import Tk, Label, Button, Entry
from dotenv import dotenv_values

#read the credentials.env file

dotenv_filename = "credentials.env"

def mainDDNS(systray=None, ipv4=None, ipv6="None"):
    print(">> Starting ddns update..")

    url = dotenv_values(dotenv_filename)["URL"]

    token = dotenv_values(dotenv_filename)["TOKEN"]

    zone = dotenv_values(dotenv_filename)["ZONE"]

    #set the ip to the current ip of this device
    if (ipv4 == None):
        try:
            ipv4 = str(urlopen('http://ip.42.pl/raw').read()).split("'")[1]
        except:
            updatesLabel.configure(text = "No internet!")
            ipv4 = "0.0.0.0"
    if (ipv6 == "None") and (userHasIPv6==True):
        try:
            ipv6 = str(urlopen('http://v6.ipv6-test.com/api/myip.php').read()).split("'")[1]
        except:
            ipv6 = "None"

    print("---------------------------")
    print(">> Initialized IPv4: " + ipv4)
    print("--                      ---")
    print(">> Initialized IPv6: " + ipv6)
    print("---------------------------")
    #make the get request
    if ipv6 != "None":
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

def onStartLoop():
    global loopStarted
    global userHasInternet
    global userHasIPv6
    while loopStarted:
        global ipv4
        if connect():
           print( f"{datetime.now().strftime('%H:%M:%S')} | Connected!")
           if detectNewIP():
                mainDDNS()
                updatesLabel.configure(text = "DDNS updated!")
                txtIPv4.delete(0, 'end')
                txtIPv6.delete(0, 'end')
                try:
                    txtIPv4.insert(0, str(urlopen('http://ip.42.pl/raw').read()).split("'")[1])
                except:
                    txtIPv4.insert(0, "No Internet")
                if userHasIPv6:
                    try:
                        txtIPv6.insert(0, str(urlopen('http://v6.ipv6-test.com/api/myip.php').read()).split("'")[1])
                    except:
                        txtIPv6.insert(0, "None")
                        userHasIPv6 = False
                else:
                    txtIPv6.insert(0,"None")
        else: 
            print( f">> No internet!" )
        sleep(300)

def detectNewIP():
    global ipv4
    global ipv6
    global userHasIPv6
    global userHasInternet
    if userHasInternet:
        newIPv4 = str(urlopen('http://ip.42.pl/raw').read()).split("'")[1]
    else:
        newIPv4 = "None"
        return False
    if userHasIPv6:
        try:
            newIPv6 = str(urlopen('http://v6.ipv6-test.com/api/myip.php').read()).split("'")[1]
        except:
            newIPv6 = "None"
            userHasIPv6 = False
    else:
        newIPv6="None"
    if newIPv4 != ipv4:
        ipv4 = newIPv4
        ipv6 = newIPv6
        txtIPv4.insert(0, newIPv4)
        txtIPv6.insert(0, newIPv6)
        return True
    else:
        return False

def onQuit(systray):
    global loopStarted
    print(">> Quitting..")
    loopStarted = False
    exit(0)
        
def stopLoop():
    global loopStarted
    loopStarted = False
    print(">> Loop stopped!")
    updatesLabel.configure(text = "Loop stopped!")

def startLoop():
    global loopThread
    global loopStarted
    loopStarted = True
    print(">> Loop started!")
    if loopThread.is_alive():
        print(">> Loop already running!")
    else:
        loopThread = Thread(target=onStartLoop)
        loopThread.start()
    updatesLabel.configure(text = "Loop started!")


# Execute Tkinter
def showWindow(systray=None):
    root.deiconify()

##########################################################   VAR SETUP   ################################################################
global ipv4
global ipv6
global loopStarted
global loopThread
global userHasIPv6
global userHasInternet
userHasIPv6 = True
userHasInternet = True
loopStarted = True

try:
    ipv4 = str(urlopen('http://ip.42.pl/raw').read()).split("'")[1]
except:
    ipv4 = "None" 
    userHasInternet = False
    print(">> No internet!")

if userHasInternet:
    try:
        ipv6 = str(urlopen('http://v6.ipv6-test.com/api/myip.php').read()).split("'")[1]
    except:
        userHasIPv6 = False
        ipv6 = "None"
else:
    ipv6 = "None"
    print(">> Cannot check for IPv6, user has no internet!")
##########################################################   VAR SETUP   ################################################################


############################################ TKINTER ###################################################################################
root = Tk()

# root window title and dimension
root.iconbitmap(default='ddns.ico')
root.title("Automatic DDNS        by: @Λnomaly#0908")
# Set geometry(widthxheight)
root.geometry('450x175')

# adding a label to the root window
lblIPv4 = Label(root, text = f"IPv4: ", justify="left", height=3, width=10)
lblIPv4.grid(column =0, row =0)

lblIPv6 = Label(root, text = f"IPv6: ", justify="left", height=3, width=10)
lblIPv6.grid(column =0, row =1)

# adding Entry Field
txtIPv4 = Entry(root, width=40, font=('Arial', 10), fg='black', bg='white', bd=2)
if userHasInternet != False:
    txtIPv4.insert(0, str(urlopen('http://ip.42.pl/raw').read()).split("'")[1])
else:
    txtIPv4.insert(0, "None")
txtIPv4.grid(column =1, row =0)

txtIPv6 = Entry(root, width=40, font=('Arial', 10), fg='black', bg='white', bd=2)
if userHasInternet != False:
    if userHasIPv6:
        try:
            txtIPv6.insert(0, str(urlopen('http://v6.ipv6-test.com/api/myip.php').read()).split("'")[1])
        except:
            txtIPv6.insert(0, "None")
    else:
        txtIPv6.insert(0, "None")
else:
    txtIPv6.insert(0, "None")
txtIPv6.grid(column =1, row =1)

def setAutomatedIPs():
    txtIPv4.delete(0, 'end')
    txtIPv6.delete(0, 'end')
    if userHasInternet != False:
        txtIPv4.insert(0, str(urlopen('http://ip.42.pl/raw').read()).split("'")[1])
    else:
        txtIPv4.insert(0, "None")
    if userHasInternet != False:
        if userHasIPv6:
            try:
                txtIPv6.insert(0, str(urlopen('http://v6.ipv6-test.com/api/myip.php').read()).split("'")[1])
            except:
                txtIPv6.insert(0, "None")
        else:
            txtIPv6.insert(0, "None")
    else:
        txtIPv6.insert(0, "None")
    mainDDNS()
    startLoop()
    updatesLabel.configure(text = "Loop started!, IPs updated!")

def clickedIPv6():
    res = "IPv6: " + txtIPv6.get()
    lblIPv6.configure(text = res)

def updateManualDDNS():
    mainDDNS(ipv4=txtIPv4.get(), ipv6=txtIPv6.get())
    updatesLabel.configure(text = "DDNS updated!")

updatesLabel = Label(root, text = f"", justify="left",height=1, width=20, font=('Arial', 10), fg='black', bg='white', bd=2)
updatesLabel.grid(column=1, row=2)

# button widget with red color text inside
btn1 = Button(root, text="Automatic IPs", fg="green", command=setAutomatedIPs)
btn1.place(x=40, y=130)

btn2 = Button(root, text="Stop Loop", fg="orange", command=stopLoop)
btn2.place(x=140, y=130)

btn3 = Button(root, text="Start Loop", fg="blue", command=startLoop)
btn3.place(x=240, y=130)

btn4 = Button(root, text="Update", fg="blue", command=updateManualDDNS)
btn4.place(x=340, y=130)


############################################################################################################
menu_options = (("Show window", None, showWindow),("Update", None, mainDDNS),)
trayIconWin = SysTrayIcon("ddns.ico", "Automatic DDNS\nby Anomalyforlife", menu_options, on_quit=onQuit)
trayIconWin.start()

if userHasInternet != False:
    mainDDNS(ipv4=ipv4, ipv6=ipv6)
else:
    ipv4 = "None"
    ipv6 = "None"

loopThread = Thread(target=onStartLoop)
loopThread.start()

root.protocol("WM_DELETE_WINDOW", root.withdraw)
root.withdraw()
root.resizable(False, False) # Disable resizing the GUI
root.mainloop()
############################################################################################################