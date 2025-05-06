const sleep = ms => new Promise(r => setTimeout(r, ms));

class Mutex {
    constructor() {
        this._lock = Promise.resolve()
    }

    acquire() {
        let release
        const lock = new Promise(resolve => release = resolve)
        const acquire = this._lock.then(() => release)
        this._lock = this._lock.then(() => lock)
        return acquire
    }
}

const loggerbufferlength = 32768;

class Logger {
    constructor() {
        this.buffer = "";
    }

    log(message) {
        this.buffer += message;
        this.buffer = this.buffer.slice(-loggerbufferlength);
    }

    get contents() {
        return this.buffer;
    }
};

function isdropdown(element) {
    for( ; element && element !== document; element = element.parentElement) {
        if (element.classList.contains("dropdown")) return true;
    }
    return false;
}

function hidedropdown(dropdownbuttonname) {
    const dropdownelement = document.getElementById(dropdownbuttonname);
    bootstrap.Dropdown.getOrCreateInstance(dropdownelement).hide();
}

function hidedropdowns(dropdowntarget = undefined) {
    let closed = false;
    const dropdownelements = document.getElementsByClassName("dropdown");
    for(let dropdownelement of dropdownelements) {
        const dropdownbutton = dropdownelement.getElementsByTagName("button")[0];
        if (dropdownbutton == dropdowntarget) {
            const opened = dropdownbutton.ariaExpanded == 'true';
            if (opened) closed = true;
        }
        bootstrap.Dropdown.getOrCreateInstance(dropdownbutton).hide();
    }
    return closed;
}

function toggledropdown(dropdownbuttonname) {
    const dropdownelement = document.getElementById(dropdownbuttonname);
    if (!hidedropdowns(dropdownelement)) {
        const dropdown = bootstrap.Dropdown.getOrCreateInstance(dropdownelement);
        dropdown.show();
    }
}

let busycount = 0;
function setbusystate(isbusy) {
    const spinner = document.getElementById("busyspinner");

    if (isbusy) {
        ++busycount;
        spinner.classList.remove("d-none");
    } else {
        if (--busycount <= 0) {
        busycount = 0;
        spinner.classList.add("d-none");
        }
    }
}

function errortoast(message) {
    const toastelement = document.getElementById("errortoast");
    const toastmessage = toastelement.getElementsByClassName("toast-body")[0];
    toastmessage.innerHTML = message.replace("\n", "<br>");
    const toast = new bootstrap.Toast(toastelement);
    toast.show();
}

const errordefs = {
    serialconnect: {
        message: "Serial port failed to connect"
    },
    failedstart: {
        toast: "Failed to start",
        message: "Python script failed to start"
    },
    failedreset: {
        toast: "Failed to reset",
        message: "Python failed to reset"
    },
    failedinstall: {
        toast: "Failed to install",
        message: "Failed to upload install files"
    },
    requesterror: {
        message: "Request failed"
    },
    commanderror: {
        message: "Command error"
    },
    commandfailed: {
        message: "Command failed"
    }
};

class ShowError extends Error {
    constructor(message, ...params) {
        super(...params);

        if (Error.captureStackTrace) {
            Error.captureStackTrace(this, ShowError);
        }

        this.name = "ShowError";
        this.message = message;
        this.date = new Date();
    }
}

function showerror(errordef, message, error) {
    let toastmessage;
    if(error instanceof ShowError) {
        toastmessage = error.message;
    } else {
        toastmessage = message ?? errordef.toast ?? errordef.message ?? "Unknown error";
    }
    errortoast(toastmessage);
    const consolemessage = message ?? errordef.message;
    if (error) {
        console.error(consolemessage, error);
    } else {
        console.error(consolemessage);
    }
}

export {
    sleep,
    Mutex,
    Logger,
    isdropdown, hidedropdown, hidedropdowns, toggledropdown,
    setbusystate,
    showerror, errordefs, ShowError
}