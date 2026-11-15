using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using Avatar3DEye = MMG.Characters.Avatar3D.EyeViewController;
using Avatar3DLoop = MMG.Characters.Avatar3D.EyeViewLoop;

namespace MMG.Experiments.EyeView
{
    /// <summary>
    /// Play mode check of the Race3D v1 prefab against the device-tested v6j prefab: the same shots (front, +-35, +-45,
    /// Blink, EyeSmile, gaze) rendered through the real player loop into 1080 x 2340 RenderTextures (MSAA 4) and saved to
    /// &lt;persistentDataPath&gt;/race3dcheck/&lt;tag&gt;_&lt;shot&gt;.png. Materials are instanced per character so no asset changes.
    /// </summary>
    public sealed class Race3DCheck : MonoBehaviour
    {
        public GameObject experimentPrefab;
        public GameObject race3dPrefab;
        public Vector3 lightLocal = new Vector3(0.296f, 0.5f, 0.814f);

        const int CapW = 1080, CapH = 2340;
        string dir;
        Camera cam;
        UniversalRenderPipelineAsset urp;
        int origMsaa = 1;
        float origScale = 1f;
        readonly List<string> log = new List<string>();

        void Log(string s)
        {
            Debug.Log("[Race3DCheck] " + s);
            log.Add(s);
            File.WriteAllLines(Path.Combine(dir, "log.txt"), log);
        }

        void OnDestroy()
        {
            if (urp != null) { urp.msaaSampleCount = origMsaa; urp.renderScale = origScale; }
        }

        IEnumerator Start()
        {
            dir = Path.Combine(Application.persistentDataPath, "race3dcheck");
            Directory.CreateDirectory(dir);
            urp = GraphicsSettings.currentRenderPipeline as UniversalRenderPipelineAsset;
            if (urp != null) { origMsaa = urp.msaaSampleCount; origScale = urp.renderScale; urp.msaaSampleCount = 4; urp.renderScale = 1f; }
            var go = new GameObject("Race3DCheckCam");
            cam = go.AddComponent<Camera>();
            cam.clearFlags = CameraClearFlags.SolidColor;
            cam.backgroundColor = new Color(0.93f, 0.93f, 0.95f);
            cam.nearClipPlane = 0.02f;
            cam.farClipPlane = 50f;
            cam.allowMSAA = true;
            foreach (var (tag, prefab) in new[] { ("v6j", experimentPrefab), ("race3d_v1", race3dPrefab) })
                yield return Shoot(tag, prefab);
            Log($"Avatar3D loop installed {Avatar3DLoop.IsInstalled()} after {Avatar3DLoop.InsertedAfter} before {Avatar3DLoop.InsertedBefore}; active {Avatar3DLoop.ActiveCount}");
            Log("ALL_DONE");
        }

        IEnumerator Shoot(string tag, GameObject prefab)
        {
            var go = Instantiate(prefab);
            var mats = new List<Material>();
            foreach (var r in go.GetComponentsInChildren<Renderer>(true)) mats.AddRange(r.materials);    // instances
            var eyeMats = mats.Where(m => m.HasProperty("_GazeYaw")).ToList();
            System.Action<float, float, float> inputs;
            Transform eyeL, eyeR;
            Vector3 fwdLocal, leftLocal;
            System.Func<string> state;
            var exp = go.GetComponent<EyeViewController>();
            if (exp != null)
            {
                exp.viewCamera = cam; exp.eyeMaterials = eyeMats;
                inputs = (b, e, g) => { exp.blink = b; exp.eyeSmile = e; exp.gaze = g; };
                eyeL = exp.eyeL; eyeR = exp.eyeR; fwdLocal = exp.faceForwardLocal; leftLocal = exp.characterLeftLocal;
                state = () => $"farL {exp.FarL:F2} farR {exp.FarR:F2} sideL {exp.SideL:F2} sideR {exp.SideR:F2} composed f{exp.ComposedFrame} fallback {exp.FallbackComposes} foreign {exp.ForeignWrites}";
            }
            else
            {
                var f = go.GetComponent<Avatar3DEye>();
                f.viewCamera = cam; f.eyeMaterials = eyeMats;
                inputs = (b, e, g) => { f.blink = b; f.eyeSmile = e; f.gaze = g; };
                eyeL = f.eyeL; eyeR = f.eyeR; fwdLocal = f.faceForwardLocal; leftLocal = f.characterLeftLocal;
                state = () => $"farL {f.FarL:F2} farR {f.FarR:F2} sideL {f.SideL:F2} sideR {f.SideR:F2} composed f{f.ComposedFrame} fallback {f.FallbackComposes} foreign {f.ForeignWrites} registered {f.Registered}";
            }
            float sx = Mathf.Sign(Vector3.Dot(leftLocal, Vector3.right)), front = Mathf.Sign(fwdLocal.z);
            var shots = new (string n, float yaw, float width, float blink, float es, float gaze)[]
            {
                ("front_eye", 0, 0.36f, 0, 0, 0), ("front_face", 0, 0.62f, 0, 0, 0),
                ("far35R_eye", 35, 0.36f, 0, 0, 0), ("far35L_eye", -35, 0.36f, 0, 0, 0),
                ("far45R_eye", 45, 0.36f, 0, 0, 0), ("far45L_eye", -45, 0.36f, 0, 0, 0),
                ("blink0_eye", 0, 0.36f, 1, 0, 0), ("blink35_eye", 35, 0.36f, 1, 0, 0), ("blink50_35_eye", 35, 0.36f, 0.5f, 0, 0),
                ("eyesmile0_eye", 0, 0.36f, 0, 1, 0), ("eyesmile35_eye", 35, 0.36f, 0, 1, 0),
                ("gazeL0_eye", 0, 0.36f, 0, 0, 0.25f), ("gazeR0_eye", 0, 0.36f, 0, 0, -0.25f),
                ("gazeL35_eye", 35, 0.36f, 0, 0, 0.25f), ("gazeR35_eye", 35, 0.36f, 0, 0, -0.25f),
                ("face35", 35, 0.62f, 0, 0, 0), ("face_35", -35, 0.62f, 0, 0, 0),
            };
            foreach (var s in shots)
            {
                inputs(s.blink, s.es, s.gaze);
                Vector3 pivot = (eyeL.position + eyeR.position) * 0.5f;
                Vector3 dirv = Quaternion.AngleAxis(sx * s.yaw, Vector3.up) * new Vector3(0, 0, front);
                const float dist = 0.7f;
                cam.transform.position = pivot + dirv * dist;
                cam.transform.rotation = Quaternion.LookRotation(-dirv, Vector3.up);
                float h = 2f * Mathf.Atan(s.width * 0.5f / dist);
                cam.fieldOfView = 2f * Mathf.Atan(Mathf.Tan(h * 0.5f) / ((float)CapW / CapH)) * Mathf.Rad2Deg;
                Vector3 lw = Quaternion.AngleAxis(sx * s.yaw, Vector3.up) * lightLocal;
                foreach (var m in mats) if (m.HasProperty("_LightDir")) m.SetVector("_LightDir", lw);
                yield return null;
                yield return null;
                yield return null;
                yield return new WaitForEndOfFrame();
                var rt = new RenderTexture(CapW, CapH, 24, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB) { antiAliasing = 4 };
                cam.targetTexture = rt;
                cam.Render();
                cam.targetTexture = null;
                var prev = RenderTexture.active;
                RenderTexture.active = rt;
                var t = new Texture2D(CapW, CapH, TextureFormat.RGB24, false);
                t.ReadPixels(new Rect(0, 0, CapW, CapH), 0, 0);
                t.Apply();
                RenderTexture.active = prev;
                File.WriteAllBytes(Path.Combine(dir, $"{tag}_{s.n}.png"), t.EncodeToPNG());
                Destroy(t);
                rt.Release();
                Destroy(rt);
                Log($"{tag} {s.n}: {state()}");
            }
            Destroy(go);
            foreach (var m in mats) Destroy(m);
            yield return null;
        }
    }
}
