# About the Pico ZX Printer
The Pico ZX Printer replaces the ZX Printer or TS2040 printer. It is an emulator board that plugs into the expansion bus. It captures printouts and stores them for download, viewing, and printing from a web app. It works with the Sinclair ZX81 and ZX Spectrum, as well as their Timex Sinclair counterparts the TS1000 and TS2068.

<picture>
  <img alt="Sinclair logo" src="images/sinclairlogo.svg" height="30">
</picture>
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp;
<picture>
  <img alt="Timex Sinclair logo" src="images/timexsinclairlogo.svg" height="30">
</picture>
</p>

In association with [TimexSinclair.com](https://timexsinclair.com/) and in collaboration with the TS-Team.

## 🔧 Getting started
The app is made up of two parts, the web app, and the backend that runs on the Pico ZX Printer board.

To install the backend:

- Turn off your Sinclair/Timex computer
- Connect the Pico ZX Printer to the expansion bus at the back
- Connect a USB cable between the Pico ZX Printer and your PC
- Open the [Pico ZX Printer web app](https://ohnosec.github.io/ZXPrinter) from a Chrome, Edge, or Opera web browser
- Click on the USB cable at the top right &nbsp; <picture><img alt="Timex Sinclair logo" src="images/usbcable.svg" height="17"></picture>
- Select the `Board CDC` or `Board in FS mode` port for the Pico and click `Connect`
- Click on the USB cable at the top right again
- Click the `Install` button
- On the install dialog click the `Start` button
- Turn on your Sinclair/Timex computer

The initial install will take some time. The next time you install it will be much faster as it only installs files that have changed.

Once installed you can manage the Pico ZX Printer from the [Pico ZX Printer web app](https://ohnosec.github.io/ZXPrinter), or open the web app directly from the Pico ZX Printer.

## 🔦 What does it do?
The Pico ZX Printer captures printouts from your Sinclair/Timex computer and stores them internally. These printouts can then be viewed, downloaded, and printed from your PC using a web app. The printouts can also be copied to an SD card for long term storage or transfer.

As well as the basic function of capturing printouts from your Sinclair/Timex computer, it also supports direct printing to dot matrix printers without any host PC. A dot matrix printer can be connected to the Pico ZX Printer directly over a serial or parallel cable.

Here's a list of features:

- View printouts in a web browser
- Print to a printer on your PC
- Download printouts as image files in PNG, JPEG, or BMP format
- Converts printouts to text using OCR
- Converts printouts of program listings (LLIST) to ZMakebas files using OCR
- Can be connected over USB, or without cables, over a WIFI network
- Store and manage printouts on an SD card
- Self-host the web app on the Pico ZX Printer, or your PC
- Print directly to a dot matrix printer on a serial or parallel port (uses ESC/P and ESC/POS)

## ⚙️ How does it work?
Unlike other ZX printer alternatives back in the day, the Pico ZX Printer doesn't replace the internal ROM of the Sinclair/Timex computer. Instead it uses the existing printer functionality built into the Sinclair/Timex computer by emulating the protocol of the ZX Printer.

## 🚫 Does anything not work as expected?

Limitations of the web app:

- Only modern browsers are supported. It has only really been tested on Chrome
- Only Chrome, Edge, or Opera web browsers support USB
- Github hosting only allows connection over USB
- Self hosting on the Pico ZX Printer only allows connection over the network
- Self hosting on your PC allows connection over both USB and network

Limitations of the Pico ZX Printer:

- The COPY command on the unexpanded ZX81 and TS1000 doesn't work. If the Sinclair/Timex has more than 3.5KB of memory it works fine