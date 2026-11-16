"""DCS visibility of every EDM node: {node index: [(arg, [(lo, hi), ...]), ...]}, the ArgVisibilityNodes on the
node's chain up to the root, nearest first. A node is drawn by DCS while every arg value lies in one of its ranges.

Damage parts use it: the intact pieces of a wing hang under a visibility node whose range ends at 1.0 (shown while
the damage argument is < 1), the stubs left behind under one starting at 1.0. Object property edm_parent_node (set
by edm_to_blend.py) is the index used here; the importer's split-node fix is applied the same way, so the indices
agree (checked on the F-22: FIN_L_BOTTOM node 99 under arg 243).

    vis = edm_vis.load(<io_EDM dir>, <model.edm>)
"""
import sys


def _patch_split(RenderNode):
    """As edm_to_blend.py: render nodes split between parents per vertex (EDM v10 mods)."""
    if getattr(RenderNode, '_vis_patched', False):
        return
    by_range = RenderNode.split

    def split(self):
        pd = self.parentData
        if not pd or len(pd) < 2 or pd[-1][-2] == len(self.indexData):
            return by_range(self)
        tri = [int(round(self.vertexData[self.indexData[i]][3])) for i in range(0, len(self.indexData), 3)]
        out = []
        for k, (parent, _to, damage) in enumerate(pd):
            idx = [v for t, p in enumerate(tri) if p == k for v in self.indexData[3 * t:3 * t + 3]]
            if not idx:
                continue
            n = RenderNode()
            n.version, n.props, n.material = self.version, self.props, self.material
            n.name, n.name_unknown = '{}_{}'.format(self.name, k), True
            n.parent, n.damage_argument = parent, damage
            n.indexData, n.vertexData = idx, self.vertexData
            out.append(n)
        return out

    RenderNode.split = split
    RenderNode._vis_patched = True


def load(ioedm_dir, edm_path):
    if ioedm_dir not in sys.path:
        sys.path.insert(0, ioedm_dir)
    from edm import EDMFile
    from edm.types import ArgVisibilityNode, RenderNode
    if RenderNode.split.__name__ != '_split_render_node':      # (edm_to_blend.py's own fix, when imported)
        _patch_split(RenderNode)
    f = EDMFile(edm_path)
    nodes = f.nodes

    def index(p):
        return p if isinstance(p, int) else (nodes.index(p) if p is not None else None)

    out = {}
    for i in range(len(nodes)):
        vis, j, guard = [], i, 0
        while j is not None and j >= 0 and guard < 64:
            n = nodes[j]
            if isinstance(n, ArgVisibilityNode):
                vis += [(a, [(float(lo), float(hi)) for lo, hi in r]) for a, r in n.visData]
            j, guard = index(getattr(n, 'parent', None)), guard + 1
        if vis:
            out[i] = vis
    return out
