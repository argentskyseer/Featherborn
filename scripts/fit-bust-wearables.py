#!/usr/bin/env python3
"""Generate bust-fitted copies of vanilla clothing/armor shapes for the harpy.

Each fitted shape is the vanilla shape plus one wedge element on UpperTorso that copies
the harpy bust (shapes/body/bust/bust.json), padded so it sits over the body (and armor
over clothing). The wedge samples the garment's own chest texture, so every item variant
that reuses the shape keeps its colours. The wedge is named "Bust-clothes" / "Bust-armor";
the harpy "bust" skin part hides those names when set to "none".

Usage: python3 scripts/fit-bust-wearables.py   (run from the mod root)
Finds every vanilla seraph/villager shape with a chest-covering UpperTorso piece, writes the
fitted copies to assets/featherborn/shapes/wearable/harpy/ (wiped first) and rewrites the
WearableModelReplacersByShape block in harpy-player.json.
"""
import copy, json, math, os, sys

sys.path.insert(0, os.path.dirname(__file__))
from vsjson import load

VANILLA = '/opt/vintagestory/assets/survival/shapes/'
SEARCH = ['entity/humanoid/seraph', 'entity/humanoid/villageraccessories']
OUT = 'assets/featherborn/shapes/wearable/harpy/'
BUST = 'assets/featherborn/shapes/body/bust/bust.json'
CONFIG = 'assets/featherborn/config/customplayermodels/harpy-player.json'

# wedge padding by clothing layer, so layers stack body < shirt < coat < shoulder < armor;
# the garment's own offset from the torso is added on top
LAYER_PAD = {'upperbody': 0.10, 'upperbodyover': 0.18, 'shoulder': 0.26, 'armor': 0.40,
             'emblem': 0.22, 'neck': 0.22}   # pins/necklaces only get lifted, no wedge

def bust_element():
    return next(e for e in load(BUST)['elements'] if e['name'] == 'Bust')


def sub_uv(face, lo_u, hi_u, lo_v, hi_v):
    """Sub-rectangle of a face's uv, fractions measured from the face's uv origin."""
    u0, v0, u1, v1 = face['uv']
    return [round(u0 + (u1 - u0) * lo_u, 3), round(v0 + (v1 - v0) * lo_v, 3),
            round(u0 + (u1 - u0) * hi_u, 3), round(v0 + (v1 - v0) * hi_v, 3)]


def fitted_wedge(bust, torso, kind, pad):
    w = copy.deepcopy(bust)
    w['name'] = 'Bust-' + kind
    w['stepParentName'] = 'UpperTorso'
    w['from'] = [round(w['from'][0] - pad, 3), round(w['from'][1] - pad, 3), round(w['from'][2] - pad, 3)]
    w['to'] = [w['to'][0], round(w['to'][1] + pad, 3), round(w['to'][2] + pad, 3)]
    tf, tt = torso['from'], torso['to']
    zl, zh = tt[2] - tf[2], tt[1] - tf[1]
    fz0 = max(0.0, (w['from'][2] - tf[2]) / zl); fz1 = min(1.0, (w['to'][2] - tf[2]) / zl)
    fy_top = max(0.0, (tt[1] - w['to'][1]) / zh); fy_bot = min(1.0, (tt[1] - w['from'][1]) / zh)
    depth = min(1.0, (w['to'][0] - w['from'][0]) / max(zl, 0.01))
    F = torso['faces']

    def face(src, *frac):
        src = src if src in F else 'west'
        f = {k: v for k, v in F[src].items() if k in ('texture', 'rotation')}
        f['uv'] = sub_uv(F[src], *frac)
        return f

    front = face('west', fz0, fz1, fy_top, fy_bot)          # garment chest under the wedge
    w['faces'] = {
        'west': front,
        'east': dict(front),
        'north': face('north', 0, depth, fy_top, fy_bot),
        'south': face('south', 1 - depth, 1, fy_top, fy_bot),
        'up': face('west', fz0, fz1, 0, min(1.0, depth)),
        'down': face('west', fz0, fz1, max(0.0, fy_bot - depth), fy_bot),
    }
    # child pieces of the bust (underside bevels etc.): same pad, garment's lower-chest texture
    under = face('west', fz0, fz1, max(0.0, fy_bot - 0.25), fy_bot)
    sides = {'north': face('north', 0, depth, max(0.0, fy_bot - 0.25), fy_bot),
             'south': face('south', 1 - depth, 1, max(0.0, fy_bot - 0.25), fy_bot)}

    def pad_child(c):
        # children hang off the wedge's own corner, which already moved out with the padding;
        # keep their size and only widen them to the padded width
        c['name'] += '-Bust-' + kind
        c['to'] = [c['to'][0], c['to'][1], round(c['to'][2] + 2 * pad, 3)]
        c['faces'] = {k: dict(sides.get(k, under)) for k in ('north', 'east', 'south', 'west', 'up', 'down')}
        for g in c.get('children', []):
            pad_child(g)

    for c in w.get('children', []):
        pad_child(c)
    return w


FLAT = '-flatchest'   # suffix for original chest-front pieces, hidden when the bust is on


def rot_z(p, origin, deg):
    a = math.radians(deg)
    x, y = p[0] - origin[0], p[1] - origin[1]
    return origin[0] + x * math.cos(a) - y * math.sin(a), origin[1] + x * math.sin(a) + y * math.cos(a)


def bust_front(bust):
    """Bottom and top corners of the bust's front face, in UpperTorso space."""
    o, r = bust['rotationOrigin'], bust.get('rotationZ', 0)
    x0, y0, y1 = bust['from'][0], bust['from'][1], bust['to'][1]
    return rot_z((x0, y0), o, r), rot_z((x0, y1), o, r)


def front_x_at(bust, y):
    (bx, by), (tx, ty) = bust_front(bust)
    t = min(1.0, max(0.0, (y - by) / (ty - by)))
    return bx + (tx - bx) * t


def rename_tree(e, suffix):
    e['name'] += suffix
    for c in e.get('children', []):
        rename_tree(c, suffix)


def lift_front_pieces(shape, bust, kind, pad):
    """Copy thin pieces lying on the chest front onto the bust surface.

    The copy (suffix Bust-<kind>) shows with the bust on; the original (suffix -flatchest)
    shows with it off. Unrotated pieces get the bust's own tilt; already-rotated pieces are
    pushed forward to the bust surface at their height. Returns how many pieces were lifted.
    """
    (_, y_lo), (_, y_hi) = bust_front(bust)
    z_lo, z_hi = bust['from'][2], bust['to'][2]
    lifted = 0

    def visit(siblings, off, parent_rotated):
        nonlocal lifted
        for e in list(siblings):
            f, t = e['from'], e['to']
            F = [f[0] + off[0], f[1] + off[1], f[2] + off[2]]
            T = [t[0] + off[0], t[1] + off[1], t[2] + off[2]]
            yc = (F[1] + T[1]) / 2
            rotated = parent_rotated or any(e.get('rotation' + a, 0) for a in 'XYZ')
            on_front = ('faces' in e and F[0] <= 0.1 and T[0] - F[0] <= 1.2
                        and y_lo - 0.2 <= yc <= y_hi and T[2] > z_lo and F[2] < z_hi)
            if on_front:
                lifted_copy = copy.deepcopy(e)
                rename_tree(lifted_copy, '-Bust-' + kind)
                rename_tree(e, FLAT)
                if not rotated:
                    # sit on the bust plane: push to the bust's (pre-tilt) front, then tilt with it
                    dx = bust['from'][0] - pad - 0.01   # torso front (x=0) -> wedge front
                    lifted_copy['from'] = [round(f[0] + dx, 3), f[1], f[2]]
                    lifted_copy['to'] = [round(t[0] + dx, 3), t[1], t[2]]
                    o = bust['rotationOrigin']
                    lifted_copy['rotationOrigin'] = [round(o[0] - off[0], 3), round(o[1] - off[1], 3), round(o[2] - off[2], 3)]
                    lifted_copy['rotationZ'] = bust.get('rotationZ', 0)
                else:
                    dx = front_x_at(bust, yc) - pad - 0.01
                    lifted_copy['from'] = [round(f[0] + dx, 3), f[1], f[2]]
                    lifted_copy['to'] = [round(t[0] + dx, 3), t[1], t[2]]
                    if 'rotationOrigin' in lifted_copy:
                        ro = lifted_copy['rotationOrigin']
                        lifted_copy['rotationOrigin'] = [round(ro[0] + dx, 3), ro[1], ro[2]]
                siblings.insert(siblings.index(e) + 1, lifted_copy)
                lifted += 1
                continue   # the copy carries its children along
            visit(e.get('children', []), F, rotated)

    for top in shape['elements']:
        if top.get('stepParentName') == 'UpperTorso' and not top['name'].startswith('Bust-'):
            rot = any(top.get('rotation' + a, 0) for a in 'XYZ')
            visit(top.get('children', []), top['from'], rot)
    return lifted


def covers_chest(e):
    """Garment piece on UpperTorso that covers the chest front (not a pin or necklace)."""
    f, t = e['from'], e['to']
    return e.get('stepParentName') == 'UpperTorso' and 'faces' in e and 'west' in e['faces'] \
        and f[0] <= 0.05 and t[2] - f[2] >= 5 and t[1] - f[1] >= 3


def layer_of(rel):
    parts = rel.split('/')
    if 'armor' in parts:
        return 'armor'
    return next((p for p in parts if p in LAYER_PAD), None)


def item_shape_patterns():
    """Shape paths referenced by item types (what a player can actually wear).

    Villager NPC outfits live in config/, not itemtypes/, and PML only swaps player clothing,
    so shapes only NPCs use are skipped. {variant} placeholders match any path segment.
    """
    import glob, re
    pats = set()
    for path in glob.glob(os.path.dirname(VANILLA.rstrip('/')) + '/../*/itemtypes/**/*.json', recursive=True):
        text = open(path, encoding='utf-8-sig').read()
        for ref in re.findall(r'"(?:game:)?(entity/humanoid/[^"]+)"', text):
            pats.add('^' + re.sub(r'\\\{[^}]*\\\}', '[^/]+', re.escape(ref)) + '$')
    return [re.compile(p) for p in pats]


def discover():
    import glob
    worn = item_shape_patterns()
    found = []
    for root in SEARCH:
        for path in sorted(glob.glob(VANILLA + root + '/**/*.json', recursive=True)):
            rel = path[len(VANILLA):-5]
            layer = layer_of(rel)
            if not layer or not any(p.match(rel) for p in worn):
                continue
            shape = load(path)
            if not any(e.get('stepParentName') == 'UpperTorso' for e in shape.get('elements', [])):
                continue
            torso = next((e for e in shape.get('elements', []) if covers_chest(e)), None)
            found.append((rel, layer, shape, torso))
    return found


def write_config(replacers):
    """Replace the generated WearableModelReplacersByShape block in the harpy config."""
    s = open(CONFIG).read()
    start = s.index('"WearableModelReplacersByShape": {')
    end = s.index('}', start) + 1
    ind = s[s.rindex('\n', 0, start) + 1:start]
    body = ',\n'.join(f'{ind}  "{k}": "{v}"' for k, v in sorted(replacers.items()))
    s = s[:start] + '"WearableModelReplacersByShape": {\n' + body + '\n' + ind + '}' + s[end:]
    open(CONFIG, 'w').write(s)


def main():
    import shutil
    bust = bust_element()
    replacers = {}
    shutil.rmtree(OUT, ignore_errors=True)
    for rel, layer, shape, torso in discover():
        kind = 'armor' if layer == 'armor' else 'clothes'
        pad = LAYER_PAD[layer] + (max(0.0, -torso['from'][0]) if torso else 0.0)
        lifted = lift_front_pieces(shape, bust, kind, pad)
        if torso:
            shape['elements'].append(fitted_wedge(bust, torso, kind, pad))
        elif not lifted:
            continue   # nothing on the chest front (pins, necklaces are handled separately)
        # vanilla texture paths have no domain; inside a featherborn file they'd resolve to featherborn:
        shape['textures'] = {k: (v if ':' in v else 'game:' + v) for k, v in shape.get('textures', {}).items()}
        out = OUT + rel.split('humanoid/', 1)[1] + '.json'
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, 'w') as fh:
            json.dump(shape, fh, separators=(',', ':'))   # generated; open in the editor to inspect
        replacers['game:' + rel] = 'featherborn:' + out.split('shapes/', 1)[1][:-5]
    write_config(replacers)
    print(f'{len(replacers)} fitted shapes written to {OUT}, config updated')


if __name__ == '__main__':
    main()
