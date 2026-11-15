// Race3D v3b Android device test (Unity Editor, EDIT mode, script_eval_file). Creates only under
// Assets/_Experiments/Race3D_v3b/: HairBrowPullTable asset and Race3DExprAndroidTest.unity with Race3DExprDeviceTest.
// Formal Model3D / Mobile_RPAsset / open scenes are not modified.
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

if (Application.isPlaying) return "run in edit mode";
const string Root = "Assets/_Experiments/Race3D_v3b";
const string ScenePath = Root + "/Race3DExprAndroidTest.unity";
const string TablePath = Root + "/HairBrowPullTable_bob.asset";
var log = new List<string>();
var active = SceneManager.GetActiveScene();
log.Add($"active before {active.path} dirty {active.isDirty}");
AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);

var shaders = new Dictionary<string, Shader>();
foreach (var n in new[] { "MMG/Experiments/EyeBallSparkle", "MMG/Experiments/ToonHairStencil", "MMG/Experiments/BrowCard", "MMG/Experiments/TearStream", "MMG/Character/Unlit" })
{
    var sh = Shader.Find(n);
    if (sh == null) return "missing shader " + n;
    if (ShaderUtil.ShaderHasError(sh)) return "shader error " + n;
    shaders[n] = sh;
}
var type = System.AppDomain.CurrentDomain.GetAssemblies().Select(a => a.GetType("MMG.Experiments.Race3DExpr.Race3DExprDeviceTest")).FirstOrDefault(t => t != null);
var tableType = System.AppDomain.CurrentDomain.GetAssemblies().Select(a => a.GetType("MMG.Experiments.Race3DExpr.HairBrowPullTable")).FirstOrDefault(t => t != null);
if (type == null || tableType == null) return $"types missing device={type != null} table={tableType != null}";

var table = AssetDatabase.LoadAssetAtPath<ScriptableObject>(TablePath);
if (table == null)
{
    table = ScriptableObject.CreateInstance(tableType);
    var soT = new SerializedObject(table);
    soT.FindProperty("defaultPullMeters").floatValue = 0.03f;
    var entries = soT.FindProperty("entries");
    entries.arraySize = 1;
    entries.GetArrayElementAtIndex(0).FindPropertyRelative("hairItemId").stringValue = "hair_bob_01_01";
    entries.GetArrayElementAtIndex(0).FindPropertyRelative("pullMeters").floatValue = 0.03f;
    soT.ApplyModifiedPropertiesWithoutUndo();
    AssetDatabase.CreateAsset(table, TablePath);
    log.Add("created " + TablePath);
}

var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Additive);
try
{
    var go = new GameObject("Race3DExprDeviceTest");
    SceneManager.MoveGameObjectToScene(go, scene);
    var c = go.AddComponent(type);
    var so = new SerializedObject(c);
    so.FindProperty("modelPrefab").objectReferenceValue = AssetDatabase.LoadAssetAtPath<GameObject>(Root + "/MainGirlfriend_Race3D_v3b_Expressions.fbx");
    so.FindProperty("formalPrefab").objectReferenceValue = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/_Game/Art/Characters/MainGirlfriend/Model3D/MainGirlfriend_Race3D_v1.prefab");
    so.FindProperty("eyeSparkleShader").objectReferenceValue = shaders["MMG/Experiments/EyeBallSparkle"];
    so.FindProperty("hairStencilShader").objectReferenceValue = shaders["MMG/Experiments/ToonHairStencil"];
    so.FindProperty("browCardShader").objectReferenceValue = shaders["MMG/Experiments/BrowCard"];
    so.FindProperty("tearStreamShader").objectReferenceValue = shaders["MMG/Experiments/TearStream"];
    so.FindProperty("unlitShader").objectReferenceValue = shaders["MMG/Character/Unlit"];
    so.FindProperty("sparkleL").objectReferenceValue = AssetDatabase.LoadAssetAtPath<Texture2D>(Root + "/Textures/eye_sparkle_L.png");
    so.FindProperty("sparkleR").objectReferenceValue = AssetDatabase.LoadAssetAtPath<Texture2D>(Root + "/Textures/eye_sparkle_R.png");
    so.FindProperty("specJson").objectReferenceValue = AssetDatabase.LoadAssetAtPath<TextAsset>(Root + "/Spec/race3d_v3b_unity_spec.json");
    so.FindProperty("browPullTable").objectReferenceValue = table;
    so.FindProperty("perfSeconds").floatValue = 12f;
    so.ApplyModifiedPropertiesWithoutUndo();
    bool ok = EditorSceneManager.SaveScene(scene, ScenePath);
    log.Add($"scene {ScenePath} saved {ok}");
}
finally
{
    EditorSceneManager.CloseScene(scene, true);
}
active = SceneManager.GetActiveScene();
log.Add($"active after {active.path} dirty {active.isDirty}");
return string.Join("\n", log);
