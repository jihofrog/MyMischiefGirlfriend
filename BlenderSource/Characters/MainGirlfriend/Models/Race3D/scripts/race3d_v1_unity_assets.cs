// MainGirlfriend Race3D v1 (Unity Editor, EDIT mode, Unity MCP script_eval_file; not compiled into the project).
// Creates only new files under Assets/_Game/Art/Characters/MainGirlfriend/Model3D/: import settings of the FBX and the
// textures, the blush texture, materials on the MMG/Character/* shaders (same values as the device-tested v6j assets:
// lash A2C with _ViewPull 1 mm, lid sheets without outline) and the prefab MainGirlfriend_Race3D_v1.prefab (variant of
// the FBX model: materials, EyeCentre.L/R, MMG.Characters.Avatar3D.EyeViewController with Fields input).
// Open scenes, existing prefabs and the experiment assets are not touched (the prefab is built in a temporary additive
// scene that is closed without saving).
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

if (Application.isPlaying) return "run in edit mode";
const string Root = "Assets/_Game/Art/Characters/MainGirlfriend/Model3D";
const string Fbx = Root + "/MainGirlfriend_Race3D_v1.fbx";
const string PrefabPath = Root + "/MainGirlfriend_Race3D_v1.prefab";
string projJson = File.ReadAllText(Path.GetFullPath("BlenderSource/Characters/MainGirlfriend/Experiments/ToonTest_01/spec/eye_v6b_unity_proj.json"));
var log = new List<string>();
if (AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath) != null) return "prefab exists: " + PrefabPath;
var shToon = Shader.Find("MMG/Character/Toon"); var shHair = Shader.Find("MMG/Character/ToonHair");
var shUnlit = Shader.Find("MMG/Character/Unlit"); var shBall = Shader.Find("MMG/Character/EyeBall"); var shLash = Shader.Find("MMG/Character/EyeLash");
if (shToon == null || shHair == null || shUnlit == null || shBall == null || shLash == null)
    return $"missing shader {shToon != null} {shHair != null} {shUnlit != null} {shBall != null} {shLash != null}";
float J(string json, string path)
{
    string s = json;
    var keys = path.Split('.');
    for (int k = 0; k < keys.Length - 1; k++)
    {
        int i = s.IndexOf("\"" + keys[k] + "\"");
        int o = s.IndexOf('{', i), depth = 0, e = o;
        for (; e < s.Length; e++) { if (s[e] == '{') depth++; else if (s[e] == '}' && --depth == 0) break; }
        s = s.Substring(o, e - o + 1);
    }
    var m = Regex.Match(s, "\"" + keys[keys.Length - 1] + "\"\\s*:\\s*([-0-9.eE]+)");
    return float.Parse(m.Groups[1].Value, System.Globalization.CultureInfo.InvariantCulture);
}
Vector4 Proj(string side) => new Vector4(J(projJson, side + ".su"), J(projJson, side + ".tu"), J(projJson, side + ".sv"), J(projJson, side + ".tv"));
Color C(int r, int g, int b) => new Color(r / 255f, g / 255f, b / 255f, 1);

// ---------------------------------------------------------------- import settings
AssetDatabase.Refresh();
var mi = (ModelImporter)AssetImporter.GetAtPath(Fbx);
if (mi == null) return "missing " + Fbx;
mi.importBlendShapes = true; mi.importNormals = ModelImporterNormals.Import; mi.importBlendShapeNormals = ModelImporterNormals.Import;
mi.materialImportMode = ModelImporterMaterialImportMode.ImportStandard;
mi.importCameras = false; mi.importLights = false; mi.importAnimation = false;
mi.animationType = ModelImporterAnimationType.Generic;
mi.SaveAndReimport();
// blush: soft radial spot (alpha 0.42 at the centre), same as the device-tested asset
string blushPath = Root + "/Textures/T_MainGirlfriend_BlushRadial.png";
var bt = new Texture2D(64, 64, TextureFormat.RGBA32, false);
for (int y = 0; y < 64; y++) for (int x = 0; x < 64; x++)
{
    float dx = (x - 31.5f) / 32f, dy = (y - 31.5f) / 32f * 1.6f; float a = Mathf.Clamp01(1 - Mathf.Sqrt(dx * dx + dy * dy)) * 0.42f;
    bt.SetPixel(x, y, new Color(1, 1, 1, a));
}
bt.Apply();
File.WriteAllBytes(Path.GetFullPath(blushPath), bt.EncodeToPNG());
Object.DestroyImmediate(bt);
AssetDatabase.ImportAsset(blushPath);
foreach (var (p, alpha) in new[] { ("T_MainGirlfriend_EyeLash_L", true), ("T_MainGirlfriend_EyeLash_R", true), ("T_MainGirlfriend_EyeBall_L", false),
                                   ("T_MainGirlfriend_EyeBall_R", false), ("T_MainGirlfriend_BlushRadial", true) })
{
    var ti = (TextureImporter)AssetImporter.GetAtPath($"{Root}/Textures/{p}.png");
    ti.textureType = TextureImporterType.Default; ti.sRGBTexture = true; ti.mipmapEnabled = true;
    ti.wrapMode = TextureWrapMode.Clamp; ti.filterMode = FilterMode.Bilinear; ti.alphaIsTransparency = alpha;
    ti.SaveAndReimport();
}
Texture2D Tex(string n) => AssetDatabase.LoadAssetAtPath<Texture2D>($"{Root}/Textures/{n}.png");

// ---------------------------------------------------------------- materials
if (!AssetDatabase.IsValidFolder(Root + "/Materials")) AssetDatabase.CreateFolder(Root, "Materials");
var created = new List<Material>();
Material Save(Material m, string name)
{
    m.name = name;
    AssetDatabase.CreateAsset(m, $"{Root}/Materials/{name}.mat");
    created.Add(m);
    return m;
}
Material Toon(string name, Color sh, Color mid, Color bas, Color lit, Color line, float width)
{
    var m = new Material(shToon);
    m.SetColor("_ShadowColor", sh); m.SetColor("_MidColor", mid); m.SetColor("_BaseColor", bas); m.SetColor("_LightColor", lit);
    m.SetColor("_OutlineColor", line); m.SetFloat("_OutlineWidth", width);
    return Save(m, name);
}
Material Unlit(string name, Color c, Texture tex = null, int queue = 3002)
{
    var m = new Material(shUnlit); m.SetColor("_BaseColor", c); if (tex) m.SetTexture("_BaseMap", tex); m.renderQueue = queue;
    return Save(m, name);
}
var skin = Toon("M_MainGirlfriend_Skin", C(238, 172, 150), C(252, 195, 176), C(253, 208, 189), C(254, 225, 209), C(150, 88, 70), 0.0011f);
var lidSkin = Toon("M_MainGirlfriend_LidSkin", C(238, 172, 150), C(252, 195, 176), C(253, 208, 189), C(254, 225, 209), C(150, 88, 70), 0f);
var clip = Toon("M_acc_head_hairclip_x_01_01", C(205, 196, 200), C(205, 196, 200), C(242, 231, 233), C(242, 231, 233), C(66, 30, 26), 0.0016f);
var hair = new Material(shHair); hair.SetColor("_HairColor", C(124, 68, 59)); hair.SetColor("_OutlineColor", C(66, 30, 26)); Save(hair, "M_hair_bob_01_01");
var map = new Dictionary<string, Material>
{
    ["TT_Skin"] = skin, ["TT_Clip"] = clip, ["M_acc_head_hairclip_x_01_01"] = clip, ["M_hair_bob_01_01"] = hair,
    ["TT_MG_Face_Brow"] = Unlit("M_MainGirlfriend_Brow", C(120, 66, 56)),
    ["TT_Mouth_Line"] = Unlit("M_MainGirlfriend_MouthLine", C(176, 84, 76)),
    ["TT_Nose_Dot"] = Unlit("M_MainGirlfriend_Nose", C(240, 186, 168)),
    ["TT_Blush_Radial"] = Unlit("M_MainGirlfriend_Blush", C(248, 160, 150), Tex("T_MainGirlfriend_BlushRadial"), 3003),
    ["TT_MG_Face_MouthInside"] = Unlit("M_MainGirlfriend_MouthInside", C(150, 60, 60), null, 3000),
    ["TT_MG_Face_Teeth"] = Unlit("M_MainGirlfriend_Teeth", C(250, 248, 248), null, 3001),
    ["TT_MG_Face_Tongue"] = Unlit("M_MainGirlfriend_Tongue", C(230, 120, 120), null, 3001),
    ["TT_MG_Face_LipLine"] = Unlit("M_MainGirlfriend_LipLine", C(150, 70, 62), null, 3002),
};
foreach (var side in new[] { "L", "R" })
{
    var l = new Material(shLash); l.SetFloat("_Mode", 0); l.SetFloat("_ViewPull", 0.001f); l.SetColor("_BaseColor", Color.white);
    l.SetTexture("_BaseMap", Tex($"T_MainGirlfriend_EyeLash_{side}")); l.SetFloat("_A2C", 1); l.SetFloat("_LitLo", 0.85f); l.SetFloat("_LitMid", 0.95f);
    l.renderQueue = 2450;
    map[$"MG6c_Lash_{side}"] = Save(l, $"M_MainGirlfriend_EyeLash_{side}");
    var b = new Material(shBall); b.SetFloat("_Mode", 1); b.SetColor("_BaseColor", Color.white); b.SetTexture("_BaseMap", Tex($"T_MainGirlfriend_EyeBall_{side}"));
    b.SetFloat("_UseAO", 1); b.SetFloat("_ViewDim", 0.10f); b.SetFloat("_HLDim", 0.20f); b.SetFloat("_LitLo", 0.8f); b.SetFloat("_LitMid", 0.93f);
    b.SetVector("_Proj", Proj(side)); b.renderQueue = 2450;
    map[$"MG6d_EyeBall_{side}"] = Save(b, $"M_MainGirlfriend_EyeBall_{side}");
}

// ---------------------------------------------------------------- prefab (variant of the FBX model)
var model = AssetDatabase.LoadAssetAtPath<GameObject>(Fbx);
var tmp = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Additive);
try
{
    var go = (GameObject)PrefabUtility.InstantiatePrefab(model, tmp);
    go.name = "MainGirlfriend_Race3D_v1";
    var rends = go.GetComponentsInChildren<Renderer>(true).ToList();
    Renderer R(string n) => rends.FirstOrDefault(r => r.name == n);
    var head = R("Blockout_Head").bounds; var eyeL = R("Eye_Ball.L").bounds;
    float sx = Mathf.Sign(eyeL.center.x);                                         // Blender +X (character left) -> Unity sx * X
    float front = Mathf.Sign(R("TT_Mouth_Closed").bounds.center.z - head.center.z);
    Vector3 lightB = new Vector3(-0.296f, -0.814f, 0.5f);
    Vector3 lightU = new Vector3(sx * lightB.x, lightB.z, (lightB.y < 0 ? front : -front) * Mathf.Abs(lightB.y));
    foreach (var m in created) if (m.HasProperty("_LightDir")) m.SetVector("_LightDir", lightU);
    var unmapped = new SortedSet<string>();
    foreach (var r in rends)
    {
        var src = r.sharedMaterials; var dst = new Material[src.Length];
        for (int i = 0; i < src.Length; i++)
        {
            string n = src[i] ? src[i].name.Replace(" (Instance)", "") : "";
            if (n == "TT_Skin" && r.name.StartsWith("Eye_Lids")) { dst[i] = lidSkin; continue; }
            if (map.TryGetValue(n, out var m)) dst[i] = m;
            else { dst[i] = src[i]; unmapped.Add($"{r.name}:{n}"); }
        }
        r.sharedMaterials = dst;
    }
    foreach (var r in rends.Where(r => r.name.StartsWith("Face_Mouth_Smile"))) r.enabled = false;
    Transform Pt(string n, Vector3 p) { var t = new GameObject(n).transform; t.SetParent(go.transform, true); t.position = p; return t; }
    var smrs = go.GetComponentsInChildren<SkinnedMeshRenderer>(true);
    var ctrl = go.AddComponent<MMG.Characters.Avatar3D.EyeViewController>();
    ctrl.head = go.transform;
    ctrl.faceForwardLocal = new Vector3(0, 0, front);
    ctrl.characterLeftLocal = new Vector3(sx, 0, 0);
    ctrl.eyeL = Pt("EyeCentre.L", R("Eye_Ball.L").bounds.center);
    ctrl.eyeR = Pt("EyeCentre.R", R("Eye_Ball.R").bounds.center);
    ctrl.renderers = smrs.ToList();
    ctrl.eyeMaterials = new List<Material> { map["MG6d_EyeBall_L"], map["MG6d_EyeBall_R"] };
    ctrl.inputSource = MMG.Characters.Avatar3D.EyeViewController.InputSource.Fields;
    var prefab = PrefabUtility.SaveAsPrefabAsset(go, PrefabPath, out bool ok);
    int shapes = smrs.Sum(s => s.sharedMesh.blendShapeCount);
    log.Add($"prefab {PrefabPath} ok {ok} variant {PrefabUtility.GetPrefabAssetType(prefab)}; renderers {rends.Count}, skinned {smrs.Length}, blend shapes {shapes}, " +
            $"materials {created.Count}, unmapped [{string.Join(", ", unmapped)}], sx {sx}, front {front}, light {lightU}");
    log.Add("blend shape names: " + string.Join(",", smrs.SelectMany(s => Enumerable.Range(0, s.sharedMesh.blendShapeCount).Select(i => s.sharedMesh.GetBlendShapeName(i))).Distinct().OrderBy(x => x)));
}
finally
{
    EditorSceneManager.CloseScene(tmp, true);
}
AssetDatabase.SaveAssets();
log.Add($"active scene {SceneManager.GetActiveScene().path} dirty {SceneManager.GetActiveScene().isDirty}");
return string.Join("\n", log);
