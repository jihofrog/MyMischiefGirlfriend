// ToonTest_01 step 89 (Unity Editor, edit mode, script_eval; not compiled into the project): head vs lash depth in Unity
// at the speck points of /tmp/speck_pts.json (t03 pixels of the front left eye), and the FBX import settings that can move
// vertices. Temporary additive scene, closed without saving.
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

const string Dir = "Assets/_Experiments/ToonTest_01";
var log = new List<string>();
var path = $"{Dir}/MG_ToonTest_01_v6j_eye.fbx";
var mi = (ModelImporter)AssetImporter.GetAtPath(path);
log.Add($"import: meshCompression {mi.meshCompression}, weldVertices {mi.weldVertices}, optimizeMesh {mi.optimizeMeshVertices}/{mi.optimizeMeshPolygons}, " +
        $"indexFormat {mi.indexFormat}, globalScale {mi.globalScale}, useFileScale {mi.useFileScale}, normals {mi.importNormals}, smoothing {mi.normalSmoothingAngle}");
float headH = 0.4015944f, topZ = 1.650909f, ppm = 733f / headH, zTop = topZ + 21f / ppm;
var pts = Regex.Matches(File.ReadAllText("/tmp/speck_pts.json"), @"\[\s*([-0-9.eE]+)\s*,\s*([-0-9.eE]+)\s*\]")
    .Cast<Match>().Select(m => new Vector2(float.Parse(m.Groups[1].Value, System.Globalization.CultureInfo.InvariantCulture),
                                           float.Parse(m.Groups[2].Value, System.Globalization.CultureInfo.InvariantCulture))).ToList();
var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Additive);
try
{
    var go = (GameObject)Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>(path));
    SceneManager.MoveGameObjectToScene(go, scene);
    var rends = go.GetComponentsInChildren<Renderer>(true).ToList();
    Renderer R(string n) => rends.First(r => r.name == n);
    var head = R("Blockout_Head").bounds;
    float sx = Mathf.Sign(R("Eye_Ball.L").bounds.center.x);
    float front = Mathf.Sign(R("TT_Mouth_Closed").bounds.center.z - head.center.z);
    log.Add($"sx {sx} front {front}; head transform scale {R("Blockout_Head").transform.lossyScale}, lash scale {R("Eye_Lash.L").transform.lossyScale}");
    var cols = new Dictionary<string, MeshCollider>();
    foreach (var n in new[] { "Blockout_Head", "Eye_Lash.L", "Eye_Lids.L" })
    {
        var smr = (SkinnedMeshRenderer)R(n);
        var m = new Mesh();
        smr.BakeMesh(m, true);
        var c = new GameObject(n + "_col");
        SceneManager.MoveGameObjectToScene(c, scene);
        c.transform.SetPositionAndRotation(smr.transform.position, smr.transform.rotation);
        var mc = c.AddComponent<MeshCollider>(); mc.sharedMesh = m;
        cols[n] = mc;
    }
    Physics.SyncTransforms();
    var gaps = new List<float>();
    foreach (var p in pts)
    {
        float x = (p.x - 1030f) / ppm, z = zTop - p.y / ppm;            // Blender x, z
        var origin = new Vector3(sx * x, z, front * 2f);
        var dir = new Vector3(0, 0, -front);
        float Hit(string n) => cols[n].Raycast(new Ray(origin, dir), out var h, 5f) ? h.distance : float.NaN;
        float dh = Hit("Blockout_Head"), dl = Hit("Eye_Lash.L");
        if (!float.IsNaN(dh) && !float.IsNaN(dl)) gaps.Add((dh - dl) * 1000f);
    }
    gaps.Sort();
    log.Add($"Unity gap head - lash (mm, + = lash in front), n {gaps.Count}: min {gaps.FirstOrDefault():F3}, median {(gaps.Count > 0 ? gaps[gaps.Count / 2] : 0):F3}, first [{string.Join(" ", gaps.Take(12).Select(g => g.ToString("F2")))}]");
}
finally
{
    EditorSceneManager.CloseScene(scene, true);
}
return string.Join("\n", log);
