To get the RISC-V QEMU portion running:

Windows
Download and install https://www.qemu.org/download/

Download and install https://openvpn.net/client/

Run this in PowerShell:

Get-NetAdapter | Where-Object {$_.InterfaceDescription -like "*TAP*"} #Take note of the adapter name

Rename-NetAdapter -Name "TAP-Windows Adapter V9" -NewName "tap0" #Make sure the TAP-Windows Adapter V9 portion matches the return value from above

To wrap a U-Boot header around the boot.txt network script (allowing U-Boot use of the network script):

 mkimage -T script -C none -n "Boot Script" -d boot.txt boot.scr.uimg

 If a DHCP, TFTP, and Web server are not already configured, one may run:

 .\RISC-V\server\python dhcp.py
 
 .\RISC-V\server\python tftp.py
 
 .\RISC-V\server\python web.py

 To boot the image from the network, run:

 .\RISC-V\networkBoot.bat

 To convert the device tree to JSON:

 python .\deviceTreeToJson.py .\tftp\[MAC address].dbt out.json
