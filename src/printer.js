import { adddropdownitem } from "./utils.js"
import { execrequest, requests } from "./client.js"
import { changegallerytarget } from "./gallery.js"

async function setprinterenable(enabled) {
    const galleryprints = document.querySelectorAll("#gallerytarget label");
    const printertest = document.getElementById("printertest");
    if (enabled.checked) {
        for(const galleryprint of galleryprints) {
            galleryprint.classList.remove("disabled");
        }
        printersettings.show();
        printertest.classList.remove("d-none");
        changeprintertarget();
    } else {
        for(const galleryprint of galleryprints) {
            galleryprint.classList.add("disabled");
        }
        document.getElementById("galtgtpc").checked = true;
        changegallerytarget();
        printersettings.hide();
        printertest.classList.add("d-none");
        await execrequest(requests.setprintertarget, {target:"off"});
    }
}

async function testprinter() {
    await execrequest(requests.testprinter)
}

// TODO: this is the same as network.networkscan, refactor!
async function findprinters() {
    const addresslistelement = document.getElementById("printeraddresslist");
    const addresselement = document.getElementById("printeraddress");

    addresslistelement.replaceChildren();
    adddropdownitem(addresslistelement, "Searching...");
    const printers = (await execrequest(requests.findprinters, { protocol: "raw" })).filter(
        p => p.pdl.includes('application/vnd.epson.escpr')
    );
    addresslistelement.replaceChildren();
    if (printers.length === 0) {
        adddropdownitem(addresslistelement, "No printers");
    } else {
        printers.sort((a,b) => a.address.localeCompare(b.address));
        printers.forEach((item) => {
            const addresstemplate = document.createElement("template");
            addresstemplate.innerHTML = item.address.link("#");
            const addresslink = addresstemplate.content.firstChild;
            addresslink.onclick = async (el) => {
                const address = el.currentTarget.textContent;
                addresselement.value = address;
                await setaddress(address)
            };
            addresslink.classList.add("dropdown-item");
            const listitem = document.createElement("li");
            listitem.appendChild(addresslink);
            addresslistelement.appendChild(listitem);
        });
    }
}

async function changeendofline() {
    const eol = document.querySelector("#printereol input[type='radio']:checked").value;

    await execrequest(requests.setendofline, {char:eol.toLowerCase()})
}

async function changeendofprint() {
    const eop = document.querySelector("#printereop input[type='radio']:checked").value;

    await execrequest(requests.setendofprint, {char:eop.toLowerCase()})
}

async function changeleftmargin() {
    const leftmargin = parseInt(document.getElementById("leftmargin").value);

    await execrequest(requests.setleftmargin, {value:leftmargin})
}

async function changedotdensity() {
    const density = parseInt(document.getElementById("dotdensity").value);

    await execrequest(requests.setdensity, {value:density})
}

async function changeprintertarget() {
    const target = document.querySelector("#printertarget input[type='radio']:checked").value;

    if (target.toLowerCase() == "serial") {
        serialsettings.show();
    } else {
        serialsettings.hide();
    }

    if (target.toLowerCase() == "network") {
        networksettings.show();
        const printerresponse = await execrequest(requests.getprinteraddress);
        const printeraddress = document.getElementById("printeraddress");
        printeraddress.value = printerresponse.address ?? "";
    } else {
        networksettings.hide();
    }

    await execrequest(requests.setprintertarget, {target:target})
}

async function changeserial() {
    const printerbaud = document.getElementById("printerbaud");
    const printerbaudvalue = printerbaud.value;
    const printerbits = document.querySelector("#printerbits input[type='radio']:checked").value;
    const printerparity = document.querySelector("#printerparity input[type='radio']:checked").value;
    const printerstop = document.querySelector("#printerstop input[type='radio']:checked").value;
    const printerdelay = parseInt(document.getElementById("serialdelay").value);

    if (printerbaudvalue.length == 0) {
        printerbaud.classList.add("is-invalid");
        return;
    }
    printerbaud.classList.remove("is-invalid");

    await execrequest(requests.setserialsetting, {
        baudrate: parseInt(printerbaudvalue),
        bits: parseInt(printerbits),
        parity: printerparity,
        stop: parseInt(printerstop)
    });

    let hardware = false;
    let software = false;

    switch(printerflow) {
        case "none":
            break;
        case "hardware":
            hardware = true;
            break;
        case "software":
            software = true;
            break;
        case "both":
            hardware = true;
            software = true;
        break;
    }

    await execrequest(requests.setserialflow, {
        hardware: hardware,
        software: software,
        delayms: printerdelay
    });
}

async function setaddress(address) {
    await execrequest(requests.setprinteraddress, {address:address});
}

async function changeaddress(event) {
    const address = event.target.value.trim();

    await setaddress(address);
}

const prtbaud = document.getElementById("printerbaud");
const prtbauddrop = document.getElementById("printerbauddrop");
prtbauddrop.addEventListener("hide.bs.dropdown", async event => {
    const target = event.clickEvent.target;
    if (target.classList.contains("dropdown-item")) {
        const value = target.innerText;
        prtbaud.value = value;
        prtbaud.classList.remove("is-invalid");
        await changeserial()
    }
})

const printersettingselement = document.getElementById("printersettings");
const printersettings = bootstrap.Collapse.getOrCreateInstance(printersettingselement, {
    toggle: false
});

const serialsettingseelement = document.getElementById("serialsettings");
const serialsettings = bootstrap.Collapse.getOrCreateInstance(serialsettingseelement, {
    toggle: false
});

const serialoptionseelement = document.getElementById("serialoptions");
const serialoptions = bootstrap.Collapse.getOrCreateInstance(serialoptionseelement, {
    toggle: false
});

const printoptionselement = document.getElementById("printoptions");
const printoptions = bootstrap.Collapse.getOrCreateInstance(printoptionselement, {
  toggle: false
});

const networksettingseelement = document.getElementById("printernetwork");
const networksettings = bootstrap.Collapse.getOrCreateInstance(networksettingseelement, {
    toggle: false
});

const printeropt = document.getElementById("printersettings");
printeropt.addEventListener("show.bs.collapse", async (event) => {
    switch(event.target.id) {
        case "printersettings":
            printoptions.hide();
            serialoptions.hide();
            break;
        case "serialoptions":
            printoptions.hide();
            break;
        case "printoptions":
            serialoptions.hide();
            break;
    }
});

const addressdropelement = document.getElementById("printeraddressdrop");
addressdropelement.addEventListener("show.bs.dropdown", async () => {
    await findprinters();
});

document.getElementById("printereol").addEventListener("change", changeendofline);
document.getElementById("printereop").addEventListener("change", changeendofprint);
document.getElementById("leftmargin").addEventListener("change", changeleftmargin);
document.getElementById("dotdensity").addEventListener("change", changedotdensity);
document.getElementById("printertarget").addEventListener("change", changeprintertarget);
document.getElementById("serialsettings").addEventListener("change", changeserial);
document.getElementById("printeraddress").addEventListener("focusout", changeaddress)

export {
    setprinterenable,
    testprinter
}