// Formal Race3D v1 expression Editor verify (EDIT→Play via MCP separately). Instantiates the formal prefab twice,
// drives Happy/Angry/Angry2/Sad/Cry/Surprise + angles, checks material isolation and Angry conflict rule.
// Writes Spec/editor_verify_log.txt. Does not save scenes.
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

if (Application.isPlaying) return "stop play mode first";
const string PrefabPath = "Assets/_Game/Art/Characters/MainGirlfriend/Model3D/MainGirlfriend_Race3D_v1.prefab";
const string OutPath = "Assets/_Game/Art/Characters/MainGirlfriend/Model3D/Spec/editor_verify_log.txt";
var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath);
if (prefab == null) return "missing prefab";
var exprType = System.AppDomain.CurrentDomain.GetAssemblies().Select(a => a.GetType("MMG.Characters.Avatar3D.ExpressionController")).FirstOrDefault(t => t != null);
var eyeType = System.AppDomain.CurrentDomain.GetAssemblies().Select(a => a.GetType("MMG.Characters.Avatar3D.EyeViewController")).FirstOrDefault(t => t != null);
if (exprType == null || eyeType == null) return "types missing";

var sb = new StringBuilder();
void L(string s) { sb.AppendLine(s); Debug.Log("[FormalExprVerify] " + s); }

var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Additive);
try
{
    var camGo = new GameObject("VerifyCam") { tag = "MainCamera" };
    var cam = camGo.AddComponent<Camera>();
    cam.clearFlags = CameraClearFlags.SolidColor;
    cam.backgroundColor = new Color(0.93f, 0.93f, 0.95f);
    SceneManager.MoveGameObjectToScene(camGo, scene);

    GameObject Spawn(string name, Vector3 pos)
    {
        var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab, scene);
        go.name = name; go.transform.position = pos;
        return go;
    }
    var a = Spawn("A", new Vector3(-0.35f, 0, 0));
    var b = Spawn("B", new Vector3(0.35f, 0, 0));
    var ea = (MonoBehaviour)a.GetComponent(exprType);
    var eb = (MonoBehaviour)b.GetComponent(exprType);
    var eyeA = (MonoBehaviour)a.GetComponent(eyeType);
    if (ea == null || eb == null || eyeA == null) return "components missing on prefab";

    // call Build via reflection if needed
    exprType.GetMethod("Build")?.Invoke(ea, null);
    exprType.GetMethod("Build")?.Invoke(eb, null);

    object St(float happy = 0, float angry = 0, float angry2 = 0, float sad = 0, float cry = 0, float surprise = 0, float blink = 0, float gaze = 0, float flow = -1)
        => exprType.GetMethod("St").Invoke(null, new object[] { happy, angry, angry2, sad, cry, surprise, blink, gaze, flow });

    void SetState(MonoBehaviour c, object st)
    {
        var f = exprType.GetField("state");
        f.SetValue(c, st);
        exprType.GetMethod("Compose")?.Invoke(c, null);
    }

    // Angry conflict: both 1 → weak suppressed
    var resolve = exprType.GetMethod("ResolveConflict");
    object[] args = { St(angry: 1, angry2: 1), 0f, 0f };
    // ResolveConflict(State g, out float weak, out float strong) — use dynamic via typed call
    var stBoth = St(angry: 1f, angry2: 1f);
    // invoke with outs via typed helper
    var m = exprType.GetMethod("ResolveConflict");
    object[] rargs = new object[] { stBoth, 0f, 0f };
    m.Invoke(null, rargs);
    float weak = (float)rargs[1], strong = (float)rargs[2];
    bool conflictOk = Mathf.Abs(weak) < 1e-5f && Mathf.Abs(strong - 1f) < 1e-5f;
    L($"CONFLICT Angry+Angry2 -> weak={weak:F3} strong={strong:F3} ok={conflictOk}");

    SetState(ea, St(surprise: 1, gaze: 0.25f));
    SetState(eb, St(sad: 1, cry: 1, flow: 1));
    // different pull overrides
    exprType.GetField("browPullOverride").SetValue(ea, 0.03f);
    exprType.GetField("browPullOverride").SetValue(eb, 0.045f);
    exprType.GetMethod("Compose").Invoke(ea, null);
    exprType.GetMethod("Compose").Invoke(eb, null);
    float s0 = (float)exprType.GetProperty("Sparkle").GetValue(ea);
    float s1 = (float)exprType.GetProperty("Sparkle").GetValue(eb);
    float f0 = (float)exprType.GetProperty("Flow").GetValue(ea);
    float f1 = (float)exprType.GetProperty("Flow").GetValue(eb);
    float p0 = (float)exprType.GetProperty("BrowPullMeters").GetValue(ea);
    float p1 = (float)exprType.GetProperty("BrowPullMeters").GetValue(eb);
    var mats0 = (System.Collections.IList)exprType.GetProperty("OwnedMaterials").GetValue(ea);
    var mats1 = (System.Collections.IList)exprType.GetProperty("OwnedMaterials").GetValue(eb);
    bool iso = s0 > 0.9f && s1 < 0.05f && f0 < 0.05f && f1 > 0.9f
               && Mathf.Abs(p0 - 0.03f) < 1e-4f && Mathf.Abs(p1 - 0.045f) < 1e-4f
               && !object.ReferenceEquals(mats0[0], mats1[0]);
    L($"ISOLATION ok={iso} A sparkle={s0:F2} flow={f0:F2} pull={p0:F3}; B sparkle={s1:F2} flow={f1:F2} pull={p1:F3}");

    // Happy stages + viewSuppress
    SetState(ea, St(happy: 0.8f));
    float vs = (float)eyeType.GetField("viewSuppress").GetValue(eyeA);
    L($"Happy0.8 viewSuppress={vs:F3} (expect ~0.8)");

    // BlendShape channel count
    int channels = a.GetComponentsInChildren<SkinnedMeshRenderer>(true).Sum(s => s.sharedMesh != null ? s.sharedMesh.blendShapeCount : 0);
    L($"blendshape_channels={channels} (expect 137)");

    // EyeView owns Blink write path when linked
    SetState(ea, St(blink: 1, surprise: 1));
    var lids = a.GetComponentsInChildren<SkinnedMeshRenderer>(true).First(s => s.name == "Eye_Lids.L");
    int blinkIdx = -1, exSurp = -1;
    for (int i = 0; i < lids.sharedMesh.blendShapeCount; i++)
    {
        if (lids.sharedMesh.GetBlendShapeName(i) == "Blink") blinkIdx = i;
        if (lids.sharedMesh.GetBlendShapeName(i) == "ExSurprise") exSurp = i;
    }
    // EyeView may not have composed yet (needs play/loop). Expression should leave Blink for EyeView; ExSurprise should be 0 when blink=1
    float exS = lids.GetBlendShapeWeight(exSurp);
    L($"blink1 ExSurprise weight={exS:F2} (expect 0); blinkIdx={blinkIdx}");

    bool ok = conflictOk && iso && channels == 137 && Mathf.Abs(vs - 0.8f) < 0.01f && exS < 1f;
    L($"EDITOR_VERIFY ok={ok}");
    File.WriteAllText(Path.GetFullPath(OutPath), sb.ToString());
    AssetDatabase.Refresh();
    return sb.ToString();
}
finally
{
    EditorSceneManager.CloseScene(scene, true);
}
