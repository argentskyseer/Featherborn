// Builds the release zip from a staged copy: only modinfo, icon, license and assets/ go in,
// and shape JSON is minified (about 40% smaller). Your editable files are never touched.
const fs = require('fs-extra');
const path = require('path');
const { zipModFolder } = require('vs-mod-packager/packager/index');

const root = path.resolve(__dirname, '..');
const stage = path.join(root, 'dist', 'stage');

async function minifyShapes(dir) {
    let saved = 0, kept = 0;
    for (const entry of await fs.readdir(dir, { withFileTypes: true })) {
        const p = path.join(dir, entry.name);
        if (entry.isDirectory()) { const r = await minifyShapes(p); saved += r.saved; kept += r.kept; continue; }
        if (!entry.name.endsWith('.json')) continue;
        const text = await fs.readFile(p, 'utf8');
        try {
            const min = JSON.stringify(JSON.parse(text));
            await fs.writeFile(p, min);
            saved += text.length - min.length;
        } catch {
            kept++;                                   // not strict JSON (comments etc.): ship as-is, the game still reads it
        }
    }
    return { saved, kept };
}

(async () => {
    await fs.remove(stage);
    for (const item of ['modinfo.json', 'modicon.png', 'LICENSE', 'assets']) {
        if (await fs.pathExists(path.join(root, item))) await fs.copy(path.join(root, item), path.join(stage, item));
    }
    const { saved, kept } = await minifyShapes(path.join(stage, 'assets', 'featherborn', 'shapes'));
    console.log(`Minified shapes: saved ${(saved / 1e6).toFixed(1)} MB${kept ? `, ${kept} non-strict file(s) copied as-is` : ''}`);
    const zip = await zipModFolder(stage);
    const out = path.join(root, 'dist', path.basename(zip));
    await fs.move(zip, out, { overwrite: true });
    await fs.remove(stage);
    console.log(`Mod packaged at: ${out}`);
})().catch(err => { console.error('Error:', err.message); process.exit(1); });
