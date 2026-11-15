// ToonTest_01 step 87 (copy of u13: v6j with the eye material fixes, outputs unity_v6jm_*)
// Material fixes: lash = MMGExp/AnimeToonEyeV6j (A2C alpha sharpened at 0.5, two-sided, depth pulled 1 mm toward the
// camera), lid sheets = skin toon without the outline pass. (Unity Editor, run through the Unity MCP script_eval tool; not compiled into the project).
// v6i check: MG_ToonTest_01_{v6f_A,v6i}_eye.fbx, view-angle keys set by View() = eye_v6_common.view_key_values; in a temporary additive scene (layer 31 only), same boxes as
// t48 (spec/eye_f6_boxes_v6d_3.json): faces with / without hair at 0, +-35, +-45, +-60, +-90 and both eyes x4 without
// hair at every angle, expressions and gaze at 0 / +-35. The light turns with the camera like the t03 sun. Eyeball:
// MMGExp/AnimeToonEyeV6d. Saves renders/unity_<tag>_f6_*.png and closes the scene without saving.
// Materials are created in memory only. Existing scenes, prefabs and assets are not touched (only the new test FBX /
// texture import settings are set).
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

const string Dir = "Assets/_Experiments/ToonTest_01";
string exp = Path.GetFullPath("BlenderSource/Characters/MainGirlfriend/Experiments/ToonTest_01");
string outDir = Path.Combine(exp, "renders");
var tags = new[] { "v6j" };
var log = new List<string>();
AssetDatabase.Refresh();
foreach (var t in tags)
{
    var mi = (ModelImporter)AssetImporter.GetAtPath($"{Dir}/MG_ToonTest_01_{t}_eye.fbx");
    bool dirty = !mi.importBlendShapes || mi.importNormals != ModelImporterNormals.Import || mi.importBlendShapeNormals != ModelImporterNormals.Import
                 || mi.materialImportMode != ModelImporterMaterialImportMode.ImportStandard;
    mi.importBlendShapes = true; mi.importNormals = ModelImporterNormals.Import; mi.importBlendShapeNormals = ModelImporterNormals.Import;
    mi.materialImportMode = ModelImporterMaterialImportMode.ImportStandard;
    if (dirty) mi.SaveAndReimport();
}
AssetDatabase.Refresh();
var shToon = Shader.Find("MMGExp/AnimeToonV6"); var shHair = Shader.Find("MMGExp/AnimeToonHairV2");
var shUnlit = Shader.Find("MMGExp/UnlitTex"); var shEyeC = Shader.Find("MMGExp/AnimeToonEyeV6c");
var shEyeD = Shader.Find("MMGExp/AnimeToonEyeV6d"); var shEyeJ = Shader.Find("MMGExp/AnimeToonEyeV6j"); var shEyeE = Shader.Find("MMGExp/AnimeToonEyeV6e");
if (shEyeJ == null) return "missing MMGExp/AnimeToonEyeV6j";
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
var prevActive = SceneManager.GetActiveScene();
foreach (var tag in tags)
{
    var model = AssetDatabase.LoadAssetAtPath<GameObject>($"{Dir}/MG_ToonTest_01_{tag}_eye.fbx");
    var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Additive);
    try
    {
        var go = (GameObject)Object.Instantiate(model);
        SceneManager.MoveGameObjectToScene(go, scene);
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
            // _ViewPull 1 mm: the head skin under the lash band showed through in specks
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
        var hair = rends.Where(r => r.name.StartsWith("hair_bob_01") || r.name.StartsWith("acc_head")).ToList();
        var mouthOpen = rends.Where(r => r.name.StartsWith("Face_Mouth_Smile")).ToList();
        Renderer closedMouth = R("TT_Mouth_Closed");
        // edit-mode camera renders do not run the skinning update: each pose is baked (BakeMesh) into a plain mesh
        var baked = new Dictionary<SkinnedMeshRenderer, Mesh>();
        foreach (var smr in smrs)
        {
            var bgo = new GameObject(smr.name + "_baked") { layer = 31 };
            bgo.transform.SetParent(smr.transform, false);
            var mesh = new Mesh(); baked[smr] = mesh;
            bgo.AddComponent<MeshFilter>().sharedMesh = mesh;
            var mr = bgo.AddComponent<MeshRenderer>(); mr.sharedMaterials = smr.sharedMaterials;
            smr.enabled = false;
            if (mouthOpen.Contains(smr)) { mouthOpen.Remove(smr); mouthOpen.Add(mr); }
            if (smr.name == "TT_Mouth_Closed") closedMouth = mr;
        }
        float Sm(float t) { t = Mathf.Clamp01(t); return t * t * (3 - 2 * t); }
        // eye_v6_common.view_key_values: yaw (deg, + = camera toward the character's left), gaze (rad), Blink / EyeSmile (0..100)
        Dictionary<string, float> View(Dictionary<string, float> w, float yaw, float gaze)
        {
            var o = new Dictionary<string, float>(w);
            float blink = (w.TryGetValue("Blink", out var b) ? b : 0) / 100f, es = (w.TryGetValue("EyeSmile", out var e) ? e : 0) / 100f;
            float wf0 = Sm((Mathf.Abs(yaw) - 20f) / 20f), side = Sm((Mathf.Abs(yaw) - 50f) / 15f) * 0.8f;
            foreach (var (s, sg) in new[] { ("L", 1f), ("R", -1f) })
            {
                bool far = s == "R" ? yaw > 0 : yaw < 0;
                float sd = far ? side : 0, k = (1 - blink) * (1 - es), ws = (far ? wf0 : 0) * k * (1 - sd);
                float gout = sg * gaze, to = Mathf.Clamp01(gout / 0.25f), ti = Mathf.Clamp01(-gout / 0.12f);
                o[$"ViewFar{s}"] = ws * (1 - to - ti) * 100; o[$"ViewFar{s}_GO"] = ws * to * 100; o[$"ViewFar{s}_GI"] = ws * ti * 100;
                o[$"ViewSide{s}"] = sd * k * 100;
            }
            return o;
        }
        void Keys(Dictionary<string, float> w)
        {
            foreach (var smr in smrs)
            {
                for (int i = 0; i < smr.sharedMesh.blendShapeCount; i++)
                    smr.SetBlendShapeWeight(i, w.TryGetValue(smr.sharedMesh.GetBlendShapeName(i), out var v) ? v : 0f);
                smr.BakeMesh(baked[smr]);
                baked[smr].RecalculateBounds();
            }
            foreach (var r in mouthOpen) r.enabled = false;
            closedMouth.enabled = true;
        }
        void Gaze(float rad) { foreach (var m in mats) if (m.HasProperty("_GazeYaw")) m.SetFloat("_GazeYaw", rad); }

        var camGo = new GameObject("TT_UnityCam"); SceneManager.MoveGameObjectToScene(camGo, scene);
        var cam = camGo.AddComponent<Camera>();
        cam.orthographic = true; cam.cullingMask = 1 << 31; cam.clearFlags = CameraClearFlags.SolidColor;
        cam.backgroundColor = Color.white; cam.nearClipPlane = 0.01f; cam.farClipPlane = 10f; cam.enabled = false;
        void Shoot(string name, int[] b, float yaw, float scale)
        {
            int x0 = b[0], y0 = b[1], x1 = b[2], y1 = b[3];
            int w = x1 - x0, h = y1 - y0, W = (int)(w * scale), H = (int)(h * scale);
            var rot = Quaternion.AngleAxis(sx * yaw, Vector3.up);
            foreach (var m in mats) if (m.HasProperty("_LightDir")) m.SetVector("_LightDir", rot * lightU);   // t03: the sun turns with the camera
            var rt = new RenderTexture(W, H, 24, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB) { antiAliasing = 4 };
            cam.targetTexture = rt; cam.aspect = (float)w / h; cam.orthographicSize = h / ppm / 2f;
            float cx = (((x0 + x1) / 2f) - 1030f) / ppm, cy = zTop - ((y0 + y1) / 2f) / ppm;
            var pivot = new Vector3(0, cy, -0.03f * front);
            var dir = rot * new Vector3(0, 0, front);
            var right = Vector3.Cross(Vector3.up, -dir).normalized;
            cam.transform.position = pivot + dir * 3f + right * cx;
            cam.transform.rotation = Quaternion.LookRotation(-dir, Vector3.up);
            cam.Render();
            var prev = RenderTexture.active; RenderTexture.active = rt;
            var tex = new Texture2D(W, H, TextureFormat.RGB24, false); tex.ReadPixels(new Rect(0, 0, W, H), 0, 0); tex.Apply();
            RenderTexture.active = prev;
            File.WriteAllBytes(Path.Combine(outDir, $"unity_{tag}m_f6_{name}.png"), tex.EncodeToPNG());
            cam.targetTexture = null; rt.Release(); Object.DestroyImmediate(rt); Object.DestroyImmediate(tex);
        }
        var none = new Dictionary<string, float>();
        Keys(none); Gaze(0);
        foreach (var a in new[] { 0, 15, -15, 25, -25, 35, -35, 45, -45, 60, -60, 90, -90 })
        {
            Keys(View(none, a, 0));
            foreach (var r in hair) r.enabled = true;
            Shoot($"face_{a}", new[] { 600, 0, 1460, 860 }, a, 1f);
            foreach (var r in hair) r.enabled = false;
            Shoot($"facenh_{a}", new[] { 600, 0, 1460, 860 }, a, 1f);
            foreach (var s in new[] { "L", "R" }) Shoot($"{s}_toon_{a}", Box(boxJson, $"{s}_{a}"), a, 4f);
        }
        foreach (var r in hair) r.enabled = true;
        var poses = new (string, Dictionary<string, float>, float)[]
        {
            ("Neutral", none, 0), ("Blink50", new Dictionary<string, float> { ["Blink"] = 50 }, 0), ("Blink", new Dictionary<string, float> { ["Blink"] = 100 }, 0),
            ("EyeSmile", new Dictionary<string, float> { ["EyeSmile"] = 100 }, 0),
            ("SmileEyeSmile", new Dictionary<string, float> { ["Smile"] = 100, ["EyeSmile"] = 100 }, 0),
            ("Surprise", new Dictionary<string, float> { ["Surprise"] = 100 }, 0), ("GazeL", none, 0.15f), ("GazeR", none, -0.15f), ("GazeLmax", none, 0.25f), ("GazeRmax", none, -0.25f), ("GazeLh", none, 0.06f), ("GazeRh", none, -0.06f),
        };
        foreach (var a in new[] { 0, 35, -35 })
        {
            var bl = Box(boxJson, $"L_{a}"); var br = Box(boxJson, $"R_{a}");
            float cx = (bl[0] + bl[2] + br[0] + br[2]) / 4f, cy = (bl[1] + bl[3] + br[1] + br[3]) / 4f;
            var b = new[] { (int)(cx - 280), (int)(cy - 110), (int)(cx + 280), (int)(cy + 150) };
            foreach (var (pn, w, gz) in poses)
            {
                Keys(View(w, a, gz)); Gaze(gz);
                Shoot($"expr_{pn}_{a}", b, a, 1.4f);
            }
        }
        // head turn 0 -> 60 -> 0 and 0 -> -60 -> 0 (t74 frames)
        Directory.CreateDirectory(Path.Combine(outDir, $"unity_{tag}m_rot"));
        var seq = Enumerable.Range(0, 31).Select(i => 2 * i).Concat(Enumerable.Range(0, 30).Select(i => 58 - 2 * i)).ToList();
        seq = seq.Concat(seq.Select(v => -v)).ToList();
        for (int i = 0; i < seq.Count; i++)
        {
            Keys(View(none, seq[i], 0)); Gaze(0);
            Shoot($"rot_{i:000}", new[] { 560, 340, 1500, 640 }, seq[i], 1f);
            string dst = Path.Combine(outDir, $"unity_{tag}m_rot", $"{i:000}.png");
            if (File.Exists(dst)) File.Delete(dst);
            File.Move(Path.Combine(outDir, $"unity_{tag}m_f6_rot_{i:000}.png"), dst);
        }
        Keys(none); Gaze(0);
        log.Add($"{tag}: rendered");
    }
    finally
    {
        EditorSceneManager.CloseScene(scene, true);
        SceneManager.SetActiveScene(prevActive);
    }
}
log.Add($"active after: {SceneManager.GetActiveScene().path} dirty {SceneManager.GetActiveScene().isDirty} scenes {SceneManager.sceneCount}");
return string.Join("\n", log);
