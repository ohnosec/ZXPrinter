import { sleep, hidedropdown, toggledropdown, hidedropdowns, showerror, errordefs } from "./utils.js"
import * as command from "./command.js"
import * as serial from "./serial.js"
import { ishttpallowed } from "./client.js"

const passwordplaceholder = '\x00\x00\x00\x00\x00';

async function networkavailable() {
    try {
        const response = await command.execute("about", [], 200);
        return response.network;
    } catch {
        return false;
    }
}

function networkupdate(response) {
    const networkaddresselement = document.getElementById('networkaddress');
    const networkaddresscopyelement = document.getElementById('networkaddresscopy');

    const networkstateonelement = document.getElementById('networkstateon');
    const networkstateoffelement = document.getElementById('networkstateoff');

    if(response.connected) {
        networkstateonelement.classList.add("active");
        networkstateoffelement.classList.remove("active");
    } else {
        networkstateonelement.classList.remove("active");
        networkstateoffelement.classList.add("active");
    }
    if(response.ip) {
        networkaddresselement.value = response.ip;
        networkaddresselement.disabled = false;
        networkaddresscopyelement.disabled = false;
    } else {
        networkaddresselement.value = "";
        networkaddresselement.placeholder = response.status;
        networkaddresselement.disabled = true;
        networkaddresscopyelement.disabled = true;
    }
}

async function networkpopulate() {
    const networknameelement = document.getElementById('networkname');
    const networkpasswordelement = document.getElementById('networkpassword');
    const networkhostnameelement = document.getElementById('networkhostname');
    const networklistelement = document.getElementById('networknamelist');
    const networkdropelement = document.getElementById('networknamedrop');

    let response;

    response = await command.execute("getnetwork", []);
    networknameelement.value = response.ssid;
    networkpasswordelement.value = passwordplaceholder;

    response = await command.execute("status", []);
    networkupdate(response);
    networkhostnameelement.value = response.hostname;

    if (!response.connecting) {
        response = await command.execute("scan", []);
        networklistelement.replaceChildren();
        response.sort((a,b) => b.rssi - a.rssi);
        response.forEach((item) => {
            const nametemplate = document.createElement('template');
            nametemplate.innerHTML = item.ssid.link("#");
            const namelink = nametemplate.content.firstChild;
            namelink.onclick = (el) => {
                const name = el.currentTarget.textContent;
                networknameelement.value = name;
            };
            namelink.classList.add("dropdown-item");
            const li = document.createElement('li');
            li.appendChild(namelink);
            networklistelement.appendChild(li);
        });
        networkdropelement.dataset.bsToggle = response.length==0 ? "" : "dropdown";
    }
}

function networkaddresscopy() {
    const networkaddresselement = document.getElementById('networkaddress');
    const networkaddresscopyelement = document.getElementById('networkaddresscopy');

    navigator.clipboard.writeText(networkaddresselement.value);

    const tooltip = bootstrap.Tooltip.getOrCreateInstance(networkaddresscopyelement);
    tooltip.setContent({ '.tooltip-inner': 'Copied' });
    tooltip.show();
}

async function networksave() {
    const networkhostnameelement = document.getElementById('networkhostname');
    const networknameelement = document.getElementById('networkname');
    const networkpasswordelement = document.getElementById('networkpassword');

    const params = [networkhostnameelement.value];
    await command.execute("sethostname", params);

    const params2 = [networknameelement.value];
    const password = networkpasswordelement.value;
    if (password && password!=passwordplaceholder) {
        params2.push(password);
    }
    await command.execute("setnetwork", params2);

    serialhide();
}

async function networktest() {
    const networknameelement = document.getElementById('networkname');
    const networkpasswordelement = document.getElementById('networkpassword');

    const networktestbutton = document.getElementById('networktest');
    const networktestspinner = document.getElementById('networktestspinner');
    const networktestgood = document.getElementById('networktestgood');
    const networktestbad = document.getElementById('networktestbad');
    networktestbutton.disabled = true;
    networktestspinner.classList.remove("d-none");
    networktestgood.classList.add("d-none");
    networktestbad.classList.add("d-none");

    const params = [networknameelement.value];
    const password = networkpasswordelement.value;
    if (password && password!=passwordplaceholder) {
        params.push(password);
    }
    await command.execute("connect", params);

    let connecting = true;
    let connected = false;
    do {
        const response = await command.execute("status", []);
        connecting = response.connecting;
        connected = response.connected;
        networkupdate(response);
        await sleep(500);
    } while(connecting);
    if (connected) {
        networktestgood.classList.remove("d-none");
    } else {
        networktestbad.classList.remove("d-none");
    }
    networktestspinner.classList.add("d-none");
    networktestbutton.disabled = false;
}

async function serialup() {
    try {
        await command.execute("about", [], 200);
        return true;
    } catch {
        return false;
    }
}

function serialhide() {
    hidedropdown('serialdropdown');
}

async function serialdisconnect() {
    await serial.disconnect();
    serialhide();
}

async function serialconnect() {
    if(serial.isconnected) {
        //const response = await command.execute("status", []);
        //networkupdate(response);
        const useserialopt = document.getElementById('useserialopt');
        const networksettings = document.getElementById('networksettings');
        const hasnetwork = await networkavailable();
        if (!ishttpallowed() || !hasnetwork) {
            const useserialchk = document.getElementById('useserial');
            useserialchk.checked = true;
            useserialopt.classList.add("d-none");
        } else {
            useserialopt.classList.remove("d-none");
        }
        if (!hasnetwork) {
            networksettings.classList.add("d-none");
        } else {
            networksettings.classList.remove("d-none");
        }
        toggledropdown('serialdropdown');
    } else {
        try {
            hidedropdowns();
            await serial.connect(); // this never exits
        } catch(error) {
            let message = error.message;
            if (error.cause && error.cause.name == "NetworkError") {
                message = "Serial port connection failed\nThe port may be in use"
            }
            showerror(errordefs.serialconnect, message, error);
        }
    }
}

async function serialreset() {
    const resetbutton = document.querySelector("#reset button");
    const installbutton = document.querySelector("#install button");
    resetbutton.disabled = true;
    installbutton.disabled = true;
    try {
        await command.reset();
        serialhide();
        await serialrefreshstate();
    } catch(error) {
        serialhide();
        showerror(errordefs.failedreset, undefined, error);
    } finally {
        resetbutton.disabled = false;
        installbutton.disabled = false;
    }
}

if (navigator.serial) {
    document.getElementById("serialdropdown").style.display = "block";
}

async function serialrefreshstate() {
    serialclearstate();
    if (await serialup()) {
        const serialupstate = document.getElementById("serialupstate");
        serialupstate.classList.add("active");
    } else {
        const serialdownstate = document.getElementById("serialdownstate");
        serialdownstate.classList.add("active");
    }
}

function serialclearstate() {
    const serialupstate = document.getElementById("serialupstate");
    const serialdownstate = document.getElementById("serialdownstate");
    serialupstate.classList.remove("active");
    serialdownstate.classList.remove("active");
}

serial.connecthandler.add(async () => {
    await serialrefreshstate();
});

serial.disconnecthandler.add(async () => {
    serialclearstate();
});

export {
    networkpopulate, networkaddresscopy, networktest, networksave,
    serialconnect, serialdisconnect, serialreset, serialrefreshstate
}