.pragma library

// Exact app-name/desktop aliases only. Never use substring matching here.
function normalized(name) {
    return String(name || "").trim().toLowerCase().replace(/\s+/g, " ");
}

function groupFor(name) {
    const value = normalized(name);
    const groups = {
        "t3code": ["t3 code", "t3 code (beta)", "t3code", "com.t3tools.t3code"],
        "codex": ["codex", "multi codex", "multi-codex-desktop"],
        "vscode": ["visual studio code", "vs code", "code", "com.microsoft.vscode"]
    };
    for (const group of Object.keys(groups)) {
        if (groups[group].indexOf(value) >= 0) return group;
    }
    return "";
}

function allows(name, enabled, hidden) {
    const group = groupFor(name);
    return group !== "" && enabled.indexOf(group) >= 0
        && !hidden.some(value => normalized(value) === normalized(name));
}
