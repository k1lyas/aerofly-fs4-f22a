"""Texture helpers for building Aerofly FS 4 converter input from DCS textures (run inside Blender).

Rules (docs/PIPELINE.md section 0/3): square power-of-two PNG, 64..4096, 8-bit, only IHDR/pHYs/IDAT/IEND chunks;
`_bump` = height map (the converter builds the normal map), `_specular` RGB + `_specular_alpha` gloss,
`_reflection` strength in red only, `_ambient` = ambient occlusion; colours black >= 8/255, white <= 232/255.
"""
import os, struct, zlib
import bpy
import numpy as np

MIN_SIZE = 64
COLOUR_SCALE = 0.82      # base colour scale for skin materials (see write_material_textures)
AMBIENT_MIN = 0.6        # ambient = AMBIENT_MIN + (1 - AMBIENT_MIN) * AO


def find_texture(tex_dir, name, exts=('.dds', '.png', '.tga', '.bmp')):
    low = {f.lower(): f for f in os.listdir(tex_dir)}
    for ext in exts:
        f = low.get(name.lower() + ext)
        if f:
            return os.path.join(tex_dir, f)
    return None


def load_image(path):
    """RGBA float array (rows top to bottom as stored by Blender: bottom row first)."""
    img = bpy.data.images.load(path)
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    return px.reshape(h, w, 4)


def fit_size(a, limit):
    """Square (repeat along the short side - UVs are normalised), power-of-two box downsampling to limit."""
    n = max(a.shape[0], a.shape[1])
    p2 = 1 << (n.bit_length() - 1)
    if a.shape[0] != a.shape[1] or n != p2:
        # nearest-neighbour resample to a square power of two (UVs are normalised, so the mapping is kept)
        ri = (np.arange(p2) * a.shape[0] // p2)
        ci = (np.arange(p2) * a.shape[1] // p2)
        a = a[ri][:, ci]
    while a.shape[0] > limit or a.shape[1] > limit:
        a = 0.25 * (a[0::2, 0::2] + a[1::2, 0::2] + a[0::2, 1::2] + a[1::2, 1::2])
    if a.shape[0] < MIN_SIZE or a.shape[1] < MIN_SIZE:
        a = np.broadcast_to(a.reshape((-1,) + a.shape[2:]).mean(0), (MIN_SIZE, MIN_SIZE) + a.shape[2:]).copy()
    return a


def strip_png(path):
    """Keep IHDR/pHYs/IEND and merge all IDAT chunks into one (as in the SDK sample textures)."""
    data = open(path, 'rb').read()
    keep, idat, i = {}, [], 8
    while i < len(data):
        n = struct.unpack('>I', data[i:i + 4])[0]
        kind = data[i + 4:i + 8]
        if kind == b'IDAT':
            idat.append(data[i + 8:i + 8 + n])
        elif kind in (b'IHDR', b'pHYs', b'IEND'):
            keep[kind] = data[i:i + 12 + n]
        i += 12 + n
    body = b''.join(idat)
    chunk = struct.pack('>I', len(body)) + b'IDAT' + body + struct.pack('>I', zlib.crc32(b'IDAT' + body) & 0xffffffff)
    open(path, 'wb').write(data[:8] + keep[b'IHDR'] + keep.get(b'pHYs', b'') + chunk + keep[b'IEND'])


def save_png(path, rgb, alpha=None, limit=2048):
    rgb = fit_size(np.asarray(rgb, dtype=np.float32), limit)
    h, w = rgb.shape[:2]
    img = bpy.data.images.new(os.path.basename(path), w, h, alpha=False)
    px = np.ones((h, w, 4), dtype=np.float32)
    px[..., :3] = rgb if rgb.ndim == 3 else rgb[..., None]
    img.pixels.foreach_set(px.reshape(-1))
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)
    strip_png(path)
    if alpha is not None:
        save_png(path[:-4] + '_alpha.png', alpha, limit=limit)


def clamp_colour(rgb):
    """IPACS colour range: black not below 8/255, white not above 232/255 (avoids the 'neon' look)."""
    return np.clip(rgb, 8 / 255.0, 232 / 255.0)


def height_from_normals(nm, size, strength=1.0, depth_px=4.0, sigma_px=6.0):
    """Integrate a (DirectX, green = -y) tangent-space normal map into a 0..1 height map (Frankot-Chellappa).

    `strength` is the DCS material normalMapValue (DCS draws its normal maps at 30 % by default; the fine
    "orange peel" noise in them is meant to be barely visible). Heights use a fixed scale (depth_px pixels =
    full range) instead of stretching to the image range, and a high-pass (sigma_px at 4096) keeps panel lines and
    rivets only; a wider one keeps larger forms (cloth folds).
    """
    nm = fit_size(nm[..., :3].astype(np.float64), size)
    n = nm * 2.0 - 1.0
    nz = np.clip(n[..., 2], 0.2, None)
    p = -n[..., 0] / nz * strength
    q = n[..., 1] / nz * strength
    h, w = p.shape
    wx = np.fft.fftfreq(w) * 2 * np.pi
    wy = np.fft.fftfreq(h) * 2 * np.pi
    WX, WY = np.meshgrid(wx, wy)
    denom = WX ** 2 + WY ** 2
    denom[0, 0] = 1.0
    Z = (-1j * WX * np.fft.fft2(p) - 1j * WY * np.fft.fft2(q)) / denom
    Z[0, 0] = 0.0
    sigma = sigma_px * w / 4096.0
    Z *= 1.0 - np.exp(-denom * sigma ** 2)
    z = np.real(np.fft.ifft2(Z))
    z -= np.median(z)
    return np.clip(0.5 + 0.5 * z / depth_px, 0, 1).astype(np.float32)


def _resample(a, shape):
    """Nearest-neighbour resample of a 2D/3D array to (h, w)."""
    ri = np.arange(shape[0]) * a.shape[0] // shape[0]
    ci = np.arange(shape[1]) * a.shape[1] // shape[1]
    return a[ri][:, ci]


def albedo_relief(rgb, small_px=1.0, large_px=24.0):
    """Relief from a colour map whose folds and seams are painted as shading (the DCS pilot: its normal map is almost
    flat): band-passed luminance (gaussian small_px - large_px), dark = recess, scaled to unit deviation."""
    lum = rgb[..., :3].mean(2).astype(np.float64)
    h, w = lum.shape
    fy, fx = np.fft.fftfreq(h)[:, None], np.fft.fftfreq(w)[None, :]
    f2 = (fx ** 2 + fy ** 2) * (2 * np.pi) ** 2
    F = np.fft.fft2(lum)
    band = np.real(np.fft.ifft2(F * (np.exp(-f2 * small_px ** 2 / 2) - np.exp(-f2 * large_px ** 2 / 2))))
    return (band / (band.std() + 1e-9)).astype(np.float32)


def write_material_textures(out_dir, name, diffuse, normal=None, roughmet=None, size=2048, kind='standard',
                            alpha=False, normal_strength=0.3, height=None):
    """Aerofly channel set for one material from DCS diffuse / normal / RoughMet (R = AO, G = rough, B = metal).

    DCS is a metal/roughness PBR renderer: on metallic texels the base colour is the reflection tint and the
    diffuse part is almost black. Aerofly has a classic diffuse + specular model, so metallic texels get a dark
    diffuse colour and their base colour moves into the specular colour and a stronger reflection.
    """
    base = os.path.join(out_dir, name)
    rgb = fit_size(diffuse[..., :3].astype(np.float32), size)
    if roughmet is not None:
        rm = _resample(fit_size(roughmet[..., :3].astype(np.float32), size), rgb.shape[:2])
        ao, gloss, metal = rm[..., 0], 1.0 - rm[..., 1], rm[..., 2]
    else:
        ao = np.ones(rgb.shape[:2], np.float32)
        gloss, metal = np.full(rgb.shape[:2], 0.4, np.float32), np.zeros(rgb.shape[:2], np.float32)
    # (DCS 'chrome_material' only adds an environment reflection pass; the metalness itself is in RoughMet -
    # forcing metal here turned the tyres, which share the su35_detail texture, into mirrors)
    m3 = metal[..., None]
    # DCS albedo is bright (light-blue camo median ~0.7): in Aerofly the aircraft looked self-lit at dusk next to
    # the stock jets, so the base colour is scaled by COLOUR_SCALE (test 2026-10-09: 0.82)
    colour = clamp_colour(rgb * (1.0 - 0.8 * m3) * COLOUR_SCALE)
    a = fit_size(diffuse[..., 3].astype(np.float32), size) if alpha else None
    save_png(base + '_color.png', colour, a, limit=size)
    hopts = dict(height or {})
    albedo = hopts.pop('albedo', 0.0)         # + relief from the colour map (albedo_relief), this many units per deviation
    bump = height_from_normals(normal, size, normal_strength, **hopts) if normal is not None else None
    if albedo:
        relief = albedo * albedo_relief(rgb)
        bump = np.clip((bump if bump is not None else 0.5) + relief, 0, 1)
    save_png(base + '_bump.png', bump if bump is not None else np.full((64, 64), 0.5, np.float32), limit=size)
    # painted surfaces: weak grey highlights; metal: highlights tinted with the base colour
    # rough metal (e.g. the tyres, which the mod marks metal = 1, rough = 0.7) must stay dull: the reflection
    # strength and the highlight sharpness follow the gloss, not only the metalness
    g3 = gloss[..., None]
    grey = (0.03 + 0.05 * gloss)[..., None]
    spec = np.clip(grey * (1.0 - m3) + rgb * 0.6 * m3 * (0.3 + 0.7 * g3), 0, 1)
    save_png(base + '_specular.png', spec, np.clip(0.45 + 0.50 * gloss, 0, 1), limit=min(size, 2048))
    red = np.zeros(gloss.shape + (3,), np.float32)
    red[..., 0] = np.clip(0.02 + 0.06 * gloss + 0.35 * metal * gloss ** 2, 0, 1)
    save_png(base + '_reflection.png', red, limit=min(size, 2048))
    # AO baked in DCS includes shadows of pylons and stores we drop: keep it subtle
    save_png(base + '_ambient.png', np.clip(AMBIENT_MIN + (1.0 - AMBIENT_MIN) * ao, 0, 1), limit=min(size, 2048))


def write_burner_textures(out_dir, name, diffuse, size=1024, cold=None):
    """Afterburner glow surfaces: sooty dark metal when cold, the DCS self-lit texture as luminance (scaled in the
    game by the graphics object's InputLuminance). cold: an own map for the unlit surface (rgb)."""
    base = os.path.join(out_dir, name)
    rgb = fit_size(diffuse[..., :3].astype(np.float32), size)
    save_png(base + '_color.png', clamp_colour(rgb * 0.15 if cold is None else fit_size(cold.astype(np.float32), size)), limit=size)
    save_png(base + '_light.png', np.clip(rgb, 0, 1), limit=size)
    save_png(base + '_bump.png', np.full((64, 64), 0.5, np.float32))
    save_png(base + '_specular.png', np.full((64, 64, 3), 0.03, np.float32), np.full((64, 64), 0.5, np.float32))
    save_png(base + '_reflection.png', np.zeros((64, 64, 3), np.float32))
    save_png(base + '_ambient.png', np.ones((64, 64), np.float32))


def write_lamp_textures(out_dir, name, colour, off=None, specular=0.6, gloss=0.9, reflection=0.15, light=None):
    """Exterior light lens: tinted when off, the `_light` image is white (the lit colour is the graphics object's
    InputLuminance, switched by the light switches). Glossy glass by default; matte panels (formation strips) pass
    their own off colour, specular, gloss and reflection."""
    base = os.path.join(out_dir, name)
    c = np.array(colour, np.float32)
    off = np.array(off, np.float32) if off is not None else 0.15 + 0.35 * c
    lit = light() if light else None
    # a patterned lens shows the same pattern unlit, dimmer: by day the same strip as at night
    save_png(base + '_color.png', np.broadcast_to(off, (64, 64, 3)).copy() if lit is None else off * (0.45 + 0.55 * lit))
    save_png(base + '_light.png', lit if lit is not None else np.ones((64, 64, 3), np.float32))
    save_png(base + '_bump.png', np.full((64, 64), 0.5, np.float32))
    save_png(base + '_specular.png', np.full((64, 64, 3), specular, np.float32), np.full((64, 64), gloss, np.float32))
    save_png(base + '_reflection.png', np.full((64, 64, 3), reflection, np.float32))
    save_png(base + '_ambient.png', np.ones((64, 64), np.float32))


def write_flat_textures(out_dir, name, colour):
    """Plain matte colour (gap plates inside the structure)."""
    base = os.path.join(out_dir, name)
    save_png(base + '_color.png', np.broadcast_to(np.array(colour, np.float32), (64, 64, 3)).copy())
    save_png(base + '_bump.png', np.full((64, 64), 0.5, np.float32))
    save_png(base + '_specular.png', np.full((64, 64, 3), 0.02, np.float32), np.full((64, 64), 0.3, np.float32))
    save_png(base + '_reflection.png', np.zeros((64, 64, 3), np.float32))
    save_png(base + '_ambient.png', np.full((64, 64), 0.6, np.float32))


def write_illumination_texture(out_dir, name, level, size=512, masks=None, flood=None, flood_on_masks=1.0):
    """Cockpit lighting map <name>_illumination (as the SDK DR400: channel k = InputIllumination<k>): red = flood
    light - the baked light of the flood lamps (`flood`, 1 = brightest) times `level`, else the material's ambient
    occlusion times `level` (recesses stay darker); masks {channel: image} add lit areas in the green / blue channel
    (self-lit panel labels on their own knobs)."""
    base = os.path.join(out_dir, name)
    src = flood if flood is not None else load_image(base + '_ambient.png')[..., 0]
    ao = fit_size(np.asarray(src, np.float32)[..., None], size)[..., 0]
    rgb = np.zeros(ao.shape + (3,), np.float32)
    rgb[..., 0] = np.clip(ao * level, 0, 1)
    for ch, mask in (masks or {}).items():
        rgb[..., ch] = np.clip(fit_size(np.asarray(mask, np.float32)[..., None], ao.shape[0])[..., 0], 0, 1)
        # the lettering is ~10 x brighter paint than its panel, so plain flood light lit it like its own lamps: flood_on_masks is what is left of the flood on it
        rgb[..., 0] *= 1.0 - (1.0 - flood_on_masks) * rgb[..., ch]
    save_png(base + '_illumination.png', rgb, limit=size)


def write_display_textures(out_dir, name, light_size=2048, specular=0.25, gloss=0.9, reflection=0.04, wear=None,
                           wear_tint=(0.45, 0.46, 0.45)):
    """Cockpit display surfaces (MFDs, HUD projection): black glass; the `_light` image is only a placeholder,
    the game renders the display into it (texture_animation TextureName <name>_light). wear: [(x, y, w, h, variant)]
    atlas regions (pixels from the bottom left) that get the worn-glass map (screen_wear_map; variant turns it: 1
    mirror u, 2 mirror v, 4 swap) blended into the dark colour towards wear_tint."""
    base = os.path.join(out_dir, name)
    if wear:
        dark = np.array([8 / 255.0] * 3, np.float32)
        col = np.broadcast_to(dark, (light_size, light_size, 3)).copy()
        m = screen_wear_map()
        n = m.shape[0]
        for x, y, w, h, variant in wear:
            v, u = np.mgrid[0:h, 0:w].astype(np.float32)
            u, v = (u + 0.5) / w, (v + 0.5) / h
            if variant & 1:
                u = 1 - u
            if variant & 2:
                v = 1 - v
            if variant & 4:
                u, v = v, u
            haze = m[np.clip((v * n).astype(int), 0, n - 1), np.clip((u * n).astype(int), 0, n - 1)]
            col[y:y + h, x:x + w] = dark + (np.array(wear_tint, np.float32) - dark) * haze[..., None]
        save_png(base + '_color.png', col, limit=light_size)
    else:
        save_png(base + '_color.png', np.full((64, 64, 3), 8 / 255.0, np.float32))
    # placeholder of the render target's size (as the SDK sample's display_light.png)
    save_png(base + '_light.png', np.zeros((light_size, light_size, 3), np.float32), limit=light_size)
    save_png(base + '_bump.png', np.full((64, 64), 0.5, np.float32))
    save_png(base + '_specular.png', np.full((64, 64, 3), specular, np.float32), np.full((64, 64), gloss, np.float32))
    save_png(base + '_reflection.png', np.full((64, 64, 3), reflection, np.float32))
    save_png(base + '_ambient.png', np.ones((64, 64), np.float32))


def procedural_burner(kind, n=512):
    """Glow textures for burner parts whose DCS texture is missing from the mod. 'disc': the flame-holder vane
    ring (even hot yellow-orange); 'wall': orange with streaks."""
    v, u = np.mgrid[0:n, 0:n] / float(n)            # array row 0 = Blender's bottom row = UV v 0
    hot = np.array([1.0, 0.62, 0.22], np.float32)
    if kind == 'flame':
        # spinning afterburner sleeves (as the Concorde's reheat texture): orange with deep-red blotches and yellow
        # hot spots, seamless around the tube (u) so the spin shows no joint
        tau = 2 * np.pi
        f = (np.sin(tau * 5 * u + 2.2 * np.sin(tau * 3 * v)) * np.sin(tau * 4 * v + 1.7 * np.sin(tau * 2 * u)) +
             0.5 * np.sin(tau * 11 * u + tau * 7 * v) * np.cos(tau * 9 * v - tau * 3 * u))
        base = np.array([1.0, 0.50, 0.12], np.float32)
        red = np.array([0.75, 0.12, 0.04], np.float32)
        yellow = np.array([1.0, 0.85, 0.45], np.float32)
        t_red = np.clip((f - 0.25) / 0.5, 0, 1)[..., None]
        t_yel = np.clip((-f - 0.55) / 0.4, 0, 1)[..., None]
        rgb = base * (1 - t_red) + red * t_red
        rgb = rgb * (1 - t_yel) + yellow * t_yel
        # flame tongues on black: the luminance is multiplied in the game, a texture without dark gaps saturates to a
        # flat bright disc and the spin becomes invisible
        # soft brightness variation (no hard black bands: they spun into a hypnotic spiral)
        g = np.sin(tau * 3 * u + 1.5 * np.sin(tau * 2 * v)) * np.sin(tau * 3 * v + 1.3 * np.sin(tau * 2 * u))
        rgb = rgb * (0.65 + 0.35 * g)[..., None]
    elif kind == 'disc':
        # the 'Circle' mesh is the flame-holder ring with radial vanes (UVs not planar): even hot yellow-orange
        rgb = np.broadcast_to(np.array([1.0, 0.72, 0.32], np.float32), (n, n, 3)).copy()
    else:
        streak = 0.7 + 0.3 * np.cos(u * 2 * np.pi * 24) ** 4
        rgb = hot[None, None, :] * streak[..., None] * 0.85
    out = np.ones((n, n, 4), np.float32)
    out[..., :3] = np.clip(rgb, 0, 1)
    return out


def _blur(a, sigma):
    """Gaussian blur by FFT (wraps at the edges; the glass maps are made larger and cropped)."""
    h, w = a.shape
    fy, fx = np.fft.fftfreq(h)[:, None], np.fft.fftfreq(w)[None, :]
    return np.real(np.fft.ifft2(np.fft.fft2(a) * np.exp(-2 * (np.pi * sigma) ** 2 * (fx * fx + fy * fy))))


def screen_wear_map(n=1024, seed=7):
    """Wear of a flat LCD's face (F-22 MFDs and UFDs, 2026-11-17): matt anti-glare glass, its marks in the
    screen's own colour map, as the stock F/A-18's screens (write_display_textures). Map 0..1, v up, the edges of the
    map = the bezel. (A separate cover glass with the instrument glass shader was tried and dropped the same day: that
    shader reflects one environment picture taken at the spawn, in flight the screens showed the parking spot's trees -
    with a black reflection map as well.) Levels after the SDK sample's instrument glass (dr400 glass_color_alpha mean
    0.07, smudges to ~0.27): ours lighter, a display must stay readable - 0.02 on clean glass.
      dust       along the bezel, a few mm wide, patchy
      wipes      broad arcs of a cloth, faint
      prints     fingertips at the edges where the bezel keys are: ridges ~0.5 mm (5 px at ~0.1 mm per px), oval
      scratches  a few thin lines, longer near the middle"""
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:n, 0:n].astype(np.float32) / n
    edge = np.minimum(np.minimum(x, 1 - x), np.minimum(y, 1 - y))
    noise = lambda s: (lambda b: (b - b.min()) / (np.ptp(b) + 1e-9))(_blur(rng.standard_normal((n, n)).astype(np.float32), s))
    haze = np.full((n, n), 0.02, np.float32)
    dust = np.clip(1 - edge / 0.05, 0, 1) ** 1.5 * np.clip(noise(6) * 1.6 - 0.4, 0, 1)
    haze += 0.09 * dust
    wipes = np.zeros((n, n), np.float32)
    for _ in range(5):
        cx, cy, r = rng.uniform(-0.3, 1.3), rng.uniform(-0.3, 1.3), rng.uniform(0.5, 1.1)
        d = np.abs(np.hypot(x - cx, y - cy) - r)
        wipes += np.exp(-(d / rng.uniform(0.02, 0.05)) ** 2) * rng.uniform(0.4, 1.0)
    wipes *= np.clip(noise(40) * 2 - 0.5, 0, 1)
    haze += 0.03 * wipes
    prints = np.zeros((n, n), np.float32)
    for _ in range(12):
        side = rng.integers(4)
        t, inset = rng.uniform(0.1, 0.9), rng.uniform(0.03, 0.12)
        cx, cy = [(t, inset), (t, 1 - inset), (inset, t), (1 - inset, t)][side]
        a = rng.uniform(0, np.pi)
        u = (x - cx) * np.cos(a) + (y - cy) * np.sin(a)
        v = -(x - cx) * np.sin(a) + (y - cy) * np.cos(a)
        rx, ry = rng.uniform(0.045, 0.06), rng.uniform(0.06, 0.08)
        rr = np.hypot(u / rx, v / ry)
        ridges = 0.5 + 0.5 * np.sin(2 * np.pi * rr * rx * n / 5.0 + 3 * noise(20))
        prints += np.clip(1 - rr, 0, 1) ** 0.7 * ridges * rng.uniform(0.5, 1.0)
    haze += 0.07 * prints
    scratches = np.zeros((n, n), np.float32)
    for _ in range(9):
        p0 = rng.uniform(0.1, 0.9, 2)
        a, length = rng.uniform(0, np.pi), rng.uniform(0.04, 0.25)
        bend = rng.uniform(-0.03, 0.03)
        for s_ in np.linspace(0, 1, int(length * n * 2)):
            px = p0[0] + np.cos(a) * length * s_ - np.sin(a) * bend * np.sin(np.pi * s_)
            py = p0[1] + np.sin(a) * length * s_ + np.cos(a) * bend * np.sin(np.pi * s_)
            i, j = int(py * n), int(px * n)
            if 0 <= i < n and 0 <= j < n:
                scratches[i, j] = max(scratches[i, j], 1.0 - 0.6 * abs(s_ - 0.5) * 2)
    scratches = np.clip(_blur(scratches, 0.6) * 3, 0, 1)
    haze += 0.08 * scratches
    return np.clip(haze, 0, 0.18)


def write_glass_textures(out_dir, name, inside, tint=(0.36, 0.38, 0.40), opacity=0.07, reflection=0.32,
                         specular=(0.0, 0.0, 0.0)):
    """Canopy glass: `tint` / `opacity` the glass colour, `specular` the colour of the sun glints (a coated canopy's
    tint; the exterior glass shader's reflection is a strength only, red channel)."""
    n = 256
    base = os.path.join(out_dir, name)
    save_png(base + '_color.png', np.full((n, n, 3), tint, np.float32), np.full((n, n), opacity, np.float32))
    save_png(base + '_bump.png', np.full((n, n), 0.5, np.float32))
    save_png(base + '_specular.png', np.full((n, n, 3), specular, np.float32), np.ones((n, n), np.float32))
    refl = np.zeros((n, n, 3), np.float32)
    if inside:
        refl[:] = 0.04      # 0.10 until the cockpit build: hazy canopy with a bright sky glare from the seat
    else:
        refl[..., 0] = reflection
    save_png(base + '_reflection.png', refl)
