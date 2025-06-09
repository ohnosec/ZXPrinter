# About the Pico ZX Printer
The Pico ZX Printer is a ZX Printer emulator board that plugs into the expansion bus. It captures printouts and stores them for download, viewing, and printing from a web browser. It works with the Sinclair ZX81 and ZX Spectrum, as well as their Timex Sinclair counterparts the TS1000 and TS2068.

<picture>
  <img alt="Sinclair logo" src="images/sinclairlogo.svg" height="30">
</picture>
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp;
<picture>
  <img alt="Timex Sinclair logo" src="images/timexsinclairlogo.svg" height="30">
</picture>

## 🔧 Getting started
The app is made up of two parts, the web app, and the backend that runs on the Pico ZX Printer board. The web app can be viewed directly from GitHub, or self hosted on the Pico ZX Printer itself.

To install the backend:
- Turn off your ZX/Timex computer
- Connect the Pico ZX Printer to the expansion bus at the back
- Connect a USB cable between the Pico ZX Printer and your PC
- Open the [Pico ZX Printer web app](https://ohnosec.github.io/ZXPrinter) from a Chrome, Edge, or Opera browser
- Click on the USB cable at the top right &nbsp; <picture><img alt="Timex Sinclair logo" src="images/usbcable.svg" height="17"></picture>
- Select the `Board CDC` port for the Pico and click `Connect`
- Click on the USB cable at the top right again
- Click the `Install` button
- On the install dialog click the `Install` button

The initial install will take some time. The next time you install it will be much faster as it will only install files that have changed.