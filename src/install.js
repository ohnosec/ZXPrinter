import * as command from "./command.js"
import * as network from "./network.js"

import { showerror, errordefs, ShowError } from "./utils.js"

async function fetchfile(url) {
    const response = await fetch(url);
    if (!response.ok) {
        throw new ShowError(`Could not get file '${url}' (${response.status})`)
    }
    return response;
}

async function play() {
    try {
        await command.executerepl(async (repl) => {
            const mainpy = await fetchfile("/main.py");
            const mainpytext = await mainpy.text();

            await repl.execute(mainpytext);

            const response = await serial.read("", 2000);

            console.log(`Python script running: ${response}`);
        });
    } catch (error) {
        showerror(errordefs.failedstart, undefined, error);
    }
}

async function uploadfiles(repl, files, callback) {
    let sourcefile = "";
    try {
        for(const file of files) {
            sourcefile = file.source;
            const targetfile = file.target;

            console.log(`Uploading ${sourcefile}`);

            const filefetch = await fetchfile(sourcefile);
            const filebuffer = await filefetch.arrayBuffer();

            await repl.put(targetfile, new Uint8Array(filebuffer));

            callback();
        }
    }
    catch(error) {
        console.log(`Failed to upload ${sourcefile} ${error}`);
        throw error;
    }
}

function updateprogress(progresselement, percent) {
    const percenttext = `${percent}%`;
    progresselement.style.width = percenttext;
    progresselement.textContent = percenttext;
}

async function getfiles() {
    const configfile = "files.json";

    const configfetch = await fetchfile(configfile);
    const config = await configfetch.json();

    return config;
}

async function install() {
    const installmodal = bootstrap.Modal.getInstance(document.getElementById("installmodal"));
    const installbutton = document.getElementById("installbutton");
    const cleancheckbox = document.getElementById("cleaninstall");
    installbutton.disabled = true;
    try {
        await command.executerepl(async (repl) => {
            const progresselement = document.getElementById("installprogress");
            updateprogress(progresselement, 0);

            if (cleancheckbox.checked) {
                await repl.removedir("", ["printout", "sd", "settings.json"])
            }

            const files = await getfiles();

            const todo = files.length;
            let done = 0;
            await uploadfiles(repl, files, () => {
                done += 1;
                updateprogress(progresselement, Math.floor(done / todo * 100));
            });

            updateprogress(progresselement, 100);

            console.log("Rebooting");
            await command.reboot();
            installmodal.hide();
        });
        await network.serialrefreshstate();
    } catch (error) {
        installmodal.hide();
        showerror(errordefs.failedinstall, undefined, error);
    } finally {
        installbutton.disabled = false;
    }
}

export { install, play }