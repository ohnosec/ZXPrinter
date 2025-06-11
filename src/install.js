import * as command from "./command.js"
import * as network from "./network.js"

import { showerror, errordefs, ShowError } from "./utils.js"

const DISTROFILENAME = "files.json";

async function fetchfile(url) {
    const response = await fetch(url);
    if (!response.ok) {
        throw new ShowError(`Could not get file '${url}' (${response.status})`)
    }
    return response;
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
    } catch(error) {
        console.log(`Failed to upload ${sourcefile} ${error}`);
        throw error;
    }
}

function updateprogress(progresselement, percent) {
    const percenttext = `${percent}%`;
    progresselement.style.width = percenttext;
    progresselement.textContent = percenttext;
}

async function getdistro() {
    const distrofetch = await fetchfile(DISTROFILENAME);
    const distro = await distrofetch.json();
    return distro;
}

async function getdistrorepl(repl) {
    const distrojson = await repl.gettext(DISTROFILENAME);
    const distro = JSON.parse(distrojson);
    return distro;
}

async function install() {
    const initialcursor = document.body.style.cursor;
    document.body.style.cursor = "wait";
    const installmodal = bootstrap.Modal.getInstance(document.getElementById("installmodal"));
    const installbutton = document.getElementById("installbutton");
    const installclosebutton = document.getElementById("installclosebutton");
    const installdismissbutton = document.getElementById("installdismissbutton");
    const isquickcheckbox = document.getElementById("quickinstall");
    const iscleancheckbox = document.getElementById("cleaninstall");
    installbutton.disabled = true;
    installclosebutton.disabled = true;
    installdismissbutton.disabled = true;
    isquickcheckbox.disabled = true;
    iscleancheckbox.disabled = true;
    const isquick = isquickcheckbox.checked;
    const isclean = iscleancheckbox.checked;
    try {
        await command.executerepl(async (repl) => {
            const progresselement = document.getElementById("installprogress");
            updateprogress(progresselement, 0);

            const distrofiles = await getdistro();
            const installfiles = [...distrofiles];

            if (isquick && !isclean) {
                const existingfiles = await getdistrorepl(repl);
                if (existingfiles !== null) {
                    installfiles.length = 0;
                    for (let i=0; i<distrofiles.length; i++) { // for...of blows up chrome!
                        const distrofile = distrofiles[i];
                        const existingfile = existingfiles.find((f) => f.source === distrofile.source);
                        if (!existingfile
                            || existingfile.checksum != distrofile.checksum
                            || distrofile.source == DISTROFILENAME)
                        {
                            installfiles.push(distrofile);
                        }
                    }
                    // only the distro file so don't install anything
                    if (installfiles.length === 1) {
                        installfiles.length = 0;
                    }
                }
            }

            if (installfiles.length > 0) {
                if (isclean) {
                    await repl.removedir("", ["printout", "sd", "settings.json"])
                }

                const todo = installfiles.length+1;
                let done = 0;
                await uploadfiles(repl, installfiles, () => {
                    done += 1;
                    updateprogress(progresselement, Math.floor(done / todo * 100));
                });
            }

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
        installclosebutton.disabled = false;
        installdismissbutton.disabled = false;
        isquickcheckbox.disabled = false;
        iscleancheckbox.disabled = false;
        changequick();
        document.body.style.cursor = initialcursor;
    }
}

function changequick() {
    const isquick = document.getElementById("quickinstall").checked;
    const clean = document.getElementById("cleaninstall");

    clean.disabled = isquick;
    if (isquick) {
        clean.checked = false;
    }
}

const installelement = document.getElementById("installmodal")
installelement.addEventListener("show.bs.modal", () => {
    const progresselement = document.getElementById("installprogress");
    updateprogress(progresselement, 0);
});

document.getElementById("quickinstall").addEventListener("change", changequick);

export { install }