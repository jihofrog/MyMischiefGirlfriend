// ToonTest_01 step 39 (Unity Editor, run through the Unity MCP script_eval tool; not compiled into the project).
// v6d check: MG_ToonTest_01_{v6c,v6d_3}_eye.fbx in a temporary additive scene (layer 31 only), same cameras as t26:
// faces (front / 3/4 / 60 / side), eye close ups (front / 3/4 / 60 / side), no-hair 60 / side, eye poses (Neutral,
// Blink 50 %, Blink, EyeSmile, Smile + EyeSmile, Surprise). v6d_3 eyeball: MMGExp/AnimeToonEyeV6d (socket AO through UV0,
// side-view dimming). Saves renders/unity_<tag>_eye_*.png and closes the scene without saving.
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
var log = new List<string>();
AssetDatabase.Refresh();
foreach (var t in new[] { "v6c", "v6d_3" })
{
    var mi = (ModelImporter)AssetImporter.GetAtPath($"{Dir}/MG_ToonTest_01_{t}_eye.fbx");
    bool dirty = !mi.importBlendShapes || mi.importNormals != ModelImporterNormals.Import || mi.importBlendShapeNormals != ModelImporterNormals.Import
                 || mi.materialImportMode != ModelImporterMaterialImportMode.ImportStandard;
    mi.importBlendShapes = true; mi.importNormals = ModelImporterNormals.Import; mi.importBlendShapeNormals = ModelImporterNormals.Import;
    mi.materialImportMode = ModelImporterMaterialImportMode.ImportStandard;
    if (dirty) mi.SaveAndReimport();
}
foreach (var n in new[] { "eye_tex_ball_L", "eye_tex_ball_R", "eye_tex_lash_L", "eye_tex_lash_R", "eye_tex_lash_v6c_L", "eye_tex_lash_v6c_R" })
{
    var ti = (TextureImporter)AssetImporter.GetAtPath($"{Dir}/{n}.png");
    if (ti.wrapMode != TextureWrapMode.Clamp || !ti.alphaIsTransparency) { ti.wrapMode = TextureWrapMode.Clamp; ti.alphaIsTransparency = true; ti.SaveAndReimport(); }
}
foreach (var n in new[] { "eye_tex_ball_v6d_L", "eye_tex_ball_v6d_R" })       // alpha = AO, colour must stay as painted
{
    var ti = (TextureImporter)AssetImporter.GetAtPath($"{Dir}/{n}.png");
    if (ti.wrapMode != TextureWrapMode.Clamp || ti.alphaIsTransparency) { ti.wrapMode = TextureWrapMode.Clamp; ti.alphaIsTransparency = false; ti.SaveAndReimport(); }
}
AssetDatabase.Refresh();
var shToon = Shader.Find("MMGExp/AnimeToonV6"); var shHair = Shader.Find("MMGExp/AnimeToonHairV2");
var shEye = Shader.Find("MMGExp/AnimeToonEye"); var shUnlit = Shader.Find("MMGExp/UnlitTex"); var shEyeC = Shader.Find("MMGExp/AnimeToonEyeV6c"); var shEyeD = Shader.Find("MMGExp/AnimeToonEyeV6d");
var irisOld = AssetDatabase.LoadAssetAtPath<Texture2D>(Dir + "/tex_iris_R.png");
if (shToon == null || shHair == null || shEye == null || shUnlit == null || shEyeC == null || shEyeD == null) return $"missing shader {shToon != null} {shHair != null} {shEye != null} {shUnlit != null}";
string projJson = File.ReadAllText(Path.Combine(exp, "spec", "eye_v6b_unity_proj.json"));
Vector4 Proj(string side)
{
    var m = Regex.Match(projJson, "\"" + side + "\"\\s*:\\s*\\{([^}]*)\\}");
    float G(string k) => float.Parse(Regex.Match(m.Groups[1].Value, "\"" + k + "\"\\s*:\\s*([-0-9.eE]+)").Groups[1].Value, System.Globalization.CultureInfo.InvariantCulture);
    return new Vector4(G("su"), G("tu"), G("sv"), G("tv"));
}
float headH = 0.4015944f, topZ = 1.650909f, ppm = 733f / headH, zTop = topZ + 21f / ppm;
Color C(int r, int g, int b) => new Color(r / 255f, g / 255f, b / 255f, 1);
var prevActive = SceneManager.GetActiveScene();
foreach (var tag in new[] { "v6c", "v6d_3" })
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
        var head = R("Blockout_Head").bounds; var eyeL = (R("Eye_White.L") ?? R("Eye_Ball.L")).bounds;
        float sx = Mathf.Sign(eyeL.center.x);                                     // Blender +X (character left) -> Unity sx * X
        float front = Mathf.Sign(R("TT_Mouth_Closed").bounds.center.z - head.center.z);
        Vector3 lightB = new Vector3(-0.296f, -0.814f, 0.5f);
        Vector3 lightU = new Vector3(sx * lightB.x, lightB.z, (lightB.y < 0 ? front : -front) * Mathf.Abs(lightB.y));
        // blend shapes
        var smrs = go.GetComponentsInChildren<SkinnedMeshRenderer>(true);
        int total = 0; var names = new SortedSet<string>();
        foreach (var smr in smrs) for (int i = 0; i < smr.sharedMesh.blendShapeCount; i++) { total++; names.Add(smr.sharedMesh.GetBlendShapeName(i)); }
        log.Add($"{tag}: renderers {rends.Count}, skinned {smrs.Length}, blend shapes {total} ({string.Join(",", names)})");
        log.Add($"{tag}: per mesh " + string.Join("; ", smrs.Select(s => s.name + "=" + string.Join("/", Enumerable.Range(0, s.sharedMesh.blendShapeCount).Select(i => s.sharedMesh.GetBlendShapeName(i))))));
        int tris = rends.Where(r => r.name.StartsWith("Eye_") || r.name.Contains("Lashes")).Sum(r => (r is SkinnedMeshRenderer s ? s.sharedMesh : r.GetComponent<MeshFilter>().sharedMesh).triangles.Length / 3);
        log.Add($"{tag}: eye meshes {rends.Count(r => r.name.StartsWith("Eye_") || r.name.Contains("Lashes"))}, tris {tris}, head tris {(R("Blockout_Head") is SkinnedMeshRenderer hs ? hs.sharedMesh : R("Blockout_Head").GetComponent<MeshFilter>().sharedMesh).triangles.Length / 3}");

        Material Toon(Color sh, Color mid, Color bas, Color lit, Color line, float width)
        {
            var m = new Material(shToon);
            m.SetColor("_ShadowColor", sh); m.SetColor("_MidColor", mid); m.SetColor("_BaseColor", bas); m.SetColor("_LightColor", lit);
            m.SetColor("_OutlineColor", line); m.SetFloat("_OutlineWidth", width); m.SetVector("_LightDir", lightU);
            return m;
        }
        Material Unlit(Color c, Texture tex = null, int queue = 3002)
        { var m = new Material(shUnlit); m.SetColor("_BaseColor", c); if (tex) m.SetTexture("_BaseMap", tex); m.renderQueue = queue; return m; }
        Material Eye(int mode, Color c, Texture tex = null, bool clip = false, Vector4? proj = null, float lo = 0.8f, float mid = 0.93f)
        {
            var m = new Material(shEye); m.SetFloat("_Mode", mode); m.SetColor("_BaseColor", c); if (tex) m.SetTexture("_BaseMap", tex);
            m.SetFloat("_Clip", clip ? 1 : 0); m.SetVector("_LightDir", lightU); m.SetFloat("_LitLo", lo); m.SetFloat("_LitMid", mid);
            if (proj.HasValue) m.SetVector("_Proj", proj.Value);
            return m;
        }
        var blushTex = new Texture2D(64, 64, TextureFormat.RGBA32, false);
        for (int y = 0; y < 64; y++) for (int x = 0; x < 64; x++)
        {
            float dx = (x - 31.5f) / 32f, dy = (y - 31.5f) / 32f * 1.6f; float a = Mathf.Clamp01(1 - Mathf.Sqrt(dx * dx + dy * dy)) * 0.42f;
            blushTex.SetPixel(x, y, new Color(1, 1, 1, a));
        }
        blushTex.Apply();
        Texture2D Tex(string n) => AssetDatabase.LoadAssetAtPath<Texture2D>($"{Dir}/{n}.png");
        var lit = tag == "v6a";
        Color dark = C(45, 20, 18);
        var map = new Dictionary<string, Material>
        {
            ["TT_Skin"] = Toon(C(238, 172, 150), C(252, 195, 176), C(253, 208, 189), C(254, 225, 209), C(150, 88, 70), 0.0011f),
            ["TT_Clip"] = Toon(C(205, 196, 200), C(205, 196, 200), C(242, 231, 233), C(242, 231, 233), C(66, 30, 26), 0.0016f),
            ["TT_MG_Face_Brow"] = Unlit(C(120, 66, 56)), ["TT_Mouth_Line"] = Unlit(C(176, 84, 76)), ["TT_Nose_Dot"] = Unlit(C(240, 186, 168)),
            ["TT_Blush_Radial"] = Unlit(C(248, 160, 150), blushTex, 3003),
            ["TT_MG_Face_MouthInside"] = Unlit(C(150, 60, 60), null, 3000), ["TT_MG_Face_Teeth"] = Unlit(C(250, 248, 248), null, 3001),
            ["TT_MG_Face_Tongue"] = Unlit(C(230, 120, 120), null, 3001), ["TT_MG_Face_LipLine"] = Unlit(C(150, 70, 62), null, 3002),
            ["TT_MG_Eye_White"] = lit ? Eye(2, C(250, 246, 246)) : Unlit(C(250, 246, 246), null, 3000),
            ["TT_Eye_Iris"] = lit ? Eye(0, Color.white, irisOld, true) : Unlit(Color.white, irisOld, 3001),
            ["TT_MG_Eye_Lash"] = lit ? Eye(2, dark, null, false, null, 0.85f, 0.95f) : Unlit(dark),
            ["TT_MG_Eye_UpperLid"] = lit ? Eye(2, dark, null, false, null, 0.85f, 0.95f) : Unlit(dark),
            ["TT_MG_Eye_OuterLine"] = lit ? Eye(2, dark, null, false, null, 0.85f, 0.95f) : Unlit(dark),
            ["TT_MG_Face_Lash"] = lit ? Eye(2, dark, null, false, null, 0.85f, 0.95f) : Unlit(dark),
            ["TT_MG_Eye_LowerLid"] = Unlit(C(120, 60, 52)), ["TT_MG_Eye_Crease"] = Unlit(C(150, 85, 72)), ["TT_MG_Face_LowerLash"] = Unlit(C(90, 45, 40)),
            ["MG6_EyeBall_L"] = Eye(1, Color.white, Tex("eye_tex_ball_L"), false, Proj("L")),
            ["MG6_EyeBall_R"] = Eye(1, Color.white, Tex("eye_tex_ball_R"), false, Proj("R")),
            ["MG6_Lash_L"] = Eye(0, Color.white, Tex("eye_tex_lash_L"), true, null, 0.85f, 0.95f),
            ["MG6_Lash_R"] = Eye(0, Color.white, Tex("eye_tex_lash_R"), true, null, 0.85f, 0.95f),
        };
        foreach (var side in new[] { "L", "R" })
        {
            var m = new Material(shEyeC); m.SetFloat("_Mode", 0); m.SetColor("_BaseColor", Color.white); m.SetTexture("_BaseMap", Tex($"eye_tex_lash_v6c_{side}"));
            m.SetFloat("_A2C", 1); m.SetVector("_LightDir", lightU); m.SetFloat("_LitLo", 0.85f); m.SetFloat("_LitMid", 0.95f);
            map[$"MG6c_Lash_{side}"] = m;
            var d = new Material(shEyeD); d.SetFloat("_Mode", 1); d.SetColor("_BaseColor", Color.white); d.SetTexture("_BaseMap", Tex($"eye_tex_ball_v6d_{side}"));
            d.SetFloat("_UseAO", 1); d.SetFloat("_ViewDim", 0.10f); d.SetFloat("_HLDim", 0.20f); d.SetVector("_LightDir", lightU);
            d.SetFloat("_LitLo", 0.8f); d.SetFloat("_LitMid", 0.93f); d.SetVector("_Proj", Proj(side));
            map[$"MG6d_EyeBall_{side}"] = d;
        }
        var hairMat = new Material(shHair);
        hairMat.SetColor("_HairColor", C(124, 68, 59)); hairMat.SetColor("_OutlineColor", C(66, 30, 26)); hairMat.SetVector("_LightDir", lightU);
        map["M_hair_bob_01_01"] = hairMat; map["M_acc_head_hairclip_x_01_01"] = map["TT_Clip"];
        var unmapped = new HashSet<string>();
        foreach (var r in rends)
        {
            var src = r.sharedMaterials; var dst = new Material[src.Length];
            for (int i = 0; i < src.Length; i++)
            {
                string n = src[i] ? src[i].name.Replace(" (Instance)", "") : "";
                if (map.TryGetValue(n, out var m)) dst[i] = m; else { dst[i] = src[i]; unmapped.Add(n); }
            }
            r.sharedMaterials = dst;
        }
        log.Add($"{tag}: unmapped {string.Join(",", unmapped)}");
        var hair = rends.Where(r => r.name.StartsWith("hair_bob_01") || r.name.StartsWith("acc_head")).ToList();
        var mouthOpen = rends.Where(r => r.name.StartsWith("Face_Mouth_Smile")).ToList();
        Renderer closedMouth = R("TT_Mouth_Closed");
        // edit-mode camera renders do not run the skinning update: each pose is baked (SkinnedMeshRenderer.BakeMesh, the
        // blend shapes as imported) into a plain mesh drawn in place of the skinned renderer
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
        void Keys(string key, float w)
        {
            var on = key.Split('+');
            foreach (var smr in smrs)
            {
                for (int i = 0; i < smr.sharedMesh.blendShapeCount; i++)
                    smr.SetBlendShapeWeight(i, System.Array.IndexOf(on, smr.sharedMesh.GetBlendShapeName(i)) >= 0 ? w : 0f);
                smr.BakeMesh(baked[smr]);
                baked[smr].RecalculateBounds();                                     // BakeMesh leaves empty bounds (culled)
            }
            foreach (var r in mouthOpen) r.enabled = key == "MouthOpen";
            closedMouth.enabled = key != "MouthOpen";
        }
        var irisPos = new Dictionary<Renderer, Vector3>();
        foreach (var r in rends.Where(r => r.name.StartsWith("Eye_Iris"))) irisPos[r] = r.transform.position;
        void Gaze(float rad)
        {
            foreach (var m in new[] { map["MG6_EyeBall_L"], map["MG6_EyeBall_R"] }) m.SetFloat("_GazeYaw", rad);
            foreach (var kv in irisPos) kv.Key.transform.position = kv.Value + new Vector3(sx * rad * 0.09f, 0, 0);
        }

        var camGo = new GameObject("TT_UnityCam"); SceneManager.MoveGameObjectToScene(camGo, scene);
        var cam = camGo.AddComponent<Camera>();
        cam.orthographic = true; cam.cullingMask = 1 << 31; cam.clearFlags = CameraClearFlags.SolidColor;
        cam.backgroundColor = Color.white; cam.nearClipPlane = 0.01f; cam.farClipPlane = 10f; cam.enabled = false;
        void Shoot(string name, int x0, int y0, int x1, int y1, float yaw, float scale = 1f, float jx = 0f, float jy = 0f)
        {
            int w = x1 - x0, h = y1 - y0, W = (int)(w * scale), H = (int)(h * scale);
            var rt = new RenderTexture(W, H, 24, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB) { antiAliasing = 4 };
            cam.targetTexture = rt; cam.aspect = (float)w / h; cam.orthographicSize = h / ppm / 2f;
            float cx = (((x0 + x1) / 2f) - 1030f) / ppm, cy = zTop - ((y0 + y1) / 2f) / ppm;   // camera right already points to the character's left (u01-u04 mirrored off-centre boxes)
            var pivot = new Vector3(0, cy, -0.03f * front);                         // t03 orbits about Blender (x 0, y 0.03)
            var dir = Quaternion.AngleAxis(sx * yaw, Vector3.up) * new Vector3(0, 0, front);
            var right = Vector3.Cross(Vector3.up, -dir).normalized;
            cam.transform.position = pivot + dir * 3f + right * (cx + jx / ppm) - Vector3.up * (jy / ppm);
            cam.transform.rotation = Quaternion.LookRotation(-dir, Vector3.up);
            cam.Render();
            var prev = RenderTexture.active; RenderTexture.active = rt;
            var tex = new Texture2D(W, H, TextureFormat.RGB24, false); tex.ReadPixels(new Rect(0, 0, W, H), 0, 0); tex.Apply();
            RenderTexture.active = prev;
            File.WriteAllBytes(Path.Combine(outDir, $"unity_{tag}_eye_{name}.png"), tex.EncodeToPNG());
            cam.targetTexture = null; rt.Release(); Object.DestroyImmediate(rt); Object.DestroyImmediate(tex);
        }
        Keys("", 0); Gaze(0);
        Shoot("face_front", 700, 0, 1360, 860, 0);
        Shoot("face_34", 600, 0, 1460, 860, 35);
        Shoot("face_60", 600, 0, 1460, 860, 60);
        Shoot("face_side", 600, 0, 1460, 860, 90);
        Shoot("zoom_front", 780, 400, 1280, 600, 0, 2f);
        Shoot("zoom_34", 700, 340, 1300, 660, 35, 1.6f);
        Shoot("zoom_60", 700, 340, 1300, 660, 60, 1.6f);
        Shoot("zoom_side", 600, 340, 1000, 596, 90, 2f);
        foreach (var k in new[] { "", "Blink", "Blink50", "EyeSmile", "Smile+EyeSmile", "Surprise" })
        {
            string nm = k == "" ? "neutral" : k.Replace("+", "");
            if (k == "Blink50") Keys("Blink", 50); else Keys(k, 100);
            Shoot($"expr_{nm}", 780, 380, 1280, 720, 0, 1.2f);
            Shoot($"expr34_{nm}", 700, 340, 1300, 660, 35, 1.2f);
        }
        Keys("", 0);
        foreach (var r in hair) r.enabled = false;
        Shoot("nohair_front", 600, 200, 1460, 760, 0);
        Shoot("nohair_34_L", 600, 200, 1460, 760, 35);
        Shoot("nohair_60_L", 600, 200, 1460, 760, 60);
        Shoot("nohair_side_L", 600, 200, 1460, 760, 90);
        foreach (var r in hair) r.enabled = true;
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
