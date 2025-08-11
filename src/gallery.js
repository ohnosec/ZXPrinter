import { datauri } from "./datauri.js"
import { bmp_mono } from "./jsbmp.js"
import { execrequest, requests } from "./client.js"
import { Mutex, addtooltip, updatetooltip } from "./utils.js"
import { eventhandler } from "./event.js"
import * as serial from "./serial.js"
import * as command from "./command.js"

const PrintSource = Object.freeze({
    FLASH: 0,
    SD: 1
});

const PrintTarget = Object.freeze({
    PC: 0,
    ZXPRINTER: 1
});

const printcache = new Map();
printcache.set(PrintSource.FLASH, new Map());
printcache.set(PrintSource.SD, new Map());

const printselected = new Map();
printselected.set(PrintSource.FLASH, []);
printselected.set(PrintSource.SD, []);

const printcopies = [];

let printsource = PrintSource.FLASH;
let printtarget = PrintTarget.PC;

const jsPDF = window.jspdf.jsPDF;

const rendermutex = new Mutex();

class PrintItem {
    constructor(source, filename) {
        this.source = source;
        this.filename = filename;
    }
}

function arrayremove(array, callback) {
    let i = array.length;
    while(i--) {
        if (callback(array[i], i)) {
            array.splice(i, 1);
        }
    }
}

function unpack(packed) {
    // PackBits unpack
    // see https://en.wikipedia.org/wiki/PackBits
    const unpacked = [];
    for(let i = 0; i < packed.length; ) {
        let flagcounter = packed[i];
        if (flagcounter == 128) {            // ignore
        } else if (flagcounter > 128) {      // repeat
            flagcounter = 256 - flagcounter;
            for (let j = 0; j <= flagcounter; ++j) {
                unpacked.push(packed[i + 1]);
            }
            ++i;
        } else {                            // literal
            for (let j = 0; j <= flagcounter; ++j) {
                unpacked.push(packed[i + j + 1]);
            }
            i += flagcounter+1;
        }
        ++i;
    }
    return unpacked;
}

function getstorename(source = printsource) {
    return source == PrintSource.SD ? "sd" : "flash"
}

async function loadprintout(name) {
    const printout = await execrequest(requests.loadprintout, { store: getstorename(), name: name });
    const packed = printout
        .map((block) => block.match(/.{1,2}/g)
        .map((byte) => Number('0x'+byte)))
        .flat();
    return unpack(packed);
}

async function getprintout(name) {
    const cachedprintout = printcache.get(printsource).get(name);
    if (cachedprintout) return cachedprintout;
    const loadedprintout = await loadprintout(name);
    printcache.get(printsource).set(name, loadedprintout);
    return loadedprintout;
}

function getfilename(name, extension) {
    return name.replace(".packed", "").replace(/\.[^/.]+$/, "")+extension;
}

function getimagemime(img) {
    return img.src.match(/[^:]\w+\/[\w-+\d.]+(?=;|,)/)[0];
}

function getfilenamefromprt(prt) {
    return prt.id.substring(3);
}

function download(name, href) {
    const link = document.createElement("a");
    link.href = href;
    link.download = name;
    link.click();
    URL.revokeObjectURL(link.href);
}

function downloadimg(name, img) {
    const mime = getimagemime(img);
    const extension = `.${mime.replace("image/", "")}`;
    download(getfilename(name, extension), img.src);
}

function downloadtxt(name, txt) {
    const text = txt.innerText;
    const blob = new Blob([text], {type: 'text/plain'});
    download(getfilename(name, ".txt"), URL.createObjectURL(blob));
}

function downloadcap(name, bitmap) {
    const bytes = Uint8Array.from(bitmap);
    const blob = new Blob([bytes], {type: 'application/octet-stream'});
    download(getfilename(name, ".cap"), URL.createObjectURL(blob));
}

function downloadpdf(name, img) {
    const doc = new jsPDF();
    doc.addImage(img.src, x=10, y=10);
    //doc.save(getfilename(name, ".pdf"));
    const datauri = doc.output('datauristring');
    download(getfilename(name, ".pdf"), datauri);
}

function printElement(element, fontsize = null) {
    let prtelement = element.cloneNode(true);
    document.body.appendChild(prtelement);
    prtelement.classList.remove("overflow-auto")
    prtelement.classList.add("printable");
    prtelement.style.transform = "rotateY(0deg)";
    prtelement.style.padding = "25px 0px 0px 0px";
    prtelement.style.overflow = "hidden";
    if (fontsize) {
        prtelement.style.fontSize = fontsize;
    }
    window.print();
    document.body.removeChild(prtelement);
}

function putimage(name, bitmap, format, imgsrc) {
    const prtid = `prt${name}`;
    const imgid = `img${name}`;
    let img = document.getElementById(imgid);
    if (!img) {
        const prt = document.getElementById("prttemplate").cloneNode(true);
        prt.id = prtid;
        prt.removeAttribute('hidden');
        prt.classList.add("prt");

        img = prt.getElementsByClassName("prtimg")[0];
        img.id = imgid;

        const txtflip = prt.getElementsByClassName("flip-card-inner")[0];
        txtflip.dataset.flipped = false;
        txtflip.dataset.view = "image";
        const btntxtimg = prt.getElementsByClassName("prttxtimgbtn")[0];
        const btnchk = btntxtimg.getElementsByClassName("btn-check");
        const btnbtn = btntxtimg.getElementsByClassName("btn");
        for(let i=0; i<btnchk.length; i++) {
            const btn = btnchk[i];
            btn.id = btn.id+imgid;
            btn.name = btn.name+imgid;
            btn.addEventListener("click", (event) => {
                const view = event.currentTarget.value;
                if (view !== txtflip.dataset.view) {
                    txtflip.dataset.view = view;
                    const istext = view === "text";
                    const islisting = view === "listing";
                    txtflip.dataset.flipped = istext || islisting;
                    if (istext || islisting) {
                        const txt = prt.getElementsByClassName("prttxt")[0];
                        converttext(name, islisting, txt);
                    }
                }
            });
        }
        for(let i=0; i<btnbtn.length; i++) {
            const attr = btnbtn[i].getAttribute("for");
            btnbtn[i].setAttribute("for", attr+imgid);
        }

        const downbtn = prt.getElementsByClassName("prtdownbtn")[0];
        downbtn.addEventListener("click", () => {
            if (txtflip.dataset.flipped == "false") {
                if (format === "cap") {
                    downloadcap(name, bitmap);
                } else {
                    downloadimg(name, img);
                }
            } else {
                downloadtxt(name, txt);
            }
        });

        const printbtn = prt.getElementsByClassName("prtprintbtn")[0];
        printbtn.addEventListener("click", async () => {
          if (printtarget == PrintTarget.PC) {
            if (txtflip.dataset.flipped == "false") {
              printElement(img);
            } else {
              printElement(txt, "9.5px");
            }
          } else {
            const name = getfilenamefromprt(prt);
            await execrequest(requests.printprintout, { store: getstorename(), name: name });
          }
        });

        const selectchk = prt.getElementsByClassName("prtcheck")[0];
        if (printselected.get(printsource).indexOf(name) >= 0) {
            selectchk.checked = true;
        }

        const collapseable = prt.getElementsByClassName("prtcollapse")[0];
        const collapse = bootstrap.Collapse.getOrCreateInstance(collapseable, {
          toggle: false
        });
        const collapsesource = sourcegallery();
        const collapsedelement = collapsesource.getElementsByClassName('galleryprtcollapse')[0];
        if (collapsedelement.ariaExpanded === 'true') {
            collapse.show();
        } else {
            collapse.hide();
        }

        document.getElementById("prtdoc").appendChild(prt);

        addtooltip([prt]);
    }
    const prt = document.getElementById(prtid);
    const txt = prt.getElementsByClassName("prttxt")[0];
    converttext(name, false, txt);

    const paper = document.querySelector("#paper input[type='radio']:checked").value;
    const paperelement = img.parentElement;
    if (paper == "ts2040") {
        paperelement.classList.remove("zxpaper")
        paperelement.classList.add("tspaper");
    } else {
        paperelement.classList.remove("tspaper")
        paperelement.classList.add("zxpaper");
    }

    try {
        img.src = imgsrc;
    } catch (e) {
        alert("Error - possible malformed image.");
        console.log(e);
    }
}

function rendercanvas(name, bitmap, format, mimetype) {
    const scale = parseInt(document.getElementById("scale").value);

    const rowlength = 256;
    const rowbytes = rowlength/8;

    const rows = Math.ceil(bitmap.length/rowbytes)

    const canvas = document.createElement('canvas');
    const height = rows*scale;
    const width = rowlength*scale;

    canvas.height = height;
    canvas.width = width;

    const context = canvas.getContext("2d");
    const imageData = context.createImageData(width, height);
    const data = imageData.data;
    let dataindex=0;

    const paper = document.querySelector("#paper input[type='radio']:checked").value;
    const papercolor = paper == "ts2040" ? 0xff : 0xc0;
    const pushpixels = function(bits) {
        for (let bit = 7; bit >= 0; --bit) {
            const isbit = bits & (1<<bit);
            for (let i = 0; i < scale; ++i) {
                data[dataindex++] = isbit ? 0 : papercolor; // red
                data[dataindex++] = isbit ? 0 : papercolor; // green
                data[dataindex++] = isbit ? 0 : papercolor; // blue
                data[dataindex++] = 255;                    // transparency
            }
        }
    }

    for(let row = 0; row <= rowbytes*(rows-1) ; row += rowbytes) {
        for (let i = 0; i < scale; ++i) {
            for (let col = 0; col < rowbytes; ++col) {
                const pos = row + col;
                if (pos < bitmap.length)
                    pushpixels(bitmap[pos]);
                else
                    pushpixels(0);
            }
        }
    }

    context.putImageData(imageData, 0, 0);
    putimage(name, bitmap, format, canvas.toDataURL(mimetype))
}

function renderbmp(name, bitmap, format) {
    const scale = parseInt(document.getElementById("scale").value);

    const rowlength = 256;
    const rowbytes = rowlength/8;

    const rows = Math.ceil(bitmap.length/rowbytes)

    const pixels = [];

    const pushpixels = function(bits) {
        for (let bit = 7; bit >= 0; --bit) {
            const isbit = bits & (1<<bit);
            for (let i = 0; i < scale; ++i) {
                pixels.push(isbit!=0 ? true : false);
            }
        }
    }

    for(let row = rowbytes*(rows-1); row >= 0 ; row -= rowbytes) {
        for (let i = 0; i < scale; ++i) {
            for (let col = 0; col < rowbytes; ++col) {
                const pos = row + col;
                if (pos < bitmap.length)
                    pushpixels(bitmap[pos]);
                else
                    pushpixels(0);
            }
        }
    }

    const width = rowlength * scale;
    const height = rows * scale;

    const paper = document.querySelector("#paper input[type='radio']:checked").value;
    const papercolor = paper == "ts2040" ? "FFFFFF" : "C0C0C0";
    const content = bmp_mono(width, height, pixels, [papercolor, '000000']);
    putimage(name, bitmap, format, datauri("image/bmp", content));
}

let renderinprogress = 0;

async function renderall(clear = false) {
    renderinprogress++;
    const release = await rendermutex.acquire();
    const format = document.querySelector("#format input[type='radio']:checked").value;
    try {
        if (clear) {
            const docelements = document.getElementById('prtdoc').children;
            const prtelements = [].filter.call(docelements, el => el.id != 'prttemplate');
            for(const prtelement of prtelements) {
                prtelement.remove();
            }
        }
        if (renderinprogress > 1) return;
        const names = await execrequest(requests.loadprintouts, { store: getstorename() });
        names.sort();
        for(const name of names) {
            if (renderinprogress > 1) break;
            const bitmap = await getprintout(name);
            switch(format) {
                case "png":
                case "cap":
                    rendercanvas(name, bitmap, format, "image/png");
                    break;
                case "jpeg":
                    rendercanvas(name, bitmap, format, "image/jpeg");
                    break;
                default:
                    renderbmp(name, bitmap, format);
            }
        }
    } catch(error) {
        console.error('Error:', error);
    } finally {
        renderinprogress--;
        release();
        updatetooltip();
    }
}

async function converttext(name, islisting, element) {
    const convertto = document.querySelector("#convert input[type='radio']:checked").value;
    const fonttype = document.querySelector("#fonttype input[type='radio']:checked").value;
    const iszmakebas = convertto == "zmakebas";
    const istsfont = convertto == "ts";
    const issoftfont = fonttype == "soft";

    const bitmap = await getprintout(name);

    const rowlength = 256;
    const rowbytes = rowlength/8;
    const rows = bitmap.length/rowbytes;
    const lines = rows/8;

    const fontarray = fontbitmap
        .map((block) => block.match(/.{1,2}/g)
        .map((byte) => Number('0x'+byte)))
        .flat();
    const fonts = ((arr, size) =>
        Array.from({ length: Math.ceil(arr.length / size) }, (_, i) =>
            arr.slice(i * size, i * size + size)
        ))(fontarray, 8);

    const getascii = (line, column) => {
        const unknown = String.fromCharCode(0xFFFD);
        const pound = String.fromCharCode(0xA3);
        const inversedStart = 152;  // start of zx81 inversed characters in fonts
        const zx81map = [
            '"',
            pound,
            '$', ':', '?', '(', ')', '>', '<', '=', '+', '-',
            '*', '/', ';', ',', '.',
            '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
            'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J',
            'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T',
            'U', 'V', 'W', 'X', 'Y', 'Z'
        ];

        for (let font = 0; font < fonts.length; font++) {
            let bitrow;
            for (bitrow = 0; bitrow < 8; bitrow++) {
                if (bitmap[(line * rowbytes * 8) + (bitrow * rowbytes) + column] != (fonts[font][bitrow])) {
                    break;
                }
            }
            if (bitrow == 8) {
                const ascii = font + 32;
                if (ascii >= inversedStart) {
                    // zx81 inverse characters
                    const ch = zx81map[ascii - inversedStart];
                    if (iszmakebas) {
                        return ch == pound ? "\\@" : `\\${ch}`;         // TODO: doesn't this clash with the escaped label?
                    } else {
                        if (ch>='A' && ch<='Z') {
                            return String.fromCodePoint(0x1F150 + (ch.charCodeAt(0)-'A'.charCodeAt(0)));
                        }
                        if (ch=='0') {
                            return String.fromCodePoint(0x1F10C);
                        }
                        if (ch>='1' && ch<='9') {
                            return String.fromCodePoint(0x278A + (ch.charCodeAt(0)-'1'.charCodeAt(0)));
                        }
                        return String.fromCharCode(0) + ch;
                    }
                }
                switch(ascii) {
                    // timex 2068 lowercase 'm' and 'w' are wider than spectrum
                    case 0x90: return 'm';
                    case 0x91: return 'w';
                }
                if (iszmakebas) {
                    switch (ascii) {
                        // spectrum/ts2068 special characters and blocks
                        case 0x60: return "\\\\";                       // pound TODO: doesn't this clash with escaped backslash
                        case 0x7F: return "\\*";                        // copyright
                        case 0x80: return "\\  ";
                        case 0x81: return "\\ '";                       // upper right
                        case 0x82: return "\\' ";                       // upper left
                        case 0x83: return "\\''";                       // upper half
                        case 0x84: return "\\ .";                       // lower right
                        case 0x85: return "\\ :";                       // right half
                        case 0x86: return "\\'.";                       // upper left, lower right
                        case 0x87: return "\\':";                       // upper half, lower right
                        case 0x88: return "\\. ";                       // lower left
                        case 0x89: return "\\.'";                       // lower left, upper right
                        case 0x8A: return "\\: ";                       // left half
                        case 0x8B: return "\\:'";                       // upper half, lower left
                        case 0x8C: return "\\..";                       // lower half
                        case 0x8D: return "\\.:";                       // lower half, upper right
                        case 0x8E: return "\\:.";                       // left half, lower right
                        case 0x8F: return "\\::";                       // whole block

                        // zx81/ts1000/ts1500 checker board
                        case 0x92: return "\\!:";                       // whole checker
                        case 0x93: return "\\!.";                       // lower checker
                        case 0x94: return "\\!'";                       // upper checker
                        case 0x95: return "\\|:";                       // inverse whole checker
                        case 0x96: return "\\|.";                       // inverse lower checker
                        case 0x97: return "\\|'";                       // inverse upper checker

                        default: return String.fromCharCode(ascii);
                    }
                } else {
                    switch (ascii) {
                        // spectrum/ts2068 special characters and blocks
                        case 0x60: return pound;                            // pound
                        case 0x7F: return String.fromCharCode(0xA9);        // copyright
                        case 0x80: return " ";
                        case 0x81: return String.fromCharCode(0x259D);      // upper right
                        case 0x82: return String.fromCharCode(0x2598);      // upper left
                        case 0x83: return String.fromCharCode(0x2580);      // upper half
                        case 0x84: return String.fromCharCode(0x2597);      // lower right
                        case 0x85: return String.fromCharCode(0x2590);      // right half
                        case 0x86: return String.fromCharCode(0x259A);      // upper left, lower right
                        case 0x87: return String.fromCharCode(0x259C);      // upper half, lower right
                        case 0x88: return String.fromCharCode(0x2596);      // lower left
                        case 0x89: return String.fromCharCode(0x259E);      // lower left, upper right
                        case 0x8A: return String.fromCharCode(0x258C);      // left half
                        case 0x8B: return String.fromCharCode(0x259B);      // upper half, lower left
                        case 0x8C: return String.fromCharCode(0x2584);      // lower half
                        case 0x8D: return String.fromCharCode(0x259F);      // lower half, upper right
                        case 0x8E: return String.fromCharCode(0x2599);      // left half, lower right
                        case 0x8F: return String.fromCharCode(0x2588);      // whole block

                        // zx81/ts1000/ts1500 checker board
                        case 0x92: return String.fromCodePoint(0x2592);     // whole checker
                        case 0x93: return String.fromCodePoint(0x1FB8F);    // lower checker
                        case 0x94: return String.fromCodePoint(0x1FB8E);    // upper checker
                        case 0x95: return String.fromCodePoint(0x1FB90);    // inverse whole checker
                        case 0x96: return String.fromCodePoint(0x1FB91);    // inverse lower checker
                        case 0x97: return String.fromCodePoint(0x1FB92);    // inverse upper checker

                        default: return String.fromCharCode(ascii);
                    }
                }
            }
        }
        return unknown;
    }

    const htmlencode = (text) => {
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
    }

    const linebuilder = () => {
        let linetext = "";
        let inversed = false;
        function endinverse() {
            if (inversed) {
                linetext += '</span>';
                inversed = false;
            }
        }
        return {
            addnormal: (ch) => {
                endinverse();
                linetext += htmlencode(ch);
            },
            addinverse: (ch) => {
                if (!inversed) {
                    linetext += '<span class="prttxtinverse">';
                    inversed = true;
                }
                linetext += htmlencode(ch);
            },
            gettext: () => {
                endinverse();
                return linetext;
            }
        }
    }
    // get text lines
    let text = [];
    for(let line=0; line<lines; line++) {
        const builder = linebuilder();
        for(let column=0; column<rowbytes; column++) {
            let ch = getascii(line, column);
            if (ch.charCodeAt(0) == 0) { // it's a zx81 inversed character
                ch = ch.substr(1);
                builder.addinverse(ch);
            } else {
                if (istsfont) {
                    // timex 2068 lowercase 'm' and 'w' are wider than spectrum
                    if (ch == 'm') ch = String.fromCodePoint(0x1E41);
                    else if (ch == 'w') ch = String.fromCodePoint(0x1E87);
                }
                builder.addnormal(ch);
            }
        }
        text.push(builder.gettext());
    }
    // unwrap lines if it's a listing
    if (text.length>0 && islisting) {
        const listing = [];
        let line = "";
        for(const textline of text) {
            const partialline = textline.trimEnd();
            // 0-3 spaces followed by 1-4 digits followed by a space
            const matchnewline = textline.match(/^ {0,3}\d{1,4} /);
            const isnewline = matchnewline && matchnewline[0].length == 5;
            if (isnewline) {
                if (line != "") {
                    listing.push(line);
                }
                line = partialline;
            } else
                line += partialline;
        }
        if (line != "") {
            listing.push(line);
        }
        text = listing;
    }
    let html = "";
    for(let i=0; i<text.length; i++) {
        html += text[i] + "\n";
    }
    element.innerHTML = "";
    setTimeout(() => {
        const zxfontclass = "prttxtzx";
        const zxsoftfontclass = "prttxtzxsoft";
        const zmakfontclass = "prttxtzmak";
        if (iszmakebas) {
            element.classList.remove(zxfontclass);
            element.classList.remove(zxsoftfontclass);
            element.classList.add(zmakfontclass);
        } else if (issoftfont) {
            element.classList.remove(zxfontclass);
            element.classList.remove(zmakfontclass);
            element.classList.add(zxsoftfontclass);
        } else {
            element.classList.remove(zmakfontclass);
            element.classList.remove(zxsoftfontclass);
            element.classList.add(zxfontclass);
        }
        element.innerHTML = html;
    }, 100);
}

function getchecked() {
    const checked = document.querySelectorAll('.prtcheck:checked');
    return [...checked].map(check => {
        const prt = check.closest(".prt");
        const filename = getfilenamefromprt(prt);
        return new PrintItem(printsource, filename);
    });
}

function gettoolelement(source, classname) {
    const sourceelementid = source == PrintSource.FLASH ? 'galleryflash' : 'gallerysd';
    const sourceelement = document.getElementById(sourceelementid);
    return sourceelement.closest(".gallerysource").getElementsByClassName(classname)[0];
}

function refreshtools() {
    const flashpaste = gettoolelement(PrintSource.FLASH, 'gallerypaste');
    const sdpaste = gettoolelement(PrintSource.SD, 'gallerypaste');

    if (printcopies.length > 0) {
        flashpaste.classList.remove("d-none");
        sdpaste.classList.remove("d-none");
    } else {
        flashpaste.classList.add("d-none");
        sdpaste.classList.add("d-none");
    }

    const flashdelete = gettoolelement(PrintSource.FLASH, 'gallerydelete');
    const sddelete = gettoolelement(PrintSource.SD, 'gallerydelete');

    const flashcopy = gettoolelement(PrintSource.FLASH, 'gallerycopy');
    const sdcopy = gettoolelement(PrintSource.SD, 'gallerycopy');

    const flashjoin = gettoolelement(PrintSource.FLASH, 'galleryjoin');
    const sdjoin = gettoolelement(PrintSource.SD, 'galleryjoin');

    if (printselected.get(PrintSource.FLASH).length > 0) {
        flashdelete.classList.remove("d-none");
        flashcopy.classList.remove("d-none");
    } else {
        flashdelete.classList.add('d-none');
        flashcopy.classList.add('d-none');
    }

    if (printselected.get(PrintSource.SD).length > 0) {
        sddelete.classList.remove("d-none");
        sdcopy.classList.remove("d-none");
    } else {
        sddelete.classList.add('d-none');
        sdcopy.classList.add('d-none');
    }

    if (printselected.get(PrintSource.FLASH).length > 1) {
        flashjoin.classList.remove("d-none");
    } else {
        flashjoin.classList.add('d-none');
    }

    if (printselected.get(PrintSource.SD).length > 1) {
        sdjoin.classList.remove("d-none");
    } else {
        sdjoin.classList.add('d-none');
    }
}

async function galleryflash() {
    refreshtools();

    const flashelement = document.getElementById('galleryflash');
    const sdelement = document.getElementById('gallerysd');

    flashelement.classList.add("active");
    sdelement.classList.remove("active");

    sdelement.closest(".gallerysource").getElementsByClassName('gallerymethods')[0].classList.add("invisible");
    flashelement.closest(".gallerysource").getElementsByClassName('gallerymethods')[0].classList.remove("invisible");

    printsource = PrintSource.FLASH;
    await renderall(true);
}

async function gallerysd() {
    refreshtools();

    const flashelement = document.getElementById('galleryflash');
    const sdelement = document.getElementById('gallerysd');

    flashelement.classList.remove("active");
    sdelement.classList.add("active");

    flashelement.closest(".gallerysource").getElementsByClassName('gallerymethods')[0].classList.add("invisible");
    sdelement.closest(".gallerysource").getElementsByClassName('gallerymethods')[0].classList.remove("invisible");

    printsource = PrintSource.SD;
    await renderall(true);
}

function confirmdelete() {
    confirmdeletemodal.show();
}

async function deleteprintout() {
    for (const print of getchecked()) {
        await execrequest(requests.deleteprintout, { store: getstorename(), name: print.filename });
        arrayremove(printselected.get(printsource), filename => filename == print.filename);
        arrayremove(printcopies, c => c.source == printsource && c.filename == print.filename);
    }
    confirmdeletemodal.hide();
    refreshtools();
    await renderall(true);
}

async function joinprintout() {
    const storename = getstorename();
    const filenames = getchecked().map(p => p.filename);

    await execrequest(requests.joinprintout, { names: filenames, fromstore: storename, tostore: storename });

    await renderall(true);
}

function copyprintout(element) {
    printcopies.length = 0;
    for (const print of getchecked()) {
        printcopies.push(print);
    }

    refreshtools();

    const tooltip = bootstrap.Tooltip.getOrCreateInstance(element);
    tooltip.setContent({ '.tooltip-inner': 'Copied' });
    tooltip.show();
}

async function pasteprintout() {
    for(const printcopy of printcopies) {
        await execrequest(requests.copyprintout, { name: printcopy.filename, fromstore: getstorename(printcopy.source), tostore: getstorename() });
    }
    await renderall(true);
}

function sourcegallery() {
    const flashelement = document.getElementById('galleryflash');
    const sdelement = document.getElementById('gallerysd');

    if (flashelement.classList.contains("active")) {
        return flashelement.closest(".gallerysource");
    }
    if (sdelement.classList.contains("active")) {
        return sdelement.closest(".gallerysource");
    }
    return undefined;
}

function selectprintout() {
    printselected.set(printsource, getchecked().map(selected => selected.filename));
    refreshtools();
}

async function gallerycapture() {
    const captureelement = document.getElementById('gallerycapture');
    await execrequest(requests.setcapture, { state: captureelement.checked ? "on" : "off"});
}

function galleryexpandcollapse(expanded) {
    const selectallelements = document.getElementsByClassName("galleryselectall");
    for (const selectallelement of [...selectallelements]) {
        if (expanded) {
            selectallelement.classList.remove("d-none");
        } else {
            selectallelement.classList.add("d-none");
        }
    }
    const collapseelements = document.getElementsByClassName("prtcollapse");
    for (const collapseelement of [...collapseelements]) {
        if (collapseelement.parentNode.id == "prttemplate") continue;
        const collapse = bootstrap.Collapse.getOrCreateInstance(collapseelement, {
            toggle: false
        });
        if (expanded) {
            collapse.show();
        } else {
            collapse.hide();
        }
    }
}

function galleryselectall() {
    const checks = [...document.querySelectorAll('.prtcheck')].filter(chk => !chk.closest("#prttemplate"));
    const isallselected = checks.every(chk => chk.checked);
    for (const check of checks) {
        check.checked = !isallselected;
    }
    selectprintout();
}

function galleryadvanced(element) {
    const collapseelement = element.parentElement;
    const expanded = collapseelement.ariaExpanded !== 'true';
    collapseelement.ariaExpanded = expanded;
    galleryexpandcollapse(expanded);
}

function changegallerytarget() {
    const target = document.querySelector("#gallerytarget input[type='radio']:checked").value;

    printtarget = target.toLowerCase() == 'pc' ? PrintTarget.PC : PrintTarget.ZXPRINTER;
}

// NOTE: keep the second value the same as those in prttxtzx and prttxtzxsoft
// AND   keep the array lengths the same
const normalsizes   = [7.4, 14.3, 21.3, 28.3, 35.3, 42.3, 49.2, 56.2];
const softsizes     = [8.4, 16.3, 24.4, 32.4, 40.4, 48.4, 56.2, 64.2];
const lineheights   = [8,   15.9, 24,   32,   40,   48,   56,   64  ];

async function changescale() {
    const fonttype = document.querySelector("#fonttype input[type='radio']:checked").value;
    const issoftfont = fonttype == "soft";

    await renderall();

    const scale = parseInt(document.getElementById("scale").value);

    const scaleindex = scale - 1;
    if (scaleindex < 0 || scaleindex >= normalsizes.length) scaleindex = 0;

    const fontsize = issoftfont ? softsizes[scaleindex] : normalsizes[scaleindex];
    const lineheight = lineheights[scaleindex];

    for (const txt of document.getElementsByClassName("prttxt")) {
        txt.style.fontSize = `${fontsize}px`;
        txt.style.lineHeight = `${lineheight}px`;
    };
}

async function changeconvert() {
    const convertto = document.querySelector("#convert input[type='radio']:checked").value;
    const iszmakebas = convertto == "zmakebas";

    const fontstyle = document.getElementById("fontstyle");
    if (iszmakebas) {
        fontstyle.classList.add("d-none");
    } else {
        fontstyle.classList.remove("d-none");
    }

    await changescale();
}

function handlesd(ismounted) {
    const sdsource = document.getElementById("gallerysdsource");
    printcache.set(PrintSource.SD, new Map());
    printselected.set(PrintSource.SD, []);
    if (ismounted) {
        sdsource.classList.remove("d-none");
        if (printsource == PrintSource.SD) {
            renderall(true);
        }
    } else {
        arrayremove(printcopies, c => c.source == PrintSource.SD);
        sdsource.classList.add("d-none");
        if (printsource == PrintSource.SD) {
            const button = document.getElementById("galleryflashbutton");
            button.focus();
            button.click();
        }
    }
}

async function sdavailable() {
    try {
        const response = await command.execute("about", [], 200);
        return response.sdcard;
    } catch {
        return false;
    }
}

serial.connecthandler.add(async () => {
    handlesd(await sdavailable());
});

eventhandler.add(async (event) => {
    switch(event.type) {
        case "capture":
            if (printsource == PrintSource.FLASH) {
                renderall(true);
            }
            break;
        case "sdcard":
            handlesd(event.data);
            break;
    }
});

const confirmdeleteeelement = document.getElementById("deletemodal");
const confirmdeletemodal = bootstrap.Modal.getOrCreateInstance(confirmdeleteeelement, {
  backdrop: 'static'
});

document.getElementById("scale").addEventListener("change", changescale);
document.getElementById("format").addEventListener("change", renderall);
document.getElementById("paper").addEventListener("change", renderall);
document.getElementById("convert").addEventListener("change", changeconvert);
document.getElementById("fonttype").addEventListener("change", changeconvert);
document.getElementById("gallerytarget").addEventListener("change", changegallerytarget);

export {
    renderall,
    galleryflash, gallerysd,
    deleteprintout, selectprintout, joinprintout, copyprintout, pasteprintout, confirmdelete,
    gallerycapture, galleryadvanced, galleryselectall, changegallerytarget
}