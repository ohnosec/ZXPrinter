export * from "./log.js"
export * from "./gallery.js"
export * from "./network.js"
export * from "./install.js"
export * from "./cloud.js"
export * from "./printer.js"

import { isdropdown, hidedropdowns, addtooltip, updatetooltip } from "./utils.js"
import * as settings from "./settings.js"

const TOOLTIPSTATENAME = "showtooltip";

// fix "Blocked aria-hidden on an element...""
document.addEventListener("hide.bs.modal", (event) => {
    if (document.activeElement) {
        document.activeElement.blur();
    }
});

document.body.addEventListener("click", e => {
    if (!isdropdown(e.target)) {
        hidedropdowns();
    }
});

const tooltipstate = settings.get(TOOLTIPSTATENAME, true);
const tooltipenable = document.getElementById("tooltipenable");
tooltipenable.checked = tooltipstate;
addtooltip();
updatetooltip();

function showtooltip(checkbox) {
    updatetooltip();
    settings.set(TOOLTIPSTATENAME, checkbox.checked);
}

function setupmenu(element) {
    const menus = element.querySelectorAll(".menu");
    const menucontents = element.querySelectorAll(".menucontent");

    for (const menu of menus) {
        menu.addEventListener("click", (event) => {
            event.preventDefault();
            const targetId = menu.dataset.target;

            for (const hidemenu of menus) {
                hidemenu.classList.remove("active");
            }
            menu.classList.add("active");

            for (const content of menucontents) {
                if (content.classList.contains(targetId)) {
                    content.classList.add("active");
                } else {
                    content.classList.remove("active");
                }
            };
            return false;
        });
    };
}

setupmenu(document.getElementById("maincontainer"));

function sidebartoggle() {
    const menu = document.getElementById("menucontainer");
    menu.ariaExpanded = menu.ariaExpanded !== "true";
}

export { sidebartoggle, showtooltip }