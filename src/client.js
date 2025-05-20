import { islocal } from "./local.js"
import * as serial from "./serial.js"
import * as command from "./command.js"
import { setbusystate, showerror, errordefs, ShowError } from "./utils.js"

const requests = {
    getlog: {
      route: "log",
      method: "GET",
      command: "getlog",
      paramnames: []
    },
    setcapture: {
      route: "printer/capture/{state}",
      method: "PUT",
      command: "setcapture",
      paramnames: ["state"]
    },
    setendofline: {
        route: "printer/endofline/{char}",
        method: "PUT",
        command: "setendofline",
        paramnames: ["char"]
    },
    setendofprint: {
        route: "printer/endofprint/{char}",
        method: "PUT",
        command: "setendofprint",
        paramnames: ["char"]
    },
    setleftmargin: {
        route: "printer/leftmargin/{value}",
        method: "PUT",
        command: "setleftmargin",
        paramnames: ["value"]
    },
    setdensity: {
        route: "printer/density/{value}",
        method: "PUT",
        command: "setdensity",
        paramnames: ["value"]
    },
   setprttarget: {
      route: "printer/{target}",
      method: "PUT",
      command: "setprinter",
      paramnames: ["target"]
    },
    setserialsetting: {
      route: "printer/serial/settings",
      method: "PUT",
      command: "setserial",
      paramnames: ["baudrate", "bits", "parity", "stop"]
    },
    setserialflow: {
      route: "printer/serial/flow",
      method: "PUT",
      command: "setflow",
      paramnames: ["hardware", "software", "delayms"]
    },
    loadprintouts: {
      route: "printouts/{store}",
      method: "GET",
      command: "getprintouts",
      paramnames: ["store"]
    },
    loadprintout: {
      route: "printouts/{store}/{name}",
      method: "GET",
      command: "getprintout",
      paramnames: ["name", "store"]
    },
    deleteprintout: {
      route: "printouts/{store}/{name}",
      method: "DELETE",
      command: "deleteprintout",
      paramnames: ["name", "store"]
    },
    printprintout: {
      route: "printouts/{store}/{name}/printer",
      method: "PUT",
      command: "printprintout",
      paramnames: ["name", "store"]
    },
    copyprintout: {
        route: "printouts/{tostore}",
        method: "POST",
        command: "copyprintout",
        paramnames: ["name", "fromstore", "tostore"],
        body: { source: "/printouts/{fromstore}/{name}" }
    },
    about: {
      route: "about",
      method: "GET",
      command: "about",
      paramnames: []
    },
}

let userCancelController = new AbortController();

function isrunninglocal() {
    return islocal == "true";
}

function hasaddress() {
    return isrunninglocal() || getaddress();
}

function gettargetpath() {
    return isrunninglocal() ? '' : `http://${getaddress()}`;
}

function gettargeturl() {
    const currenturl = window.location;
    const targetpath = gettargetpath();
    const targeturl = URL.parse(targetpath, currenturl);
    return targeturl;
}

function iscloudconnection() {
    const useserial = document.getElementById('useserial');
    return !(useserial.checked && serial.isconnected) && ishttpallowed();
}

function getaddress() {
    return localStorage.getItem('address');
}

function setaddress(address) {
    localStorage.setItem('address', address);
}

function fetchcancel() {
    userCancelController.abort();
}

function ishttpallowed() {
    const currenturl = window.location;
    const targeturl = gettargeturl();
    if (currenturl.protocol === "https:" && targeturl.protocol === "http:") {
        return false;
    }
    return true;
}

async function fetchrequest(basepath, request, params = {}, timeout = 5000) {
    if (!ishttpallowed()) {
        throw new ShowError("Secure web hosting (https) doesn't support using the web to access ZX Printer");
    }
    userCancelController = new AbortController();
    const body = request.body ? structuredClone(request.body) : {};
    let path = request.route;
    for(const paramname of request.paramnames) {
      if (request.route.includes(`{${paramname}}`)) {
        path = path.replace(`{${paramname}}`, params[paramname]);
      } else {
        if (!request.body) {
            body[paramname] = params[paramname];
        }
      }
    }
    if (request.body) {
        for (const property in body) {
            if (typeof property === 'string' || property instanceof String) {
                for(const paramname of request.paramnames) {
                    body[property] = body[property].replace(`{${paramname}}`, params[paramname]);
                }
            }
        }
    }
    const requestinit = {
      method: request.method,
      headers: {},
      signal: AbortSignal.any([
        userCancelController.signal,
        AbortSignal.timeout(timeout)
      ])
    };
    if (request.method == "POST" || request.method == "PUT") {
      requestinit['body'] = JSON.stringify(body);
      requestinit.headers["Content-Type"] = "application/json"
    }
    const startTime = (new Date()).getTime();
    let response = await fetch(`${basepath}/${path}`, requestinit);
    const responseMs = (new Date()).getTime() - startTime;
    console.log(`Request to '${path}' took ${responseMs} ms`);
    return response;
}

async function execrequest(request, params = {}, timeout = 5000, showerrortoast = true) {
  try {
    if (timeout>500) setbusystate(true);
    if (iscloudconnection()) {
        if (!hasaddress()) {
            throw new ShowError("The web address has not been set");
        }
        const response = await fetchrequest(gettargetpath(), request, params, timeout);
        if (!response.ok) {
            throw new Error(`The web request was not ok (${response.status}:${response.statusText})`)
        }
        return await response.json();
    } else {
        if (!serial.isconnected) {
            throw new ShowError("The serial port is not connected");
        }
        const cmdparams = [];
        for (const paramname of request.paramnames) {
            cmdparams.push(params[paramname]);
        }
        return await command.execute(request.command, cmdparams, timeout);
    }
  } catch(error) {
    if (error.name != "AbortError") {
        if (showerrortoast) {
            showerror(errordefs.requesterror, null, error);
        }
    }
    throw error;
  } finally {
    if (timeout>500) setbusystate(false);
  }
}

export {
    requests,
    isrunninglocal,
    hasaddress,
    gettargeturl,
    getaddress,
    setaddress,
    execrequest,
    fetchcancel,
    fetchrequest,
    ishttpallowed,
    gettargetpath
}