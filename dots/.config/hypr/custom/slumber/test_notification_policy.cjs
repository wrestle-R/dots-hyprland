const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const context = {};
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(__dirname, 'NotificationPolicy.js'), 'utf8').replace(/^\.pragma library\s*/, ''), context);
const enabled = ['t3code', 'codex', 'vscode'];
for (const name of ['T3 Code', 'T3 Code (Beta)', 't3code', 'com.t3tools.T3Code', 'Codex', 'Multi Codex', 'multi-codex-desktop', 'Visual Studio Code', 'VS Code', 'Code', 'com.microsoft.VSCode', '  VISUAL   STUDIO CODE ']) {
    assert.equal(context.allows(name, enabled, []), true, name);
}
for (const name of ['Instagram', 'Zen', 'KDE Connect', 'Local System Message Service', 'Wallpaper switcher', 'Messages', 'Fake T3 Code', 'Code Helper', 'electron', '', null]) {
    assert.equal(context.allows(name, enabled, []), false, String(name));
}
assert.equal(context.allows('Code', ['codex', 't3code'], []), false);
assert.equal(context.allows('Codex', [], []), false);
assert.equal(context.allows('Code', enabled, [' code ']), false);
console.log('PASS: approved app aliases, unknown/partial-name denial, disabled groups and legacy hiding');
