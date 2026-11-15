// Race3D v3b expressions (Unity Editor, EDIT mode, Unity MCP script_eval_file; not compiled into the project).
// Experiment only: import settings of Assets/_Experiments/Race3D_v3b (FBX, sparkle textures), shader compile check and the
// scene Assets/_Experiments/Race3D_v3b/Race3DExprCheck.unity with the test driver Race3DExprCheck. The formal Model3D
// assets are only referenced (materials copied at run time); open scenes are not touched (the new scene is created
// additively, saved and closed).
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

if (Application.isPlaying) return "run in edit mode";
const string Root = "Assets/_Experiments/Race3D_v3b";
const string Fbx = Root + "/MainGirlfriend_Race3D_v3b_Expressions.fbx";
const string ScenePath = Root + "/Race3DExprCheck.unity";
var log = new List<string>();
var active = SceneManager.GetActiveScene();
log.Add($"active scene before {active.path} dirty {active.isDirty}");
AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
var mi = (ModelImporter)AssetImporter.GetAtPath(Fbx);
if (mi == null) return "missing " + Fbx;
mi.importBlendShapes = true; mi.importNormals = ModelImporterNormals.Import; mi.importBlendShapeNormals = ModelImporterNormals.Import;
mi.materialImportMode = ModelImporterMaterialImportMode.ImportStandard;
mi.importCameras = false; mi.importLights = false; mi.importAnimation = false;
mi.animationType = ModelImporterAnimationType.Generic;
mi.SaveAndReimport();
foreach (var s in new[] { "L", "R" })
{
    var ti = (TextureImporter)AssetImporter.GetAtPath($"{Root}/Textures/eye_sparkle_{s}.png");
    ti.textureType = TextureImporterType.Default; ti.sRGBTexture = true; ti.mipmapEnabled = false;
    ti.wrapMode = TextureWrapMode.Clamp; ti.filterMode = FilterMode.Bilinear; ti.alphaIsTransparency = false;
    ti.textureCompression = TextureImporterCompression.Uncompressed;
    ti.SaveAndReimport();
}
var shaders = new Dictionary<string, Shader>();
foreach (var n in new[] { "MMG/Experiments/EyeBallSparkle", "MMG/Experiments/ToonHairStencil", "MMG/Experiments/BrowCard", "MMG/Experiments/TearStream", "MMG/Character/Unlit" })
{
    var sh = Shader.Find(n);
    if (sh == null) return "missing shader " + n;
    if (ShaderUtil.ShaderHasError(sh)) return "shader error " + n + ": " + string.Join(" | ", ShaderUtil.GetShaderMessages(sh).Select(m => m.message));
    shaders[n] = sh;
}
var type = System.AppDomain.CurrentDomain.GetAssemblies().Select(a => a.GetType("MMG.Experiments.Race3DExpr.Race3DExprCheck")).FirstOrDefault(t => t != null);
if (type == null) return "driver type not compiled yet";
var model = AssetDatabase.LoadAssetAtPath<GameObject>(Fbx);
var mesh = model.GetComponentsInChildren<SkinnedMeshRenderer>(true);
log.Add($"fbx renderers {model.GetComponentsInChildren<Renderer>(true).Length}, skinned {mesh.Length}, blend shapes {mesh.Sum(m => m.sharedMesh.blendShapeCount)}");

var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Additive);
try
{
    var go = new GameObject("Race3DExprCheck");
    SceneManager.MoveGameObjectToScene(go, scene);
    var c = go.AddComponent(type);
    var so = new SerializedObject(c);
    so.FindProperty("model").objectReferenceValue = model;
    so.FindProperty("formalPrefab").objectReferenceValue = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/_Game/Art/Characters/MainGirlfriend/Model3D/MainGirlfriend_Race3D_v1.prefab");
    so.FindProperty("eyeSparkleShader").objectReferenceValue = shaders["MMG/Experiments/EyeBallSparkle"];
    so.FindProperty("hairStencilShader").objectReferenceValue = shaders["MMG/Experiments/ToonHairStencil"];
    so.FindProperty("browCardShader").objectReferenceValue = shaders["MMG/Experiments/BrowCard"];
    so.FindProperty("tearStreamShader").objectReferenceValue = shaders["MMG/Experiments/TearStream"];
    so.FindProperty("unlitShader").objectReferenceValue = shaders["MMG/Character/Unlit"];
    so.FindProperty("sparkleL").objectReferenceValue = AssetDatabase.LoadAssetAtPath<Texture2D>($"{Root}/Textures/eye_sparkle_L.png");
    so.FindProperty("sparkleR").objectReferenceValue = AssetDatabase.LoadAssetAtPath<Texture2D>($"{Root}/Textures/eye_sparkle_R.png");
    so.FindProperty("specJson").objectReferenceValue = AssetDatabase.LoadAssetAtPath<TextAsset>($"{Root}/Spec/race3d_v3b_unity_spec.json");
    so.FindProperty("outDir").stringValue = Path.GetFullPath("BlenderSource/Characters/MainGirlfriend/Models/Race3D/experiments/unity_v3b");
    so.ApplyModifiedPropertiesWithoutUndo();
    bool ok = EditorSceneManager.SaveScene(scene, ScenePath);
    log.Add($"scene {ScenePath} saved {ok}; null refs [{string.Join(",", new[] { "model", "formalPrefab", "sparkleL", "sparkleR", "specJson" }.Where(p => so.FindProperty(p).objectReferenceValue == null))}]");
}
finally
{
    EditorSceneManager.CloseScene(scene, true);
}
active = SceneManager.GetActiveScene();
log.Add($"active scene after {active.path} dirty {active.isDirty}");
return string.Join("\n", log);
