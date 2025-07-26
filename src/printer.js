import { adddropdownitem, MemoryCache } from "./utils.js"
import { execrequest, requests } from "./client.js"
import { changegallerytarget } from "./gallery.js"

async function showprinter() {
    const printerresponse = await execrequest(requests.getprinter);
    const printerenabledelement = document.getElementById("printerenable");
    const printertarget = printerresponse.target;
    const printerenabled = printertarget !== "off";
    printerenabledelement.checked = printerenabled;
    refreshprinter(printerenabled);
    refreshprintertarget(printertarget);
}

function refreshprinter(printerenabled) {
    const galleryprints = document.querySelectorAll("#gallerytarget label");
    const printertest = document.getElementById("printertest");
    if (printerenabled) {
        for(const galleryprint of galleryprints) {
            galleryprint.classList.remove("disabled");
        }
        printersettings.show();
        printertest.classList.remove("d-none");
        printoptions.hide();
    } else {
        for(const galleryprint of galleryprints) {
            galleryprint.classList.add("disabled");
        }
        document.getElementById("galtgtpc").checked = true;
        changegallerytarget();
        printersettings.hide();
        printertest.classList.add("d-none");
    }
}

async function setprinterenable(enabled) {
    refreshprinter(enabled.checked);
    if (enabled.checked) {
        await changeprintertarget();
    } else {
        await execrequest(requests.setprintertarget, {target:"off"});
    }
}

async function testprinter() {
    await execrequest(requests.testprinter)
}

async function setprinterprotocol(dropdownelement) {
    const inputelement = document.getElementById("printerlanguage");
    inputelement.value = dropdownelement.textContent;
    const protocol = dropdownelement.dataset.protocol;
    await execrequest(requests.setprinterprotocol, { "protocol": protocol });
}

async function setprintercustom(customelement) {
    const option = document.getElementById("printerlanguageoption");
    if (customelement.checked) {
        option.classList.remove("d-none");
        const language = document.getElementById("printerlanguage");
        const firstlanguage = language.parentElement.querySelector("ul > li");
        await setprinterprotocol(firstlanguage);
    } else {
        option.classList.add("d-none");
        await execrequest(requests.setprinterprotocol, { "protocol": "auto" });
    }
}

const printercache = new MemoryCache();

// TODO: this is very similar to network.networkscan, refactor!
async function findprinters(printerprotocol = "raw") {
    const addresslistelement = document.getElementById("printeraddresslist");
    const addresselement = document.getElementById("printeraddress");
    const customelement = document.getElementById("printercustom");

    addresslistelement.replaceChildren();
    adddropdownitem(addresslistelement, "Searching...");
    const printersfound = await execrequest(requests.findprinters, { protocol: printerprotocol });
    printersfound.forEach((printer) => {
        printercache.set(`${printerprotocol}\t${printer.address}`, printer);
    });
    const printers = [...printercache.items()].filter(
        ([key, printer]) => {
            const [protocol, ] = key.split("\t");
            if (protocol === printerprotocol) {
                return customelement.checked ? true : printer.pdl.includes('application/vnd.epson.escpr')
            }
            return false;
        }).map(([, printer]) => printer);
    addresslistelement.replaceChildren();
    if (printers.length === 0) {
        adddropdownitem(addresslistelement, "No printers");
    } else {
        printers.sort((a,b) => a.address.localeCompare(b.address));
        printers.forEach((printer) => {
            const addresstemplate = document.createElement("template");
            addresstemplate.innerHTML = printer.address.link("#");
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

async function refreshprintertarget(target) {
    printoptions.hide();

    if (target == "serial") {
        const serialtarget = document.getElementById("prttgtserial");
        serialtarget.checked = true;
        serialsettings.show();
    } else {
        serialsettings.hide();
    }

    if (target == "parallel") {
        const paralleltarget = document.getElementById("prttgtparallel");
        paralleltarget.checked = true;
    }

    if (target == "network") {
        const networktarget = document.getElementById("prttgtnetwork");
        networktarget.checked = true;
        networksettings.show();
        const addressresponse = await execrequest(requests.getprinteraddress);
        const printeraddress = document.getElementById("printeraddress");
        printeraddress.value = addressresponse.address ?? "";
        const protocolresponse = await execrequest(requests.getprinterprotocol);
        const customelement = document.getElementById("printercustom");
        customelement.checked = protocolresponse.protocol != "auto";
        const option = document.getElementById("printerlanguageoption");
        if (customelement.checked) {
            option.classList.remove("d-none");
            const language = document.getElementById("printerlanguage");
            const firstlanguage = language.parentElement.querySelector("ul > li");
            const inputelement = document.getElementById("printerlanguage");
            inputelement.value = firstlanguage.textContent;
        } else {
            option.classList.add("d-none");
        }
    } else {
        networksettings.hide();
    }
}

async function changeprintertarget() {
    const target = document.querySelector("#printertarget input[type='radio']:checked").value;

    await refreshprintertarget(target.toLowerCase());

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
document.getElementById("menuprinter").addEventListener("active", showprinter)

export {
    setprinterenable,
    setprinterprotocol,
    setprintercustom,
    testprinter
}