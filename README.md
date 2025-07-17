# About the Pico ZX Printer
The Pico ZX Printer replaces the ZX Printer or TS2040 printer. It's an emulator board that plugs into the expansion bus. It captures printouts and stores them for download, viewing, and printing from a web app. It works with the Sinclair ZX81 and ZX Spectrum, as well as their Timex Sinclair counterparts the TS1000 and TS2068.

<picture>
  <img alt="Sinclair logo" src="docs/images/sinclairlogo.svg" height="30">
</picture>
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp;
<picture>
  <img alt="Timex Sinclair logo" src="docs/images/timexsinclairlogo.svg" height="30">
</picture>
</p>

In association with [TimexSinclair.com](https://timexsinclair.com/) and in collaboration with the TS-Team.

## 🔦 What does it do?
The Pico ZX Printer captures printouts from your Sinclair/Timex computer and stores them internally. These printouts can then be viewed, downloaded, and printed from your PC using a web app. The printouts can also be copied to an SD card for long term storage or transfer.

As well as the basic function of capturing printouts from your Sinclair/Timex computer, it also supports direct printing without any host PC. A printer can be connected to the Pico ZX Printer with a serial or parallel cable. Or it can print over the network to a network enabled printer. This makes it completley standalone and a direct replacement for a ZX Printer or TS2040 printer.

### List of features:

- View printouts in a web browser
- Print to a printer on your PC from the web browser
- Print to a serial or parallel printer with support for:
  - Epson compatible dot matrix printer
  - Thermal receipt printer
- Print to a network printer with support for:
  - Epson inkjet printer
- Download printouts as image files in PNG, JPEG, or BMP format
- Converts printouts to text
- Converts printouts of program listings (LLIST) to ZMakebas
- Can be connected over USB, or without cables, over a WIFI network
- Store and manage printouts on an SD card
- Self-host the web app on the Pico ZX Printer, or your PC

## 🔧 Getting started
The Pico ZX Printer is made up of two parts, the web app, and the backend that runs on the Pico ZX Printer board.

### To install or upgrade the backend

1. Turn off your Sinclair/Timex computer
2. Connect the Pico ZX Printer to the expansion bus at the back
3. Connect a USB cable between the Pico ZX Printer and your PC
4. Open the [Pico ZX Printer web app](https://ohnosec.github.io/ZXPrinter) from a Chrome, Edge, or Opera web browser
5. Click on the USB cable at the top right &nbsp; <picture><img alt="Timex Sinclair logo" src="docs/images/usbcable.svg" height="17"></picture>
6. Select the `Board CDC` or `Board in FS mode` port for the Pico and click `Connect`.
  If the USB port doesn't appear it may be that MicroPython isn't installed. See how to install MicroPython in [the note below](#micropython-install).
7. Click on the USB cable at the top right again
8. Click the `Install` button
9. On the install dialog click the `Start` button
10. Turn on your Sinclair/Timex computer

> [!NOTE]
> The initial install will take some time. The next time you install it will be much faster as it only copies files that have changed.

> [!TIP]
> Once installed you can manage the Pico ZX Printer from the [Pico ZX Printer web app](https://ohnosec.github.io/ZXPrinter).

<a name="micropython-install"></a>
<details>
<summary>NOTE: The backend runs on MicroPython. This should already be installed, but if you are building from scratch, or have replaced the Raspberry Pi Pico, you may have to reinstall. This is a one-time thing. Expand this section for details.</summary>

### To install MicroPython

First download the appropriate MicroPython file depending on your version of the Raspberry Pi Pico. Here's links to supported MicroPython UF2 files:

- [Pico](https://micropython.org/resources/firmware/RPI_PICO-20250415-v1.25.0.uf2)
- [Pico W](https://micropython.org/resources/firmware/RPI_PICO_W-20250415-v1.25.0.uf2)
- [Pico 2](https://micropython.org/resources/firmware/RPI_PICO2-20250415-v1.25.0.uf2)
- [Pico 2W](https://micropython.org/resources/firmware/RPI_PICO2_W-20250415-v1.25.0.uf2)

<details>
<summary>The latest MicroPython files can be found on the downloads page:</summary>
</p>

- [Pico downloads](https://micropython.org/download/RPI_PICO/)
- [Pico W downloads](https://micropython.org/download/RPI_PICO_W/)
- [Pico 2 downloads](https://micropython.org/download/RPI_PICO2/)
- [Pico 2W downloads](https://micropython.org/download/RPI_PICO2_W/)
</details>
</p>

Then on the Raspberry Pi Pico:
1. Push and hold the BOOTSEL button on the Pi Pico while connecting a USB cable to your PC
2. Release the button once your Pi Pico appears as a Mass Storage Device called RPI-RP2
3. Copy the UF2 file onto the RPI-RP2 volume
</details>

## ⚙️ How does it work?
Unlike other ZX printer alternatives back in the day, the Pico ZX Printer doesn't replace the internal ROM of the Sinclair/Timex computer. Instead it uses the existing printer functionality built-in to the Sinclair/Timex computer by emulating the protocol of the ZX Printer.

The code that runs on the ZX Printer is written in [MicroPython](https://micropython.org/). Most of the hardware interfacing uses the Pi Pico's Programmable I/O (PIO). This combined with Direct Memory Access (DMA) takes the real-time load off the Python code. The Python code runs multiple tasks, like the print capture, web server, and serial server, using [asyncio](https://docs.python.org/3/library/asyncio.html) coroutines.

## 🚫 Does anything not work as expected?

### Limitations of the web app

- Only modern browsers are supported. It's only been properly tested on Chrome
- Only designed to work on the desktop. Small screen devices have not been tested
- Only Chrome, Edge, or Opera web browsers currently support USB
- Github hosting only allows connection over USB
- Self hosting on the Pico ZX Printer only allows connection over the network
- Self hosting on your PC allows connection over both USB and network

### Limitations of the Pico ZX Printer

- The COPY command on the unexpanded ZX81 and TS1000 doesn't work. If the Sinclair/Timex has more than 3.5KB of memory it works fine