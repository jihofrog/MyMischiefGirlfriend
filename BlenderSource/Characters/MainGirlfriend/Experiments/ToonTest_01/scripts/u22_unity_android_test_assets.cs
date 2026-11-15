// ToonTest_01 step 94 (Unity Editor, EDIT mode, script_eval; not compiled into the project): Android device test assets.
// Creates only new files under Assets/_Experiments/ToonTest_01/AndroidTest/: materials (same values as u15 / u19: lash
// MMGExp/AnimeToonEyeV6j with _ViewPull 1 mm, lid sheets without outline), blush texture, the v6j test prefab (FBX
// instance + materials + EyeCentre.L/R + EyeViewController, Fields input), an animation clip / AnimatorController / Director
// asset that animate the controller fields, and the scene EyeViewAndroidTest.unity with EyeViewDeviceTest.
// The open scene is not touched (the new scene is created additively, saved and closed).
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEditor.Animations;

const string Dir = "Assets/_Experiments/ToonTest_01";
string exp = Path.GetFullPath("BlenderSource/Characters/MainGirlfriend/Experiments/ToonTest_01");
string outDir = Path.Combine(exp, "renders", "unity_final");
var tags = new[] { "v6j" };
var log = new List<string>();
if (Application.isPlaying) return "run in edit mode";
var shToon = Shader.Find("MMGExp/AnimeToonV6"); var shHair = Shader.Find("MMGExp/AnimeToonHairV2");
var shUnlit = Shader.Find("MMGExp/UnlitTex"); var shEyeC = Shader.Find("MMGExp/AnimeToonEyeV6c");
var shEyeD = Shader.Find("MMGExp/AnimeToonEyeV6d"); var shEyeJ = Shader.Find("MMGExp/AnimeToonEyeV6j"); var shEyeE = Shader.Find("MMGExp/AnimeToonEyeV6e");
if (shToon == null || shHair == null || shUnlit == null || shEyeC == null || shEyeD == null || shEyeE == null)
    return $"missing shader {shToon != null} {shHair != null} {shUnlit != null} {shEyeC != null} {shEyeD != null} {shEyeE != null}";
float J(string json, string path)
{
    // "a.b.c" in a small nested json (numbers only)
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
int[] Box(string json, string key)
{
    int j = json.IndexOf("\"" + key + "\"");
    var m = Regex.Match(json.Substring(j), "\\[\\s*(-?\\d+),\\s*(-?\\d+),\\s*(-?\\d+),\\s*(-?\\d+)\\s*\\]");
    return Enumerable.Range(1, 4).Select(g => int.Parse(m.Groups[g].Value)).ToArray();
}
string projJson = File.ReadAllText(Path.Combine(exp, "spec", "eye_v6b_unity_proj.json"));
string shadeJson = File.ReadAllText(Path.Combine(exp, "spec", "eye_v6e_outer_shade.json"));
string boxJson = File.ReadAllText(Path.Combine(exp, "spec", "eye_f6_boxes_v6i.json"));
Vector4 Proj(string side) => new Vector4(J(projJson, side + ".su"), J(projJson, side + ".tu"), J(projJson, side + ".sv"), J(projJson, side + ".tv"));
float headH = 0.4015944f, topZ = 1.650909f, ppm = 733f / headH, zTop = topZ + 21f / ppm;
Color C(int r, int g, int b) => new Color(r / 255f, g / 255f, b / 255f, 1);
const string Out = "Assets/_Experiments/ToonTest_01/AndroidTest";
if (!AssetDatabase.IsValidFolder(Out)) AssetDatabase.CreateFolder("Assets/_Experiments/ToonTest_01", "AndroidTest");
if (!AssetDatabase.IsValidFolder(Out + "/Materials")) AssetDatabase.CreateFolder(Out, "Materials");
var tag = "v6j";
var model = AssetDatabase.LoadAssetAtPath<GameObject>($"{Dir}/MG_ToonTest_01_{tag}_eye.fbx");
var tmpScene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Additive);
Vector3 lightLocal;
List<Material> lightMats;
GameObject prefab;
{
        var go = (GameObject)Object.Instantiate(model);
        go.name = "EyeView_v6j_AndroidTest";
        foreach (var t in go.GetComponentsInChildren<Transform>(true)) t.gameObject.layer = 31;
        var rends = go.GetComponentsInChildren<Renderer>(true).ToList();
        Renderer R(string n) => rends.FirstOrDefault(r => r.name == n);
        var head = R("Blockout_Head").bounds; var eyeL = R("Eye_Ball.L").bounds;
        float sx = Mathf.Sign(eyeL.center.x);                                     // Blender +X (character left) -> Unity sx * X
        float front = Mathf.Sign(R("TT_Mouth_Closed").bounds.center.z - head.center.z);
        Vector3 lightB = new Vector3(-0.296f, -0.814f, 0.5f);
        Vector3 lightU = new Vector3(sx * lightB.x, lightB.z, (lightB.y < 0 ? front : -front) * Mathf.Abs(lightB.y));
        var smrs = go.GetComponentsInChildren<SkinnedMeshRenderer>(true);
        int total = 0; var names = new SortedSet<string>();
        foreach (var smr in smrs) for (int i = 0; i < smr.sharedMesh.blendShapeCount; i++) { total++; names.Add(smr.sharedMesh.GetBlendShapeName(i)); }
        log.Add($"{tag}: renderers {rends.Count}, skinned {smrs.Length}, blend shapes {total} ({string.Join(",", names)})");
        Mesh MeshOf(Renderer r) => r is SkinnedMeshRenderer s ? s.sharedMesh : r.GetComponent<MeshFilter>().sharedMesh;
        var eyeRends = rends.Where(r => r.name.StartsWith("Eye_")).ToList();
        log.Add($"{tag}: eye meshes {eyeRends.Count}, eye tris {eyeRends.Sum(r => MeshOf(r).triangles.Length / 3)}, eye materials {eyeRends.Sum(r => r.sharedMaterials.Length)}, head tris {MeshOf(R("Blockout_Head")).triangles.Length / 3}, all tris {rends.Sum(r => MeshOf(r).triangles.Length / 3)}");

        var mats = new List<Material>();
        Material Track(Material m) { mats.Add(m); return m; }
        Material Toon(Color sh, Color mid, Color bas, Color lit, Color line, float width)
        {
            var m = Track(new Material(shToon));
            m.SetColor("_ShadowColor", sh); m.SetColor("_MidColor", mid); m.SetColor("_BaseColor", bas); m.SetColor("_LightColor", lit);
            m.SetColor("_OutlineColor", line); m.SetFloat("_OutlineWidth", width);
            return m;
        }
        Material Unlit(Color c, Texture tex = null, int queue = 3002)
        { var m = Track(new Material(shUnlit)); m.SetColor("_BaseColor", c); if (tex) m.SetTexture("_BaseMap", tex); m.renderQueue = queue; return m; }
        var blushTex = new Texture2D(64, 64, TextureFormat.RGBA32, false);
        for (int y = 0; y < 64; y++) for (int x = 0; x < 64; x++)
        {
            float dx = (x - 31.5f) / 32f, dy = (y - 31.5f) / 32f * 1.6f; float a = Mathf.Clamp01(1 - Mathf.Sqrt(dx * dx + dy * dy)) * 0.42f;
            blushTex.SetPixel(x, y, new Color(1, 1, 1, a));
        }
        blushTex.Apply();
        Texture2D Tex(string n) => AssetDatabase.LoadAssetAtPath<Texture2D>($"{Dir}/{n}.png");
        var map = new Dictionary<string, Material>
        {
            ["TT_Skin"] = Toon(C(238, 172, 150), C(252, 195, 176), C(253, 208, 189), C(254, 225, 209), C(150, 88, 70), 0.0011f),
            ["TT_Clip"] = Toon(C(205, 196, 200), C(205, 196, 200), C(242, 231, 233), C(242, 231, 233), C(66, 30, 26), 0.0016f),
            ["TT_MG_Face_Brow"] = Unlit(C(120, 66, 56)), ["TT_Mouth_Line"] = Unlit(C(176, 84, 76)), ["TT_Nose_Dot"] = Unlit(C(240, 186, 168)),
            ["TT_Blush_Radial"] = Unlit(C(248, 160, 150), blushTex, 3003),
            ["TT_MG_Face_MouthInside"] = Unlit(C(150, 60, 60), null, 3000), ["TT_MG_Face_Teeth"] = Unlit(C(250, 248, 248), null, 3001),
            ["TT_MG_Face_Tongue"] = Unlit(C(230, 120, 120), null, 3001), ["TT_MG_Face_LipLine"] = Unlit(C(150, 70, 62), null, 3002),
        };
        foreach (var side in new[] { "L", "R" })
        {
            var m = Track(new Material(shEyeJ)); m.SetFloat("_Mode", 0); m.SetFloat("_ViewPull", 0.001f); m.SetColor("_BaseColor", Color.white); m.SetTexture("_BaseMap", Tex($"eye_tex_lash_v6c_{side}"));
            m.SetFloat("_A2C", 1); m.SetFloat("_LitLo", 0.85f); m.SetFloat("_LitMid", 0.95f);
            map[$"MG6c_Lash_{side}"] = m;
            foreach (var (name, sh) in new[] { ($"MG6d_EyeBall_{side}", shEyeD), ($"MG6e_EyeBall_{side}", shEyeE) })
            {
                var d = Track(new Material(sh)); d.SetFloat("_Mode", 1); d.SetColor("_BaseColor", Color.white); d.SetTexture("_BaseMap", Tex($"eye_tex_ball_v6d_{side}"));
                d.SetFloat("_UseAO", 1); d.SetFloat("_ViewDim", 0.10f); d.SetFloat("_HLDim", 0.20f);
                d.SetFloat("_LitLo", 0.8f); d.SetFloat("_LitMid", 0.93f); d.SetVector("_Proj", Proj(side));
                if (sh == shEyeE)
                {
                    d.SetFloat("_OuterShade", J(shadeJson, side + ".strength"));
                    d.SetFloat("_OuterX0", J(shadeJson, side + ".x0")); d.SetFloat("_OuterX1", J(shadeJson, side + ".x1"));
                }
                map[name] = d;
            }
        }
        var hairMat = Track(new Material(shHair));
        hairMat.SetColor("_HairColor", C(124, 68, 59)); hairMat.SetColor("_OutlineColor", C(66, 30, 26));
        map["M_hair_bob_01_01"] = hairMat; map["M_acc_head_hairclip_x_01_01"] = map["TT_Clip"];
        var unmapped = new HashSet<string>(); var used = new SortedSet<string>();
        var lidSkin = Toon(C(238, 172, 150), C(252, 195, 176), C(253, 208, 189), C(254, 225, 209), C(150, 88, 70), 0f);   // no outline on the lid sheets
        foreach (var r in rends)
        {
            var src = r.sharedMaterials; var dst = new Material[src.Length];
            for (int i = 0; i < src.Length; i++)
            {
                string n = src[i] ? src[i].name.Replace(" (Instance)", "") : "";
                if (n == "TT_Skin" && r.name.StartsWith("Eye_Lids")) { dst[i] = lidSkin; continue; }
                if (map.TryGetValue(n, out var m)) { dst[i] = m; if (r.name.StartsWith("Eye_")) used.Add(n + "->" + m.shader.name); }
                else { dst[i] = src[i]; unmapped.Add(n); }
            }
            r.sharedMaterials = dst;
        }
        log.Add($"{tag}: unmapped [{string.Join(",", unmapped)}] eye materials [{string.Join(", ", used)}]");
        foreach (var r in rends.Where(r => r.name.StartsWith("Face_Mouth_Smile"))) r.enabled = false;
        foreach (var t in go.GetComponentsInChildren<Transform>(true)) t.gameObject.layer = 0;
        lightLocal = lightU;
        // save the blush texture and every material in use as assets
        AssetDatabase.CreateAsset(Object.Instantiate(blushTex), Out + "/blush_radial.asset");
        var blushAsset = AssetDatabase.LoadAssetAtPath<Texture2D>(Out + "/blush_radial.asset");
        var savedMats = new Dictionary<Material, Material>();
        foreach (var r in rends)
        {
            var arr = r.sharedMaterials;
            for (int i = 0; i < arr.Length; i++)
            {
                var m = arr[i];
                if (m == null || AssetDatabase.Contains(m)) continue;
                if (!savedMats.TryGetValue(m, out var saved))
                {
                    if (m.HasProperty("_BaseMap") && m.GetTexture("_BaseMap") == blushTex) m.SetTexture("_BaseMap", blushAsset);
                    string n = (r.name.StartsWith("Eye_Lids") && m.shader == shToon ? "LidSkin" : m.name.Length > 0 ? m.name : r.name + "_" + i);
                    n = new string(n.Select(ch => char.IsLetterOrDigit(ch) || ch == '_' ? ch : '_').ToArray());
                    string p = AssetDatabase.GenerateUniqueAssetPath($"{Out}/Materials/{n}.mat");
                    AssetDatabase.CreateAsset(m, p);
                    saved = m;
                    savedMats[m] = saved;
                }
                arr[i] = saved;
            }
            r.sharedMaterials = arr;
        }
        lightMats = savedMats.Values.Where(m => m.HasProperty("_LightDir")).ToList();
        Transform Pt(string n, Vector3 p) { var t = new GameObject(n).transform; t.SetParent(go.transform, true); t.position = p; return t; }
        var ctrl = go.AddComponent<MMG.Experiments.EyeView.EyeViewController>();
        ctrl.head = go.transform;
        ctrl.faceForwardLocal = new Vector3(0, 0, front);
        ctrl.characterLeftLocal = new Vector3(sx, 0, 0);
        ctrl.eyeL = Pt("EyeCentre.L", R("Eye_Ball.L").bounds.center);
        ctrl.eyeR = Pt("EyeCentre.R", R("Eye_Ball.R").bounds.center);
        ctrl.renderers = smrs.ToList();
        ctrl.eyeMaterials = savedMats.Values.Where(m => m.HasProperty("_GazeYaw")).ToList();
        ctrl.inputSource = MMG.Experiments.EyeView.EyeViewController.InputSource.Fields;
        var an = go.AddComponent<Animator>(); an.enabled = false;
        prefab = PrefabUtility.SaveAsPrefabAsset(go, Out + "/EyeView_v6j_AndroidTest.prefab");
        log.Add($"prefab: renderers {rends.Count}, skinned {smrs.Length}, materials saved {savedMats.Count}, light materials {lightMats.Count}, gaze materials {ctrl.eyeMaterials.Count}");
}
EditorSceneManager.CloseScene(tmpScene, true);
// animation driving the controller fields
var clip = new AnimationClip { name = "EyeView_FieldsTest" };
var cb = new AnimationCurve(new Keyframe(0, 0), new Keyframe(0.3f, 1), new Keyframe(0.6f, 0), new Keyframe(1.2f, 0));
var ce = new AnimationCurve(new Keyframe(0, 0), new Keyframe(0.6f, 0), new Keyframe(0.9f, 0.6f), new Keyframe(1.2f, 0));
var cg = new AnimationCurve(new Keyframe(0, -0.25f), new Keyframe(0.6f, 0.25f), new Keyframe(1.2f, -0.25f));
clip.SetCurve("", typeof(MMG.Experiments.EyeView.EyeViewController), "blink", cb);
clip.SetCurve("", typeof(MMG.Experiments.EyeView.EyeViewController), "eyeSmile", ce);
clip.SetCurve("", typeof(MMG.Experiments.EyeView.EyeViewController), "gaze", cg);
var st = AnimationUtility.GetAnimationClipSettings(clip); st.loopTime = true; AnimationUtility.SetAnimationClipSettings(clip, st);
AssetDatabase.CreateAsset(clip, Out + "/EyeView_FieldsTest.anim");
var ac = AnimatorController.CreateAnimatorControllerAtPathWithClip(Out + "/EyeView_FieldsTest.controller", clip);
var da = ScriptableObject.CreateInstance<MMG.Experiments.EyeView.EyeViewDirectorAsset>();
da.clip = clip;
AssetDatabase.CreateAsset(da, Out + "/EyeView_DirectorTest.asset");
// scene
var sc = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Additive);
var drv = new GameObject("EyeViewDeviceTest");
SceneManager.MoveGameObjectToScene(drv, sc);
var t2 = drv.AddComponent<MMG.Experiments.EyeView.EyeViewDeviceTest>();
t2.characterPrefab = prefab;
t2.lightMaterials = lightMats;
t2.lightLocal = lightLocal;
t2.animController = ac;
t2.directorAsset = da;
EditorSceneManager.SaveScene(sc, Out + "/EyeViewAndroidTest.unity");
EditorSceneManager.CloseScene(sc, true);
AssetDatabase.SaveAssets();
log.Add($"scene {Out}/EyeViewAndroidTest.unity; light {lightLocal}; active scene {SceneManager.GetActiveScene().path} dirty {SceneManager.GetActiveScene().isDirty}");
return string.Join("\n", log);
