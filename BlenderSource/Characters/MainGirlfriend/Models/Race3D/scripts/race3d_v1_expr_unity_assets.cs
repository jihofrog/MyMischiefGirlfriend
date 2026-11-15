// Race3D v1 + v3b expressions formal Unity assets (EDIT mode, script_eval_file).
// Rebuilds MainGirlfriend_Race3D_v1.prefab from the updated FBX (pre-expr backup already under Model3D/_backup_v1_*).
// Does not touch open scenes, Live2D, Mobile_RPAsset, or Assets/_Experiments/Race3D_v3b.
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
const string TablePath = Root + "/HairBrowPullTable_bob.asset";
const string SpecPath = "Assets/_Game/Art/Characters/MainGirlfriend/Model3D/Spec";
string projJson = File.ReadAllText(Path.GetFullPath("BlenderSource/Characters/MainGirlfriend/Models/Race3D/spec/race3d_v3b_unity_proj.json"));
var log = new List<string>();
AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);

var shToon = Shader.Find("MMG/Character/Toon");
var shHair = Shader.Find("MMG/Character/ToonHairStencil") ?? Shader.Find("MMG/Character/ToonHair");
var shUnlit = Shader.Find("MMG/Character/Unlit");
var shBall = Shader.Find("MMG/Character/EyeBallSparkle") ?? Shader.Find("MMG/Character/EyeBall");
var shLash = Shader.Find("MMG/Character/EyeLash");
var shBrow = Shader.Find("MMG/Character/BrowCard");
var shTear = Shader.Find("MMG/Character/TearStream");
if (shToon == null || shHair == null || shUnlit == null || shBall == null || shLash == null || shBrow == null || shTear == null)
    return $"missing shader toon={shToon!=null} hair={shHair!=null} unlit={shUnlit!=null} ball={shBall!=null} lash={shLash!=null} brow={shBrow!=null} tear={shTear!=null}";

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

var mi = (ModelImporter)AssetImporter.GetAtPath(Fbx);
if (mi == null) return "missing " + Fbx;
mi.importBlendShapes = true; mi.importNormals = ModelImporterNormals.Import; mi.importBlendShapeNormals = ModelImporterNormals.Import;
mi.materialImportMode = ModelImporterMaterialImportMode.ImportStandard;
mi.importCameras = false; mi.importLights = false; mi.importAnimation = false;
mi.animationType = ModelImporterAnimationType.Generic;
mi.SaveAndReimport();

foreach (var (p, alpha) in new[] {
    ("T_MainGirlfriend_EyeLash_L", true), ("T_MainGirlfriend_EyeLash_R", true),
    ("T_MainGirlfriend_EyeBall_L", false), ("T_MainGirlfriend_EyeBall_R", false),
    ("T_MainGirlfriend_BlushRadial", true),
    ("T_MainGirlfriend_EyeSparkle_L", true), ("T_MainGirlfriend_EyeSparkle_R", true) })
{
    var path = $"{Root}/Textures/{p}.png";
    if (!File.Exists(Path.GetFullPath(path))) { log.Add("skip tex " + p); continue; }
    AssetDatabase.ImportAsset(path);
    var ti = (TextureImporter)AssetImporter.GetAtPath(path);
    if (ti == null) continue;
    ti.textureType = TextureImporterType.Default; ti.sRGBTexture = true; ti.mipmapEnabled = true;
    ti.wrapMode = TextureWrapMode.Clamp; ti.filterMode = FilterMode.Bilinear; ti.alphaIsTransparency = alpha;
    ti.SaveAndReimport();
}
Texture2D Tex(string n) => AssetDatabase.LoadAssetAtPath<Texture2D>($"{Root}/Textures/{n}.png");

if (!AssetDatabase.IsValidFolder(Root + "/Materials")) AssetDatabase.CreateFolder(Root, "Materials");
var created = new List<Material>();
Material Save(Material m, string name)
{
    m.name = name;
    string path = $"{Root}/Materials/{name}.mat";
    var existing = AssetDatabase.LoadAssetAtPath<Material>(path);
    if (existing != null) { EditorUtility.CopySerialized(m, existing); Object.DestroyImmediate(m); created.Add(existing); return existing; }
    AssetDatabase.CreateAsset(m, path); created.Add(m); return m;
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
var hair = new Material(shHair); hair.SetColor("_HairColor", C(124, 68, 59)); hair.SetColor("_OutlineColor", C(66, 30, 26)); hair.renderQueue = 2010; Save(hair, "M_hair_bob_01_01");
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
    ["M_Ex_MouthInside"] = Unlit("M_Ex_MouthInside", C(150, 60, 60), null, 3000),
    ["M_Ex_Tongue"] = Unlit("M_Ex_Tongue", C(230, 120, 120), null, 3001),
    ["M_Ex_Teeth"] = Unlit("M_Ex_Teeth", C(250, 248, 248), null, 3001),
    ["M_Ex_MouthRim"] = Unlit("M_Ex_MouthRim", C(150, 70, 62), null, 3002),
    ["M_Tear"] = Unlit("M_Tear", new Color(190/255f, 224/255f, 255/255f, 0.6f), null, 3006),
    ["M_TearHighlight"] = Unlit("M_TearHighlight", new Color(1, 1, 1, 0.9f), null, 3007),
};
var browCard = new Material(shBrow); browCard.SetColor("_BaseColor", C(78, 38, 34)); browCard.SetFloat("_Pull", 0.03f); Save(browCard, "M_MainGirlfriend_BrowCard");
var tearStream = new Material(shTear); Save(tearStream, "M_MainGirlfriend_TearStream");
map["M_BrowCard"] = browCard; map["M_TearStream"] = tearStream;
foreach (var side in new[] { "L", "R" })
{
    var l = new Material(shLash); l.SetFloat("_Mode", 0); l.SetFloat("_ViewPull", 0.001f); l.SetColor("_BaseColor", Color.white);
    l.SetTexture("_BaseMap", Tex($"T_MainGirlfriend_EyeLash_{side}")); l.SetFloat("_A2C", 1); l.SetFloat("_LitLo", 0.85f); l.SetFloat("_LitMid", 0.95f);
    l.renderQueue = 2450;
    map[$"MG6c_Lash_{side}"] = Save(l, $"M_MainGirlfriend_EyeLash_{side}");
    var b = new Material(shBall); b.SetFloat("_Mode", 1); b.SetColor("_BaseColor", Color.white); b.SetTexture("_BaseMap", Tex($"T_MainGirlfriend_EyeBall_{side}"));
    b.SetFloat("_UseAO", 1); b.SetFloat("_ViewDim", 0.10f); b.SetFloat("_HLDim", 0.20f); b.SetFloat("_LitLo", 0.8f); b.SetFloat("_LitMid", 0.93f);
    b.SetVector("_Proj", Proj(side)); b.SetFloat("_Sparkle", 0); b.SetTexture("_SparkleTex", Tex($"T_MainGirlfriend_EyeSparkle_{side}"));
    b.renderQueue = 2450;
    map[$"MG6d_EyeBall_{side}"] = Save(b, $"M_MainGirlfriend_EyeBall_{side}");
    map[$"MG6d_EyeBall_{side}_sparkle"] = map[$"MG6d_EyeBall_{side}"];
}

// HairBrowPullTable
var tableType = System.AppDomain.CurrentDomain.GetAssemblies().Select(a => a.GetType("MMG.Characters.Avatar3D.HairBrowPullTable")).FirstOrDefault(t => t != null);
if (tableType == null) return "HairBrowPullTable type missing — compile first";
var table = AssetDatabase.LoadAssetAtPath<ScriptableObject>(TablePath);
if (table == null)
{
    table = ScriptableObject.CreateInstance(tableType);
    AssetDatabase.CreateAsset(table, TablePath);
}
var soT = new SerializedObject(table);
soT.FindProperty("defaultPullMeters").floatValue = 0.03f;
var entries = soT.FindProperty("entries");
entries.arraySize = 1;
entries.GetArrayElementAtIndex(0).FindPropertyRelative("hairItemId").stringValue = "hair_bob_01_01";
entries.GetArrayElementAtIndex(0).FindPropertyRelative("pullMeters").floatValue = 0.03f;
soT.ApplyModifiedPropertiesWithoutUndo();
EditorUtility.SetDirty(table);
log.Add("table " + TablePath);

if (AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath) != null)
    AssetDatabase.DeleteAsset(PrefabPath);

var model = AssetDatabase.LoadAssetAtPath<GameObject>(Fbx);
var tmp = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Additive);
try
{
    var go = (GameObject)PrefabUtility.InstantiatePrefab(model, tmp);
    go.name = "MainGirlfriend_Race3D_v1";
    var rends = go.GetComponentsInChildren<Renderer>(true).ToList();
    Renderer R(string n) => rends.FirstOrDefault(r => r.name == n);
    var head = R("Blockout_Head").bounds; var eyeL = R("Eye_Ball.L").bounds;
    float sx = Mathf.Sign(eyeL.center.x);
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
            if (r.name.StartsWith("Face_BrowCard")) { dst[i] = browCard; continue; }
            if (r.name.StartsWith("Face_TearStream")) { dst[i] = tearStream; continue; }
            if (map.TryGetValue(n, out var m)) dst[i] = m;
            else { dst[i] = src[i]; if (!string.IsNullOrEmpty(n)) unmapped.Add($"{r.name}:{n}"); }
        }
        r.sharedMaterials = dst;
    }
    foreach (var r in rends.Where(r => r.name.StartsWith("Face_Mouth_Smile"))) r.enabled = false;
    // hide expression overlays until the driver reveals them
    foreach (var r in rends.Where(r => r.name.StartsWith("Face_BrowCard") || r.name.StartsWith("Face_Tear") || r.name == "Face_Mouth_ExSmile" || r.name == "Face_Mouth_ExO"))
        r.enabled = false;

    Transform Pt(string n, Vector3 p) { var t = new GameObject(n).transform; t.SetParent(go.transform, true); t.position = p; return t; }
    var smrs = go.GetComponentsInChildren<SkinnedMeshRenderer>(true);
    var eyeView = go.AddComponent<MMG.Characters.Avatar3D.EyeViewController>();
    eyeView.head = go.transform;
    eyeView.faceForwardLocal = new Vector3(0, 0, front);
    eyeView.characterLeftLocal = new Vector3(sx, 0, 0);
    eyeView.eyeL = Pt("EyeCentre.L", R("Eye_Ball.L").bounds.center);
    eyeView.eyeR = Pt("EyeCentre.R", R("Eye_Ball.R").bounds.center);
    eyeView.renderers = smrs.Where(s => s.name.StartsWith("Eye_Lids") || s.name.StartsWith("Eye_Lash")
        || s.name.StartsWith("Eye_White") || s.name.StartsWith("Eye_Iris") || s.name.StartsWith("Eye_Pupil")
        || s.name.StartsWith("Eye_Highlight") || s.name.StartsWith("Eye_OuterLine") || s.name.StartsWith("Eye_Upper")).ToList();
    eyeView.eyeMaterials = new List<Material> { map["MG6d_EyeBall_L"], map["MG6d_EyeBall_R"] };
    eyeView.inputSource = MMG.Characters.Avatar3D.EyeViewController.InputSource.Fields;

    var expr = go.AddComponent<MMG.Characters.Avatar3D.ExpressionController>();
    expr.eyeView = eyeView;
    expr.eyeSparkleShader = shBall;
    expr.hairStencilShader = shHair;
    expr.browCardShader = shBrow;
    expr.tearStreamShader = shTear;
    expr.unlitShader = shUnlit;
    expr.sparkleL = Tex("T_MainGirlfriend_EyeSparkle_L");
    expr.sparkleR = Tex("T_MainGirlfriend_EyeSparkle_R");
    expr.browPullTable = table as MMG.Characters.Avatar3D.HairBrowPullTable;
    expr.hairItemId = "hair_bob_01_01";
    expr.lightAtFront = lightU;
    expr.projData = new[]
    {
        new MMG.Characters.Avatar3D.ExpressionController.Proj { side = "L", su = J(projJson,"L.su"), tu = J(projJson,"L.tu"), sv = J(projJson,"L.sv"), tv = J(projJson,"L.tv"), uc = J(projJson,"L.uc"), vc = J(projJson,"L.vc") },
        new MMG.Characters.Avatar3D.ExpressionController.Proj { side = "R", su = J(projJson,"R.su"), tu = J(projJson,"R.tu"), sv = J(projJson,"R.sv"), tv = J(projJson,"R.tv"), uc = J(projJson,"R.uc"), vc = J(projJson,"R.vc") },
    };

    var prefab = PrefabUtility.SaveAsPrefabAsset(go, PrefabPath, out bool ok);
    int shapes = smrs.Sum(s => s.sharedMesh != null ? s.sharedMesh.blendShapeCount : 0);
    var perMesh = smrs.Where(s => s.sharedMesh != null && s.sharedMesh.blendShapeCount > 0)
        .Select(s => $"{s.name}:{s.sharedMesh.blendShapeCount}:[{string.Join(",", Enumerable.Range(0, s.sharedMesh.blendShapeCount).Select(s.sharedMesh.GetBlendShapeName))}]");
    if (!AssetDatabase.IsValidFolder(SpecPath)) AssetDatabase.CreateFolder(Root, "Spec");
    File.WriteAllText(Path.GetFullPath(SpecPath + "/blendshape_inventory_unity.txt"),
        $"total_channels={shapes}\nmeshes={smrs.Count(s => s.sharedMesh != null && s.sharedMesh.blendShapeCount > 0)}\n" + string.Join("\n", perMesh));
    log.Add($"prefab {PrefabPath} ok {ok}; renderers {rends.Count}, skinned {smrs.Length}, blend shape channels {shapes}");
    log.Add("unmapped [" + string.Join(", ", unmapped) + "]");
    log.Add("sx " + sx + " front " + front + " light " + lightU);
}
finally
{
    EditorSceneManager.CloseScene(tmp, true);
}
AssetDatabase.SaveAssets();
log.Add($"active {SceneManager.GetActiveScene().path} dirty {SceneManager.GetActiveScene().isDirty}");
return string.Join("\n", log);
