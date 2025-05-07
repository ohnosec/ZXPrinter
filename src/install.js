import * as command from "./command.js"

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
            const mainpy = await fetchfile('/main.py');
            const mainpytext = await mainpy.text();

            await repl.execute(mainpytext);

            const response = await serial.read("", 2000);

            console.log(`Python script running: ${response}`);
        });
    } catch (error) {
        showerror(errordefs.failedstart, undefined, error);
    }
}

async function uploadconfig(repl, configfile, filenames, callback) {
    let filename = "";
    try {
        let filefolder = configfile.split("/").slice(0,-1).join("/");
        if (filefolder !== "") filefolder += "/";
        for(const filename of filenames) {
            console.log(`Uploading ${filename}`);

            const filefetch = await fetchfile(`${filefolder}${filename}`);
            const filebuffer = await filefetch.arrayBuffer();

            await repl.put(filename, new Uint8Array(filebuffer));

            callback();
        }
    }
    catch(error) {
        console.log(`Failed to upload ${filename} ${error}`);
        throw error;
    }
}

function updateprogress(progresselement, percent) {
    const percenttext = `${percent}%`;
    progresselement.style.width = percenttext;
    progresselement.textContent = percenttext;
}

async function getconfigs() {
    const configfiles = [
      'config.json',
      'firmware/config.json'
    ];

    const configs = [];
    for(const configfile of configfiles) {
        const configfetch = await fetchfile(configfile);
        const config = await configfetch.json();
        configs.push({
            configfile: configfile,
            filenames: config.filenames
        });
    }

    return configs;
}

async function install() {
    const installbutton = document.getElementById('installbutton');
    installbutton.disabled = true;
    try {
        await command.executerepl(async (repl) => {
            const progresselement = document.getElementById('installprogress');
            updateprogress(progresselement, 0);

            const configs = await getconfigs();
            const configfilecount = configs.reduce((accumulator, currentValue) =>
                accumulator + currentValue.filenames.length,
                0,
            );

            let filecount = 0;
            for(const config of configs) {
                await uploadconfig(repl, config.configfile, config.filenames, () => {
                    filecount += 1;
                    updateprogress(progresselement, Math.floor(filecount / configfilecount * 100));
                });
            }

            updateprogress(progresselement, 100);

            console.log('Rebooting');
            await repl.reboot();
        });
    } catch (error) {
        const installelement = document.getElementById('installmodal');
        const modal = bootstrap.Modal.getInstance(installelement);
        modal.hide();
        showerror(errordefs.failedinstall, undefined, error);
    } finally {
        installbutton.disabled = false;
    }
}

export { install, play }