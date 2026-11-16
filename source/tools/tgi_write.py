"""Writing Aerofly .tgi scenes (text geometry for the aircraft converter) from Blender objects.

Vertex format pos3/normal3/uv2, one patch per material, identical vertices merged; materials list texture
channels <material>_<suffix> (normal, color, specular, reflection, ambient - glass has no ambient).
"""
import numpy as np


def object_arrays(o):
    """Triangulated per-corner arrays (positions, normals, uvs, material index per triangle)."""
    me = o.data
    me.calc_loop_triangles()
    tris = me.loop_triangles
    nt = len(tris)
    loops = np.empty(nt * 3, dtype=np.int32)
    tris.foreach_get('loops', loops)
    mat_idx = np.empty(nt, dtype=np.int32)
    tris.foreach_get('material_index', mat_idx)
    vidx = np.empty(len(me.loops), dtype=np.int32)
    me.loops.foreach_get('vertex_index', vidx)
    co = np.empty(len(me.vertices) * 3, dtype=np.float64)
    me.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3)
    mw = np.array(o.matrix_world)
    co = co @ mw[:3, :3].T + mw[:3, 3]
    nrm = np.empty(len(me.loops) * 3, dtype=np.float64)
    me.corner_normals.foreach_get('vector', nrm)
    nrm = nrm.reshape(-1, 3) @ np.linalg.inv(mw[:3, :3])
    nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-12)
    if me.uv_layers:
        uv = np.empty(len(me.loops) * 2, dtype=np.float64)
        me.uv_layers[0].data.foreach_get('uv', uv)
        uv = uv.reshape(-1, 2)
        uv[:, 1] = 1.0 - uv[:, 1]  # back to top-left origin, as in the source DCS data
    else:
        uv = np.zeros((len(me.loops), 2))
    pos, n, t = co[vidx[loops]], nrm[loops], uv[loops]
    # winding follows the source vertex normals (the DCS normals are right for mirrored objects too, while the
    # winding of a mirrored object may or may not have been authored for its negative-determinant transform)
    p3 = pos.reshape(-1, 3, 3)
    fn = np.cross(p3[:, 1] - p3[:, 0], p3[:, 2] - p3[:, 0])
    flip = np.einsum('ij,ij->i', fn, n.reshape(-1, 3, 3).sum(1)) < 0
    if flip.any():
        order = np.arange(len(loops)).reshape(-1, 3)
        order[flip] = order[flip][:, [0, 2, 1]]
        order = order.reshape(-1)
        pos, n, t = pos[order], n[order], t[order]
    return pos, n, t, mat_idx


def fmt_floats(a):
    return ' '.join('%.6g' % x for x in a)


def write_patch(fh, mat_id, pos, nrm, uv, weld=4, lift=2e-4, split_hard=False):
    verts = np.hstack([pos, nrm, uv]).round(6)
    uniq, inverse = np.unique(verts, axis=0, return_inverse=True)
    inverse = inverse.reshape(-1)
    # Clean-up for the converter's triangle stripping, which works on vertices welded by POSITION (it reports ~3x
    # fewer vertices than written) and drops whole strips where it fails ("stripping problem": see-through F-22
    # intakes, nozzles, fin edges). DCS models list some surfaces twice with ~1e-5 m noise and let overlapping
    # panels share edges: drop triangles whose welded corner set repeats (any winding: Aerofly draws both faces)
    # or collapses (same side only), and lift triangles on edges shared by >2 welded triangles 0.2 mm along their
    # normal so they are not welded to their neighbours (invisible; two-sided sheets end up 0.4 mm thick).
    # Fine detail (cockpit: button bevels, knob flutes under 0.1 mm) passes weld=5 / lift=2e-5: at 0.1 mm the cockpit
    # lost 2300 triangles and 60000 more stood 0.2 mm off their neighbours - black wedges at button corners
    tri = inverse.reshape(-1, 3)
    _, wid = np.unique(uniq[:, :3].round(weld), axis=0, return_inverse=True)
    wid = wid.reshape(-1)
    wt = wid[tri]
    # same welded corners AND the same side (vertex normals): a real two-sided sheet (opposite normals, each side
    # lit by its own copy) keeps both copies; they are separated by the lift below (their edges count >2)
    side = np.sign(np.round(uniq[tri, 3:6].sum(1), 1))
    key = np.hstack([np.sort(wt, axis=1), side])
    _, first = np.unique(key, axis=0, return_index=True)
    keep = np.zeros(len(tri), bool)
    keep[first] = True
    keep &= (wt[:, 0] != wt[:, 1]) & (wt[:, 1] != wt[:, 2]) & (wt[:, 0] != wt[:, 2])
    tri, wt = tri[keep], wt[keep]
    e = np.sort(np.stack([wt[:, [0, 1]], wt[:, [1, 2]], wt[:, [2, 0]]], 1).reshape(-1, 2), axis=1)
    _, einv, ecount = np.unique(e, axis=0, return_inverse=True, return_counts=True)
    bad = (ecount[einv.reshape(-1)] > 2).reshape(-1, 3).any(1)
    _, kinv, kcount = np.unique(np.sort(wt, axis=1), axis=0, return_inverse=True, return_counts=True)
    bad |= kcount[kinv.reshape(-1)] > 1       # isolated two-sided pairs (same corners, opposite sides)
    if bad.any():
        fn = uniq[tri[bad], 3:6].sum(1)          # along the vertex normals: towards the side the copy shows
        fn /= np.linalg.norm(fn, axis=1, keepdims=True) + 1e-12
        lifted = uniq[tri[bad].reshape(-1)].copy()
        lifted[:, :3] += np.repeat(fn, 3, axis=0) * lift
        tri = tri.copy()
        tri[bad] = (len(uniq) + np.arange(len(lifted))).reshape(-1, 3)
        uniq = np.vstack([uniq, lifted])
    if split_hard:
        # the converter welds vertices by position and the welded vertex takes one normal: at a hard edge (a
        # recess corner, a button bevel) the flat side's vertices took the wall's normal and the thin triangles
        # fanning from the corner shaded black (wedges at every cockpit window / key corner). Vertices at one
        # position with normals more than ~25 deg apart are kept apart: each further normal group moves 50 um
        # into the surface (along its own normal)
        _, gid = np.unique(uniq[:, :3].round(weld), axis=0, return_inverse=True)
        gid = gid.reshape(-1)
        order = np.argsort(gid, kind='stable')
        bounds = np.flatnonzero(np.diff(gid[order])) + 1
        moved = 0
        for grp in np.split(order, bounds):
            if len(grp) < 2:
                continue
            nr = uniq[grp, 3:6] / (np.linalg.norm(uniq[grp, 3:6], axis=1, keepdims=True) + 1e-12)
            ref = [nr[0]]
            step = np.zeros(len(grp))
            for k in range(1, len(grp)):
                hit = [j for j, r in enumerate(ref) if np.dot(nr[k], r) > 0.9]
                if hit:
                    step[k] = hit[0]
                else:
                    ref.append(nr[k])
                    step[k] = len(ref) - 1
            if len(ref) > 1:
                uniq[grp, :3] -= nr * (step * 5e-5)[:, None]
                moved += int((step > 0).sum())
    inverse = tri.reshape(-1)
    fh.write('                    <[tmxglpatch_impexp][element][0]\n')
    fh.write('                        <[uint32][num_vertices][%d]>\n' % len(uniq))
    fh.write('                        <[uint32][num_faces][%d]>\n' % (len(inverse) // 3))
    fh.write('                        <[int32][material_id][%d]>\n' % mat_id)
    fh.write('                        <[int32][vertex_format_size][8]>\n')
    fh.write('                        <[array_int32][vertex_attrib_size][3 3 0 0 2 0 0 0]>\n')
    fh.write('                        <[array_int32][vertex_attrib_offset][0 3 -1 -1 6 -1 -1 -1]>\n')
    fh.write('                        <[list_float64][vertex_list][%s]>\n' % fmt_floats(uniq.reshape(-1)))
    fh.write('                        <[list_uint32][index_list][%s]>\n' % ' '.join(map(str, inverse)))
    fh.write('                        <[list_uint32][face_attrib_list][%s]>\n' % ' '.join(['0'] * (len(inverse) // 3)))
    fh.write('                    >\n')
    return len(uniq), len(inverse) // 3


TEXTURE_CHANNELS = ('normal', 'diffuse', 'specular', 'reflection', 'ambient')
CHANNEL_SUFFIX = {'normal': 'normal', 'diffuse': 'color', 'specular': 'specular', 'reflection': 'reflection',
                  'ambient': 'ambient'}


LUMINANCE_MATERIALS = set()   # materials that also get a self-illumination texture <name>_light


def write_material(fh, i, name, hint):
    fh.write('            <[tmxglmaterial_impexp][element][%d]\n' % i)
    fh.write('                <[string8][name][%s]>\n' % name)
    fh.write('                <[string8][shader_hint][%s]>\n' % hint)
    fh.write('                <[list_tm_tmtexture_index_pair_impexp][texture_list][]\n')
    for ch in TEXTURE_CHANNELS:
        if ch == 'ambient' and hint.startswith('glass'):
            continue
        fh.write('                    <[tm_tmtexture_index_pair_impexp][element][0]\n')
        fh.write('                        <[string8][channel][%s]>\n' % ch)
        fh.write('                        <[string8][name][%s_%s]>\n' % (name, CHANNEL_SUFFIX[ch]))
        fh.write('                        <[bool][repeat_s][true]>\n')
        fh.write('                        <[bool][repeat_t][true]>\n')
        fh.write('                        <[float32][uvscaling][1]>\n')
        fh.write('                    >\n')
    if name in LUMINANCE_MATERIALS:
        fh.write('                    <[tm_tmtexture_index_pair_impexp][element][0]\n')
        fh.write('                        <[string8][channel][luminance]>\n')
        fh.write('                        <[string8][name][%s_light]>\n' % name)
        fh.write('                        <[bool][repeat_s][true]>\n')
        fh.write('                        <[bool][repeat_t][true]>\n')
        fh.write('                        <[float32][uvscaling][1]>\n')
        fh.write('                    >\n')
    fh.write('                >\n')
    fh.write('                <[list_tm_shader_fixed_uniform_impexp][uniform_list][]\n')
    fh.write('                >\n')
    fh.write('            >\n')


def reversed_faces(pos, nrm, uv):
    order = [0, 2, 1]
    return (pos.reshape(-1, 3, 3)[:, order].reshape(-1, 3), -nrm.reshape(-1, 3, 3)[:, order].reshape(-1, 3),
            uv.reshape(-1, 3, 2)[:, order].reshape(-1, 2))


def hull_object(name, points, material):
    """Convex hull mesh object from points (collision proxies)."""
    import bpy, bmesh
    bm = bmesh.new()
    for p in points:
        bm.verts.new(p)
    bmesh.ops.convex_hull(bm, input=bm.verts)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(material)
    return bpy.data.objects.new(name, me)


FINE_MATERIALS = set()   # material indices written with the fine weld (write_patch weld=5, lift=2e-5)


def write_tgi(path, materials, parts, arrays):
    """materials: [(name, hint)] in index order; parts: {part: [objects]}; arrays(o) -> [(mat index, pos, nrm, uv)].
    Returns {part: (objects, vertices, faces)}."""
    stats = {}
    with open(path, 'w') as fh:
        fh.write('<[file][][]\n    <[tmxglscene_impexp][][]\n')
        fh.write('        <[pointer_list_tmxglmaterial_impexp][material_list][]\n')
        for i, (n, hint) in enumerate(materials):
            write_material(fh, i, n, hint)
        fh.write('        >\n')
        fh.write('        <[list_tmxglgeometry_impexp][geometry_list][]\n')
        identity = '1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1'
        for gi, (part, members) in enumerate(sorted(parts.items())):
            chunks = {}
            for o in members:
                for mi, pos, nrm, uv in arrays(o):
                    chunks.setdefault(mi, []).append((pos, nrm, uv))
            fh.write('            <[tmxglgeometry_impexp][element][%d]\n' % gi)
            fh.write('                <[int32][id][%d]>\n' % (1000 + gi))
            fh.write('                <[string8][name][%s]>\n' % part)
            fh.write('                <[matrix4_float64][matrix][ %s]>\n' % identity)
            fh.write('                <[matrix4_float64][matrix_local][ %s]>\n' % identity)
            fh.write('                <[list_tmxglpatch_impexp][patch_list][]\n')
            nv = nf = 0
            for mat_id, lst in sorted(chunks.items()):
                fine = dict(weld=5, lift=2e-5, split_hard=True) if mat_id in FINE_MATERIALS else {}
                v, f = write_patch(fh, mat_id, np.vstack([c[0] for c in lst]), np.vstack([c[1] for c in lst]),
                                   np.vstack([c[2] for c in lst]), **fine)
                nv += v
                nf += f
            fh.write('                >\n            >\n')
            stats[part] = (len(members), nv, nf)
        fh.write('        >\n    >\n>\n')
    return stats
