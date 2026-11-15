// Formal Race3D Android verify scene (EDIT mode). Creates Assets/_Experiments/Race3D_FormalVerify/FormalExprAndroidTest.unity only.
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

if (Application.isPlaying) return "run in edit mode";
const string Root = "Assets/_Experiments/Race3D_FormalVerify";
const string ScenePath = Root + "/FormalExprAndroidTest.unity";
if (!AssetDatabase.IsValidFolder(Root)) AssetDatabase.CreateFolder("Assets/_Experiments", "Race3D_FormalVerify");
var log = new List<string>();
var active = SceneManager.GetActiveScene();
AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
var type = System.AppDomain.CurrentDomain.GetAssemblies().Select(a => a.GetType("MMG.Experiments.Race3DFormal.FormalExprDeviceTest")).FirstOrDefault(t => t != null);
if (type == null) return "FormalExprDeviceTest type missing";
var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Additive);
try
{
    var go = new GameObject("FormalExprDeviceTest");
    SceneManager.MoveGameObjectToScene(go, scene);
    var c = go.AddComponent(type);
    var so = new SerializedObject(c);
    so.FindProperty("formalPrefab").objectReferenceValue =
        AssetDatabase.LoadAssetAtPath<GameObject>("Assets/_Game/Art/Characters/MainGirlfriend/Model3D/MainGirlfriend_Race3D_v1.prefab");
    so.FindProperty("perfSeconds").floatValue = 12f;
    so.FindProperty("soakSeconds").floatValue = 780f;
    so.ApplyModifiedPropertiesWithoutUndo();
    bool ok = EditorSceneManager.SaveScene(scene, ScenePath);
    log.Add($"scene {ScenePath} saved {ok}");
}
finally { EditorSceneManager.CloseScene(scene, true); }
log.Add($"active {SceneManager.GetActiveScene().path} dirty {SceneManager.GetActiveScene().isDirty}");
return string.Join("\n", log);
