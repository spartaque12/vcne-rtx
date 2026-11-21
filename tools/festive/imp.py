# blender -b --python imp.py -- <ydr dir> <out dir> : import each streetlight ydr, dump info, save .blend
import bpy, sys, os, mathutils
src, out = sys.argv[sys.argv.index('--') + 1:][:2]
for f in sorted(os.listdir(src)):
    if not f.endswith('.ydr'): continue
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.preferences.addon_enable(module='bl_ext.user_default.sollumz')
    r = bpy.ops.sollumz.import_assets(directory=src, files=[{'name': f}])
    print('IMPORT', f, r)
    for o in bpy.data.objects:
        if o.type == 'MESH':
            bb = [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
            mn = [round(min(v[i] for v in bb), 2) for i in range(3)]; mx = [round(max(v[i] for v in bb), 2) for i in range(3)]
            print('  MESH', o.name, len(o.data.vertices), mn, mx, [m.name for m in o.data.materials])
        else: print('  OBJ', o.type, o.name, tuple(round(x, 2) for x in o.matrix_world.translation), getattr(o.data, 'type', ''))
    for m in bpy.data.materials:
        tex = [(n.name, n.image.name if n.image else None, n.image.size[:] if n.image else None) for n in (m.node_tree.nodes if m.node_tree else []) if n.type == 'TEX_IMAGE']
        print('  MAT', m.name, getattr(getattr(m, 'shader_properties', None), 'name', ''), tex)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, f[:-4] + '.blend'))
