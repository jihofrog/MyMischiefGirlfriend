"""ToonTest_01 step 6 (Blender, background): Soft Stylized 3D material set on the v3 shapes, saved as v3_soft.

usage: Blender -b <Experiments/ToonTest_01/MG_ToonTest_01_v3.blend> --python t06_soft_style.py
Same meshes / shape keys / colours (r30_face_spec.json) as the toon file; only materials, lights and outlines change:
- skin: Principled BSDF, r30 face colour, low subsurface (warm radius), roughness 0.55, low specular
- eyes: r30 iris picture as base colour + emission 0.6, glossy coat (wet look); whites shaded softly
- hair: Principled, r30 hair base, anisotropic gloss, strand texture (same wave as toon v2) as colour variation
- facial lines (lashes, brows, mouth): matte Principled in the toon colours
- outlines (TT_Outline Solidify) off; key sun + soft fill + rim light, grey world ambient
Writes MG_ToonTest_01_v3_soft.blend.
"""
import json
import math
import os

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.dirname(HERE)
assert os.path.abspath(bpy.data.filepath).startswith(EXP)
SPEC = json.load(open(os.path.join(EXP, "spec", "r30_face_spec.json")))


def srgb(c):
    c = [v / 255.0 for v in c]
    return tuple(((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c) + (1.0,)


def principled(name, colour, rough=0.6, spec=0.3, sss=0.0, coat=0.0, aniso=0.0, emission=None, emit=0.0, image=None):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    p.inputs["Base Color"].default_value = srgb(colour)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Specular IOR Level"].default_value = spec
    if sss:
        p.inputs["Subsurface Weight"].default_value = sss
        p.inputs["Subsurface Radius"].default_value = (1.0, 0.35, 0.2)
        p.inputs["Subsurface Scale"].default_value = 0.01
    if coat:
        p.inputs["Coat Weight"].default_value = coat; p.inputs["Coat Roughness"].default_value = 0.05
    if aniso:
        p.inputs["Anisotropic"].default_value = aniso
    if image is not None:
        tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = image
        nt.links.new(tex.outputs["Color"], p.inputs["Base Color"]); nt.links.new(tex.outputs["Alpha"], p.inputs["Alpha"])
        nt.links.new(tex.outputs["Color"], p.inputs["Emission Color"]); p.inputs["Emission Strength"].default_value = emit
        if hasattr(m, "surface_render_method"):
            m.surface_render_method = "BLENDED"
    elif emit:
        p.inputs["Emission Color"].default_value = srgb(emission or colour); p.inputs["Emission Strength"].default_value = emit
    nt.links.new(p.outputs[0], out.inputs[0])
    return m, nt, p


S = SPEC["skin"]; HC = SPEC["hair"]
skin, _, _ = principled("SS_Skin", S["base"], rough=0.55, spec=0.25, sss=0.12)
hair, hnt, hp = principled("SS_Hair", HC["base"], rough=0.5, spec=0.35, aniso=0.5)
tc = hnt.nodes.new("ShaderNodeTexCoord"); mp = hnt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (70.0, 70.0, 6.0)
wave = hnt.nodes.new("ShaderNodeTexWave"); wave.wave_type = "BANDS"; wave.bands_direction = "X"; wave.inputs["Distortion"].default_value = 6.0
mix = hnt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.inputs["Factor"].default_value = 0.25
mix.inputs["A"].default_value = srgb(HC["base"]); mix.inputs["B"].default_value = srgb((92, 48, 42))
hnt.links.new(tc.outputs["Object"], mp.inputs[0]); hnt.links.new(mp.outputs[0], wave.inputs["Vector"])
hnt.links.new(wave.outputs["Fac"], mix.inputs["Factor"]); hnt.links.new(mix.outputs["Result"], hp.inputs["Base Color"])
clip, _, _ = principled("SS_Clip", SPEC["hairclip_colour"]["base"], rough=0.25, spec=0.5, coat=0.4)
iris_img = next(i for i in bpy.data.images if i.name.startswith("tex_iris"))
iris, _, _ = principled("SS_Iris", (120, 60, 50), rough=0.2, spec=0.5, coat=1.0, emit=0.6, image=iris_img)
white, _, _ = principled("SS_EyeWhite", (250, 246, 246), rough=0.3, spec=0.4, emit=0.35)
flat = {}
for src, c in (("TT_MG_Eye_Lash", (45, 20, 18)), ("TT_MG_Eye_UpperLid", (45, 20, 18)), ("TT_MG_Eye_OuterLine", (45, 20, 18)),
               ("TT_MG_Face_Lash", (45, 20, 18)), ("TT_MG_Face_LowerLash", (90, 45, 40)), ("TT_MG_Eye_LowerLid", (120, 60, 52)),
               ("TT_MG_Eye_Crease", (150, 85, 72)), ("TT_MG_Face_Brow", (120, 66, 56)), ("TT_Mouth_Line", (176, 84, 76)),
               ("TT_Nose_Dot", (240, 186, 168)), ("TT_MG_Face_MouthInside", (150, 60, 60)), ("TT_MG_Face_Teeth", (250, 248, 245)),
               ("TT_MG_Face_Tongue", (220, 120, 115))):
    flat[src] = principled("SS_" + src[3:], c, rough=0.8, spec=0.1, emit=0.25)[0]
swap = {"TT_Skin": skin, "TT_Hair": hair, "TT_Clip": clip, "TT_Eye_Iris": iris, "TT_MG_Eye_White": white, **flat}
for o in bpy.data.objects:
    if o.type not in ("MESH", "CURVE"):
        continue
    for slot in o.material_slots:
        if slot.material and slot.material.name in swap:
            slot.material = swap[slot.material.name]
    for md in getattr(o, "modifiers", []):
        if md.name == "TT_Outline":
            md.show_render = False; md.show_viewport = False

# lights: key (the toon sun, made softer), fill, rim; grey ambient
sun = bpy.data.objects["TT_Sun"]; sun.data.energy = 1.9; sun.data.angle = math.radians(12)
def light(name, kind, energy, rot, colour=(1, 1, 1)):
    d = bpy.data.lights.new(name, kind); d.energy = energy; d.color = colour
    if kind == "SUN":
        d.angle = math.radians(25)
    o = bpy.data.objects.new(name, d); bpy.context.scene.collection.objects.link(o); o.rotation_euler = rot
    return o
light("SS_Fill", "SUN", 0.45, (math.radians(75), 0, math.radians(40)), (1.0, 0.95, 0.92))
light("SS_Rim", "SUN", 1.4, (math.radians(-60), 0, math.radians(160)), (1.0, 0.92, 0.85))
w = bpy.context.scene.world or bpy.data.worlds.new("World"); bpy.context.scene.world = w
w.use_nodes = True
bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
bg.inputs["Color"].default_value = (0.55, 0.55, 0.58, 1); bg.inputs["Strength"].default_value = 0.35
bpy.context.scene.view_settings.view_transform = "Standard"
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(EXP, "MG_ToonTest_01_v3_soft.blend"))
print("SOFT_OK")
