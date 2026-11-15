// ToonTest_01 step 11 (Unity Editor, run through the Unity MCP script_eval tool; not compiled into the project).
// Puts hair_bob_01_test.fbx on the v3 test character (the old helmet renderers are switched off on the temporary
// instance only), renders it with MMGExp/AnimeToonHair in a temporary additive scene (layer 31 only), saves
// BlenderSource/.../ToonTest_01/renders/unity_hair4_*.png, then closes the temporary scene without saving.
// Materials are created in memory only. Existing scenes, prefabs and assets are not touched.
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

const string Dir = "Assets/_Experiments/ToonTest_01";
string outDir = Path.GetFullPath("BlenderSource/Characters/MainGirlfriend/Experiments/ToonTest_01/renders");
AssetDatabase.Refresh();
var model = AssetDatabase.LoadAssetAtPath<GameObject>(Dir + "/MG_ToonTest_01_v3.fbx");
var hairModel = AssetDatabase.LoadAssetAtPath<GameObject>(Dir + "/hair_bob_01_test.fbx");
var shHair = Shader.Find("MMGExp/AnimeToonHair");
if (hairModel == null || shHair == null) return $"missing: hair fbx {hairModel != null} hair shader {shHair != null}";
var iris = AssetDatabase.LoadAssetAtPath<Texture2D>(Dir + "/tex_iris_R.png");
var shToon = Shader.Find("MMGExp/AnimeToon"); var shSoft = Shader.Find("MMGExp/SoftStylized"); var shUnlit = Shader.Find("MMGExp/UnlitTex");
if (model == null || iris == null || shToon == null || shSoft == null || shUnlit == null)
    return $"missing: model {model != null} iris {iris != null} toon {shToon != null} soft {shSoft != null} unlit {shUnlit != null}";

var prevActive = SceneManager.GetActiveScene();
var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Additive);
var log = new List<string>();
try
{
    var go = (GameObject)Object.Instantiate(model);
    SceneManager.MoveGameObjectToScene(go, scene);
    var hairGo = (GameObject)Object.Instantiate(hairModel);
    SceneManager.MoveGameObjectToScene(hairGo, scene);
    foreach (var t in go.GetComponentsInChildren<Transform>(true)) t.gameObject.layer = 31;
    foreach (var t in hairGo.GetComponentsInChildren<Transform>(true)) t.gameObject.layer = 31;
    foreach (var r in go.GetComponentsInChildren<Renderer>(true)) if (r.name == "Hair_Main" || r.name == "Hair_Clip_X") r.enabled = false;
    var rends = new List<Renderer>(go.GetComponentsInChildren<Renderer>(true));
    rends.AddRange(hairGo.GetComponentsInChildren<Renderer>(true));
    Bounds B(string n) { foreach (var r in rends) if (r.name == n) return r.bounds; return new Bounds(); }
    var head = B("Blockout_Head"); var eyeL = B("Eye_White.L");
    float sx = Mathf.Sign(eyeL.center.x);                    // Blender +X (character left) -> Unity sx * X
    float front = Mathf.Sign(eyeL.center.z - head.center.z);  // Unity Z of the face side
    log.Add($"head {head.center} eyeL {eyeL.center} sx {sx} front {front}");

    // blender_fit / r30 spec numbers (see spec/*.json)
    float headH = 0.4015944f, topZ = 1.650909f, ppm = 733f / headH, zTop = topZ + 21f / ppm;
    Color C(int r, int g, int b) => new Color(r / 255f, g / 255f, b / 255f, 1);
    Vector3 lightB = new Vector3(-0.296f, -0.814f, 0.5f);       // Blender sun (60, 0, -20 deg): toward the light
    Vector3 lightU = new Vector3(sx * lightB.x, lightB.z, (lightB.y < 0 ? front : -front) * Mathf.Abs(lightB.y));

    Material Toon(Color sh, Color mid, Color bas, Color lit, Color line, float width, bool band = false)
    {
        var m = new Material(shToon);
        m.SetColor("_ShadowColor", sh); m.SetColor("_MidColor", mid); m.SetColor("_BaseColor", bas); m.SetColor("_LightColor", lit);
        m.SetColor("_OutlineColor", line); m.SetFloat("_OutlineWidth", width); m.SetVector("_LightDir", lightU);
        if (band) { m.SetFloat("_HairBand", 1); m.SetColor("_BandColor", C(226, 168, 156)); }
        return m;
    }
    Material Unlit(Color c, Texture tex = null, int queue = 3002)
    {
        var m = new Material(shUnlit); m.SetColor("_BaseColor", c); if (tex) m.SetTexture("_BaseMap", tex); m.renderQueue = queue; return m;
    }
    var blushTex = new Texture2D(64, 64, TextureFormat.RGBA32, false);
    for (int y = 0; y < 64; y++) for (int x = 0; x < 64; x++)
    {
        float dx = (x - 31.5f) / 32f, dy = (y - 31.5f) / 32f * 1.6f; float a = Mathf.Clamp01(1 - Mathf.Sqrt(dx * dx + dy * dy) / 1.0f) * 0.42f;
        blushTex.SetPixel(x, y, new Color(1, 1, 1, a));
    }
    blushTex.Apply();

    var flat = new Dictionary<string, Material>
    {
        ["TT_MG_Eye_White"] = Unlit(C(250, 246, 246), null, 3000), ["TT_Eye_Iris"] = Unlit(Color.white, iris, 3001),
        ["TT_MG_Eye_Lash"] = Unlit(C(45, 20, 18)), ["TT_MG_Eye_UpperLid"] = Unlit(C(45, 20, 18)), ["TT_MG_Eye_OuterLine"] = Unlit(C(45, 20, 18)),
        ["TT_MG_Eye_LowerLid"] = Unlit(C(120, 60, 52)), ["TT_MG_Eye_Crease"] = Unlit(C(150, 85, 72)), ["TT_MG_Face_Brow"] = Unlit(C(120, 66, 56)),
        ["TT_MG_Face_Lash"] = Unlit(C(45, 20, 18)), ["TT_MG_Face_LowerLash"] = Unlit(C(90, 45, 40)), ["TT_Mouth_Line"] = Unlit(C(176, 84, 76)),
        ["TT_Nose_Dot"] = Unlit(C(240, 186, 168)), ["TT_Blush_Radial"] = Unlit(C(248, 160, 150), blushTex, 3003),
    };
    var toon = new Dictionary<string, Material>(flat)
    {
        ["TT_Skin"] = Toon(C(238, 172, 150), C(252, 195, 176), C(253, 208, 189), C(254, 225, 209), C(150, 88, 70), 0.0011f),
        ["TT_Hair"] = Toon(C(70, 34, 30), C(110, 58, 50), C(124, 68, 59), C(166, 98, 84), C(66, 30, 26), 0.0016f, true),
        ["TT_Clip"] = Toon(C(205, 196, 200), C(205, 196, 200), C(242, 231, 233), C(242, 231, 233), C(66, 30, 26), 0.0016f),
    };
    var hairMat = new Material(shHair);
    hairMat.SetColor("_HairColor", C(124, 68, 59)); hairMat.SetColor("_OutlineColor", C(66, 30, 26)); hairMat.SetVector("_LightDir", lightU);
    toon["M_hair_bob_01_01"] = hairMat;
    toon["M_hair_bob_01_02"] = Toon(C(62, 34, 30), C(62, 34, 30), C(62, 34, 30), C(62, 34, 30), C(62, 34, 30), 0f);
    toon["M_acc_head_hairclip_x_01_01"] = toon["TT_Clip"];
    var original = new Dictionary<Renderer, Material[]>();
    foreach (var r in rends) original[r] = r.sharedMaterials;
    var unmapped = new HashSet<string>();
    void Apply(Dictionary<string, Material> map)
    {
        foreach (var r in rends)
        {
            var src = original[r]; var dst = new Material[src.Length];
            for (int i = 0; i < src.Length; i++)
            {
                string n = src[i] ? src[i].name.Replace(" (Instance)", "") : "";
                if (map.TryGetValue(n, out var m)) dst[i] = m; else { dst[i] = src[i]; unmapped.Add(n); }
            }
            r.sharedMaterials = dst;
        }
    }

    var camGo = new GameObject("TT_UnityCam"); SceneManager.MoveGameObjectToScene(camGo, scene);
    var cam = camGo.AddComponent<Camera>();
    cam.orthographic = true; cam.cullingMask = 1 << 31; cam.clearFlags = CameraClearFlags.SolidColor;
    cam.backgroundColor = Color.white; cam.nearClipPlane = 0.01f; cam.farClipPlane = 10f; cam.enabled = false;
    void Shoot(string tag, int x0, int y0, int x1, int y1, float yaw)
    {
        int w = x1 - x0, h = y1 - y0;
        var rt = new RenderTexture(w, h, 24, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB) { antiAliasing = 4 };
        cam.targetTexture = rt; cam.aspect = (float)w / h; cam.orthographicSize = h / ppm / 2f;
        float cx = sx * (((x0 + x1) / 2f) - 1030f) / ppm, cy = zTop - ((y0 + y1) / 2f) / ppm;
        var pivot = new Vector3(0, cy, head.center.z);
        var dir = Quaternion.AngleAxis(sx * yaw, Vector3.up) * new Vector3(0, 0, front);   // orbit toward character left
        var right = Vector3.Cross(Vector3.up, -dir).normalized;
        cam.transform.position = pivot + dir * 3f + right * cx;
        cam.transform.rotation = Quaternion.LookRotation(-dir, Vector3.up);
        cam.Render();
        var prev = RenderTexture.active; RenderTexture.active = rt;
        var tex = new Texture2D(w, h, TextureFormat.RGB24, false); tex.ReadPixels(new Rect(0, 0, w, h), 0, 0); tex.Apply();
        RenderTexture.active = prev;
        File.WriteAllBytes(Path.Combine(outDir, tag + ".png"), tex.EncodeToPNG());
        cam.targetTexture = null; rt.Release(); Object.DestroyImmediate(rt); Object.DestroyImmediate(tex);
        log.Add("saved " + tag);
    }
    Apply(toon);
    Shoot("unity_hair4_face_front", 700, 0, 1360, 860, 0);
    Shoot("unity_hair4_face_34", 600, 0, 1460, 860, 35);
    Shoot("unity_hair4_face_side", 600, 0, 1460, 860, 90);
    Shoot("unity_hair4_face_back", 600, 0, 1460, 860, 180);
    log.Add("unmapped: " + string.Join(",", unmapped));
}
finally
{
    EditorSceneManager.CloseScene(scene, true);
    SceneManager.SetActiveScene(prevActive);
}
log.Add($"active after: {SceneManager.GetActiveScene().path} dirty {SceneManager.GetActiveScene().isDirty} scenes {SceneManager.sceneCount}");
return string.Join("\n", log);
