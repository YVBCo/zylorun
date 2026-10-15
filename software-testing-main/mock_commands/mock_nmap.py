import time
import sys
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("host")
parser.add_argument("-p", "--port", action="append")
parser.add_argument("-sV", action="store_true")
args = parser.parse_args()

print(f"Starting Nmap 7.94 ( https://nmap.org ) at {time.strftime('%Y-%m-%d %H:%M')}")
time.sleep(0.5)
print(f"Nmap scan report for {args.host}")
print("Host is up (0.0012s latency).")

print("PORT   STATE SERVICE")
if args.port:
    for p in args.port:
        print(f"{p}/tcp open  unknown")
else:
    print("80/tcp open  http")
    print("443/tcp open  https")

if args.sV:
    print("Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .")

print(f"Nmap done: 1 IP address (1 host up) scanned in 1.0 seconds")
