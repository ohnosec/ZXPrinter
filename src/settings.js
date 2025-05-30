const SETTINGSKEY = "settings";

function load() {
    try {
        const settings = localStorage.getItem(SETTINGSKEY);
        return settings ? JSON.parse(settings) : {};
    } catch (error) {
        console.error("Error loading settings", error);
        return {};
    }
}

function save(settings) {
    try {
        localStorage.setItem(SETTINGSKEY, JSON.stringify(settings));
    } catch (error) {
        console.error("Error saving settings", error);
    }
}

function get(key, defaultValue = undefined) {
    const settings = load();
    return settings.hasOwnProperty(key) ? settings[key] : defaultValue;
}

function set(key, value) {
    const settings = load();
    settings[key] = value;
    save(settings);
}

function remove(key) {
    const settings = load();
    if (settings.hasOwnProperty(key)) {
        delete settings[key];
        save(settings);
    }
}

function clear() {
    try {
        localStorage.removeItem(SETTINGSKEY);
    } catch (error) {
        console.error("Error clearing all settings", error);
    }
}

export {
    get,
    set,
    remove,
    clear
}
