import { hidedropdown, showerror, errordefs, toggledropdown } from "./utils.js"
import { isrunninglocal, getaddress, setaddress, fetchrequest, requests, ishttpallowed } from "./client.js"
import * as event from "./event.js"
import * as websocket from "./websocket.js"

async function cloudrefreshstate() {
    cloudclearstate();
    cloudupstate.classList.add("active");
}

function cloudclearstate() {
    const cloudupstate = document.getElementById("cloudupstate");
    const clouddownstate = document.getElementById("clouddownstate");
    cloudupstate.classList.remove("active");
    clouddownstate.classList.remove("active");
}

websocket.connecthandler.add(async () => {
    await cloudrefreshstate();
});

websocket.disconnecthandler.add(async () => {
    cloudclearstate();
});

function cloudhide() {
    hidedropdown('clouddropdown');
}

async function cloudmenu() {
    const testelement = document.getElementById('cloudtest');
    if (!ishttpallowed()) {
        testelement.classList.add("d-none");
    } else {
        testelement.classList.remove("d-none");
    }
    cloudaddresschange();
    toggledropdown('clouddropdown');
}

async function cloudaddresschange() {
    const cloudaddresselement = document.getElementById('cloudaddress');
    const cloudtestbutton = document.getElementById('cloudtest');
    const cloudopenbutton = document.getElementById('cloudopen');

    const address = cloudaddresselement.value.trim();
    if (address=="") {
        cloudtestbutton.disabled = true;
        cloudopenbutton.disabled = true;
    } else {
        cloudtestbutton.disabled = false;
        cloudopenbutton.disabled = false;
    }
    if (!ishttpallowed()) {
        cloudtestbutton.disabled = true;
    }
}

async function cloudaddresspaste() {
    const cloudaddresselement = document.getElementById('cloudaddress');
    const address = await navigator.clipboard.readText();
    cloudaddresselement.value = address;
}

async function cloudopen() {
    const cloudaddresselement = document.getElementById('cloudaddress');
    const address = cloudaddresselement.value.trim();
    window.open(`http://${address}`, '_blank');
    cloudhide();
}

async function cloudsave() {
    const cloudaddresselement = document.getElementById('cloudaddress');
    const address = cloudaddresselement.value.trim();
    setaddress(address);
    event.connect();
    cloudhide();
}

function cloudload() {
    const cloudaddresselement = document.getElementById('cloudaddress');
    const address = getaddress();
    cloudaddresselement.value = address;
}

async function cloudtest() {
    const cloudaddresselement = document.getElementById('cloudaddress');

    const cloudtestbutton = document.getElementById('cloudtest');
    const cloudtestspinner = document.getElementById('cloudtestspinner');
    const cloudtestgood = document.getElementById('cloudtestgood');
    const cloudtestbad = document.getElementById('cloudtestbad');
    cloudtestbutton.disabled = true;
    cloudtestspinner.classList.remove("d-none");
    cloudtestgood.classList.add("d-none");
    cloudtestbad.classList.add("d-none");

    let connected = false;
    const address = cloudaddresselement.value.trim();

    try {
        const response = await fetchrequest(`http://${address}`, requests.about);
        if (response.ok) {
            const jsonresponse = await response.json();
            if (jsonresponse.version) {
                connected = true;
            }
        }
    } catch(error) {
        showerror(errordefs.requesterror, null, error);
    }

    if (connected) {
        cloudtestgood.classList.remove("d-none");
    } else {
        cloudtestbad.classList.remove("d-none");
    }
    cloudtestspinner.classList.add("d-none");
    cloudtestbutton.disabled = false;
}

if (!isrunninglocal()) {
    document.getElementById("clouddropdown").style.display = "block";
}

cloudload();

export {
    cloudmenu,
    cloudaddresschange, cloudaddresspaste,
    cloudopen, cloudsave, cloudtest
}