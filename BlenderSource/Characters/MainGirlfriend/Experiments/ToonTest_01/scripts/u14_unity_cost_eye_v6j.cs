// ToonTest_01 step 86 (Unity Editor, edit mode, run through the Unity MCP script_eval tool; not compiled into the project).
// Cost of the v6j view keys, v6f_A vs v6j FBX:
//   memory (measured in the Editor): Profiler.GetRuntimeMemorySizeLong per mesh with blend shapes, and per blend shape the
//          vertices with a non-zero delta (Unity keeps blend shapes sparse: index + position / normal / tangent delta)
//   CPU   (measured in the Editor): SkinnedMeshRenderer.BakeMesh of the eye meshes with no key / Blink / the view keys on
//          (CPU blend shape path, 2000 calls each), as a relative measure
// A temporary additive scene, closed without saving.
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Profiling;
using UnityEngine.SceneManagement;

const string Dir = "Assets/_Experiments/ToonTest_01";
var log = new List<string>();
log.Add($"gpuSkinning {PlayerSettings.gpuSkinning}, platform {EditorUserBuildSettings.activeBuildTarget}, device {SystemInfo.processorType}");
foreach (var tag in new[] { "v6f_A", "v6j" })
{
    var model = AssetDatabase.LoadAssetAtPath<GameObject>($"{Dir}/MG_ToonTest_01_{tag}_eye.fbx");
    var meshes = AssetDatabase.LoadAllAssetsAtPath($"{Dir}/MG_ToonTest_01_{tag}_eye.fbx").OfType<Mesh>().ToList();
    long total = 0, eyeTotal = 0;
    int shapes = 0;
    foreach (var m in meshes)
    {
        long sz = Profiler.GetRuntimeMemorySizeLong(m);
        total += sz;
        shapes += m.blendShapeCount;
        if (m.name.StartsWith("Eye_Lids") || m.name.StartsWith("Eye_Lash"))
        {
            eyeTotal += sz;
            var dv = new Vector3[m.vertexCount]; var dn = new Vector3[m.vertexCount]; var dt = new Vector3[m.vertexCount];
            var parts = new List<string>();
            for (int i = 0; i < m.blendShapeCount; i++)
            {
                m.GetBlendShapeFrameVertices(i, 0, dv, dn, dt);
                int nz = 0;
                for (int v = 0; v < m.vertexCount; v++)
                    if (dv[v].sqrMagnitude > 1e-14f || dn[v].sqrMagnitude > 1e-10f) nz++;
                parts.Add($"{m.GetBlendShapeName(i)}:{nz}");
            }
            log.Add($"{tag} {m.name}: verts {m.vertexCount}, memory {sz / 1024.0:F1} KB, shapes [{string.Join(" ", parts)}]");
        }
    }
    log.Add($"{tag}: meshes {meshes.Count}, blend shapes {shapes}, mesh memory {total / 1024.0:F1} KB (eye lids + lash {eyeTotal / 1024.0:F1} KB)");

    var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Additive);
    try
    {
        var go = (GameObject)Object.Instantiate(model);
        SceneManager.MoveGameObjectToScene(go, scene);
        var smrs = go.GetComponentsInChildren<SkinnedMeshRenderer>(true).Where(r => r.name.StartsWith("Eye_Lids") || r.name.StartsWith("Eye_Lash")).ToList();
        var bake = new Mesh();
        double Time(System.Action<SkinnedMeshRenderer> set)
        {
            foreach (var r in smrs) { for (int i = 0; i < r.sharedMesh.blendShapeCount; i++) r.SetBlendShapeWeight(i, 0); set(r); }
            foreach (var r in smrs) r.BakeMesh(bake);                          // warm up
            var sw = Stopwatch.StartNew();
            for (int k = 0; k < 2000; k++) foreach (var r in smrs) r.BakeMesh(bake);
            return sw.Elapsed.TotalMilliseconds * 1000.0 / 2000;               // us for all four eye meshes
        }
        void W(SkinnedMeshRenderer r, string n, float v) { int i = r.sharedMesh.GetBlendShapeIndex(n); if (i >= 0) r.SetBlendShapeWeight(i, v); }
        double none = Time(r => { });
        double blink = Time(r => W(r, "Blink", 50));
        double view = Time(r => { W(r, "ViewFarR", 60); W(r, "ViewFarR_GO", 40); W(r, "ViewSideR", 20); W(r, "ViewFarL", 60); W(r, "ViewFarL_GI", 40); W(r, "ViewSideL", 20); });
        double all = Time(r => { W(r, "Blink", 30); W(r, "EyeSmile", 20); W(r, "Surprise", 20); W(r, "ViewFarR", 60); W(r, "ViewFarR_GO", 40); W(r, "ViewSideR", 20); W(r, "ViewFarL", 60); W(r, "ViewFarL_GI", 40); W(r, "ViewSideL", 20); });
        log.Add($"{tag}: BakeMesh of the 4 eye meshes (us per frame): no key {none:F1}, Blink {blink:F1}, view keys {view:F1}, Blink+EyeSmile+Surprise+view {all:F1}");
        Object.DestroyImmediate(bake);
    }
    finally
    {
        EditorSceneManager.CloseScene(scene, true);
    }
}
return string.Join("\n", log);
