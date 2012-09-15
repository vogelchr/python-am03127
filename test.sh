#!/bin/sh

port="-p /dev/ttyUSB1 -b 9600 --verbose"

# first set dummy page 'Z' while the other pages are populated

/bin/echo -en "\033ACPlease wait....." | \
./am03127.py $port --settime --schedule='Z' --page='Z' --lead=A --lag=A --wait=3 --message

(/bin/echo -en "\033ABhost:\033AC "; hostname) | ./am03127.py $port --page='A' --lead=A --lag=A --wait=3 --message
(/bin/echo -en "\033ABuptime:\033AC "; uptime)     | ./am03127.py $port --page='B' --lead=E --lag=A --wait=3 --message
(/bin/echo -en "\033ABuname:\033AC ";  uname -a)   | ./am03127.py $port --page='C' --lead=E --lag=A --wait=3 --message


(
	read temp </sys/class/hwmon/hwmon0/temp1_input
	read name </sys/class/hwmon/hwmon0/name

	temp=$(( temp / 1000 ))
	/bin/echo -en "\033ABtemp0:\033AC $name $temp degC"
) | ./am03127.py $port --page='D' --lead=E --lag=A --wait=3 --schedule ABCD --message
