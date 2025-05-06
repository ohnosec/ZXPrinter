export * from "./log.js"
export * from "./gallery.js"
export * from "./network.js"
export * from "./install.js"
export * from "./cloud.js"
export * from "./printer.js"

import { isdropdown, hidedropdowns } from "./utils.js"

// fix "Blocked aria-hidden on an element...""
document.addEventListener('hide.bs.modal', (event) => {
    if (document.activeElement) {
        document.activeElement.blur();
    }
});

document.body.addEventListener("click", e => {
    if (!isdropdown(e.target)) {
        hidedropdowns();
    }
});

const tooltipelements = document.querySelectorAll('[data-bs-toggle="tooltip"]');
for(const tooltipelement of tooltipelements) {
    const tooltip = bootstrap.Tooltip.getOrCreateInstance(tooltipelement, {
        placement: 'top',
        trigger: 'hover',
        //delay: { 'show':0, 'hide':150 }
    });
    const title = tooltipelement.dataset.bsTitle;
    tooltipelement.addEventListener("hidden.bs.tooltip", () => {
        tooltip.setContent({ '.tooltip-inner': title });
    });
}

function showtooltip(checkbox) {
    const tooltipelements = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    const tooltipforeach = fn => {
        for(const tooltipelement of tooltipelements) {
            const tooltip = bootstrap.Tooltip.getOrCreateInstance(tooltipelement);
            fn(tooltip);
        }
    };
    if (checkbox.checked) {
        tooltipforeach(tooltip => tooltip.enable());
    } else {
        tooltipforeach(tooltip => tooltip.disable());
    }
}

function setupMenu(element) {
    const menus = element.querySelectorAll(".menu")
    const menuContents = element.querySelectorAll(".menucontent")

    menus.forEach(menuitem => {
        menuitem.addEventListener("click", (ev) => {
            ev.preventDefault()
            const targetId = menuitem.getAttribute("data-target")

            menus.forEach(t => t.classList.remove("active"))
            menuitem.classList.add("active")

            menuContents.forEach(content => {
                if (content.id === targetId) {
                    content.classList.add("active")
                } else {
                    content.classList.remove("active")
                }
            })
            return false
        })
    })
}

setupMenu(document.getElementById("menucontainer"));

function sidebartoggle() {
    const menu = document.getElementById("menucontainer");
    menu.ariaExpanded = menu.ariaExpanded !== 'true';
}

async function test() {
    // placeholder
}

export { sidebartoggle, showtooltip, test }