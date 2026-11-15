using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using Unity.Profiling;
using Unity.Profiling.LowLevel.Unsafe;
using UnityEngine;
using UnityEngine.LowLevel;
using UnityEngine.Playables;
using UnityEngine.Profiling;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEngine.SceneManagement;

namespace MMG.Experiments.EyeView
{
    /// <summary>
    /// test only (Android device build of ToonTest_01 v6j): runs every phase by itself after start and writes
    /// &lt;persistentDataPath&gt;/eyeview/: log.txt, *.csv, shots/*.png. Phases: info, quality (4 render settings x 10 shots),
    /// perf with 1 and 12 characters, eye correction LOD, thermal run, stability checks, scene re-entry, background.
    /// Command line / intent extra "phases" (comma list) limits the phases.
    /// </summary>
    public sealed class EyeViewDeviceTest : MonoBehaviour
    {
        public GameObject characterPrefab;
        public List<Material> lightMaterials = new List<Material>();
        public Vector3 lightLocal = new Vector3(-0.296f, 0.5f, -0.814f);
        public RuntimeAnimatorController animController;
        public EyeViewDirectorAsset directorAsset;
        public float perfSeconds = 20f, thermalSeconds = 300f;

        static int reloadStage;                       // survives the scene re-entry test
        static readonly StringBuilder LogText = new StringBuilder();

        string dir;
        Camera cam, cam2;
        readonly List<EyeViewController> chars = new List<EyeViewController>();
        UniversalRenderPipelineAsset urp;
        float sx = 1f, front = 1f;
        HashSet<string> phases;
        bool hostCapture;                             // shots taken by the host (adb screencap) - the real screen
        bool rtCapture;                               // shots rendered into a 1080 x 2340 RenderTexture (Editor comparison)
        bool debugMats;
        int origMsaa = 1;
        float origScale = 1f;                               // lids / head / eyeball drawn in flat colours (what shows through the lash edge)
        const int CapW = 1080, CapH = 2340;

        // render check (beginContextRendering)
        bool checking;
        int chkFrames, chkKeyBad, chkSumBad, chkMissed, chkBlinkBad;
        bool checkBlink;                              // Blink weight at render == the controller's blink field (Fields input)

        struct RS
        {
            public string name;
            public int msaa;
            public float scale;
        }

        static readonly RS[] Settings =
        {
            new RS { name = "A_msaa1_rs080", msaa = 1, scale = 0.8f }, new RS { name = "B_msaa2_rs080", msaa = 2, scale = 0.8f },
            new RS { name = "C_msaa4_rs080", msaa = 4, scale = 0.8f }, new RS { name = "D_msaa4_rs100", msaa = 4, scale = 1.0f },
        };

        void Log(string s)
        {
            string line = $"[{Time.realtimeSinceStartup:F1}s f{Time.frameCount}] {s}";
            Debug.Log("[EyeViewTest] " + line);
            LogText.AppendLine(line);
            File.AppendAllText(Path.Combine(dir, "log.txt"), line + "\n");
        }

        void Awake()
        {
            dir = Path.Combine(Application.persistentDataPath, "eyeview");
            Directory.CreateDirectory(Path.Combine(dir, "shots"));
            Screen.orientation = ScreenOrientation.Portrait;
            Screen.sleepTimeout = SleepTimeout.NeverSleep;
            QualitySettings.vSyncCount = 0;
            Application.targetFrameRate = 120;
            urp = GraphicsSettings.currentRenderPipeline as UniversalRenderPipelineAsset;
            if (urp != null) { origMsaa = urp.msaaSampleCount; origScale = urp.renderScale; }
            string arg = "";
#if UNITY_ANDROID && !UNITY_EDITOR
            try
            {
                using var up = new AndroidJavaClass("com.unity3d.player.UnityPlayer");
                using var act = up.GetStatic<AndroidJavaObject>("currentActivity");
                using var intent = act.Call<AndroidJavaObject>("getIntent");
                arg = intent.Call<string>("getStringExtra", "phases") ?? "";
            }
            catch (System.Exception e) { Debug.LogWarning(e.Message); }
#endif
            // <persistentDataPath>/eyeview_phases.txt: "quality,stability;perf=3;thermal=10" (phases; seconds)
            string cfg = Path.Combine(Application.persistentDataPath, "eyeview_phases.txt");
            if (string.IsNullOrEmpty(arg) && File.Exists(cfg))
            {
                var parts = File.ReadAllText(cfg).Trim().Split(';');
                arg = parts[0];
                foreach (var p in parts)
                {
                    if (p.StartsWith("perf=")) perfSeconds = float.Parse(p.Substring(5), System.Globalization.CultureInfo.InvariantCulture);
                    if (p.StartsWith("thermal=")) thermalSeconds = float.Parse(p.Substring(8), System.Globalization.CultureInfo.InvariantCulture);
                }
            }
            phases = new HashSet<string>(arg.Split(new[] { ',' }, System.StringSplitOptions.RemoveEmptyEntries));
            hostCapture = phases.Remove("hostcapture");
            rtCapture = phases.Remove("rtcapture");
            debugMats = phases.Remove("debugmats");
        }

        bool Want(string p) => phases.Count == 0 || phases.Contains(p);

        void OnDestroy()
        {
            if (urp != null) { urp.msaaSampleCount = origMsaa; urp.renderScale = origScale; }
        }

        void OnEnable() => RenderPipelineManager.beginContextRendering += Check;
        void OnDisable() => RenderPipelineManager.beginContextRendering -= Check;

        void OnApplicationPause(bool paused) => Log($"OnApplicationPause {paused}; loop installed {EyeViewLoop.IsInstalled()}, last run f{EyeViewLoop.LastRunFrame}");

        IEnumerator Start()
        {
            Log($"START reloadStage {reloadStage}; device {SystemInfo.deviceModel}, OS {SystemInfo.operatingSystem}, GPU {SystemInfo.graphicsDeviceName} ({SystemInfo.graphicsDeviceType}, {SystemInfo.graphicsDeviceVersion}), " +
                $"CPU {SystemInfo.processorType} x{SystemInfo.processorCount}, RAM {SystemInfo.systemMemorySize} MB, screen {Screen.width}x{Screen.height} @ {Screen.currentResolution.refreshRateRatio.value:F0} Hz, " +
                $"URP {(urp ? urp.name : "none")}, dev {Debug.isDebugBuild}, frame timing {FrameTimingManager.IsFeatureEnabled()}");
            SetupCameras();
            if (reloadStage > 0)
            {
                yield return SceneReentryStep();
                yield break;
            }
            Log($"PlayerLoop PostLateUpdate: {EyeViewLoop.Describe()}");
            Spawn(1);
            yield return null;
            yield return null;
            Log($"after spawn: loop installed {EyeViewLoop.IsInstalled()} after {EyeViewLoop.InsertedAfter} before {EyeViewLoop.InsertedBefore}; installs {EyeViewLoop.Installs}; active {EyeViewLoop.ActiveCount}");
            Log($"PlayerLoop PostLateUpdate: {EyeViewLoop.Describe()}");
            if (Want("quality")) yield return Quality();
            if (Want("perf")) yield return Perf();
            if (Want("thermal")) yield return Thermal();
            if (Want("stability")) yield return Stability();
            if (Want("reentry"))
            {
                reloadStage = 1;
                Log("scene re-entry 1 of 3");
                SceneManager.LoadScene(SceneManager.GetActiveScene().name);
                yield break;
            }
            yield return Finish();
        }

        IEnumerator Finish()
        {
            if (Want("background")) yield return Background();
            Log("ALL_DONE");
            File.WriteAllText(Path.Combine(dir, "done.txt"), "ok");
        }

        // ------------------------------------------------------------------ scene
        void SetupCameras()
        {
            var go = new GameObject("EyeViewCam") { tag = "MainCamera" };
            cam = go.AddComponent<Camera>();
            cam.clearFlags = CameraClearFlags.SolidColor;
            cam.backgroundColor = new Color(0.93f, 0.93f, 0.95f);
            cam.nearClipPlane = 0.02f;
            cam.farClipPlane = 50f;
            cam.allowMSAA = true;
            var go2 = new GameObject("EyeViewCam2");
            cam2 = go2.AddComponent<Camera>();
            cam2.clearFlags = CameraClearFlags.SolidColor;
            cam2.backgroundColor = new Color(0.95f, 0.93f, 0.93f);
            cam2.nearClipPlane = 0.02f;
            cam2.allowMSAA = true;
            cam2.enabled = false;
        }

        void Spawn(int n)
        {
            foreach (var c in chars) if (c != null) Destroy(c.gameObject);
            chars.Clear();
            for (int i = 0; i < n; i++)
            {
                var go = Instantiate(characterPrefab);
                go.name = $"EyeChar_{i}";
                if (n > 1)
                {
                    int col = i % 3, row = i / 3;                                   // 3 x 4, 0.9 m x 0.75 m apart
                    go.transform.position = new Vector3((col - 1) * 0.9f, -row * 0.75f, 0f);
                }
                var c = go.GetComponent<EyeViewController>();
                c.viewCamera = cam;
                chars.Add(c);
            }
            var c0 = chars[0];
            sx = Mathf.Sign(Vector3.Dot(c0.characterLeftLocal, Vector3.right));
            front = Mathf.Sign(c0.faceForwardLocal.z);
        }

        void DebugMats(GameObject go)
        {
            var sh = Shader.Find("Universal Render Pipeline/Unlit");
            Material Flat(Color c) { var m = new Material(sh); m.SetColor("_BaseColor", c); return m; }
            var lids = Flat(Color.green); var head = Flat(Color.blue); var ball = Flat(Color.red);
            foreach (var r in go.GetComponentsInChildren<Renderer>(true))
            {
                Material m = r.name.StartsWith("Eye_Lids") ? lids : r.name == "Blockout_Head" ? head : r.name.StartsWith("Eye_Ball") ? ball : null;
                if (m != null) r.sharedMaterials = Enumerable.Repeat(m, r.sharedMaterials.Length).ToArray();
            }
            Log("debug materials: lids green, head blue, eyeball red");
        }

        Vector3 Pivot(EyeViewController c) => (c.eyeL.position + c.eyeR.position) * 0.5f;

        /// <summary>camera at yaw (+ = toward the character's left) / pitch around the pivot, horizontal view width w (m)</summary>
        void Place(Camera c, Vector3 pivot, float yaw, float pitch, float dist, float width)
        {
            Vector3 f = new Vector3(0, 0, front);
            Vector3 dirv = Quaternion.AngleAxis(sx * yaw, Vector3.up) * f;
            Vector3 right = Vector3.Cross(Vector3.up, dirv).normalized;
            dirv = Quaternion.AngleAxis(-pitch, right) * dirv;
            c.transform.position = pivot + dirv * dist;
            c.transform.rotation = Quaternion.LookRotation(-dirv, Vector3.up);
            float aspect = rtCapture ? (float)CapW / CapH : (float)Screen.width / Screen.height;
            float h = 2f * Mathf.Atan(width * 0.5f / dist);
            c.fieldOfView = 2f * Mathf.Atan(Mathf.Tan(h * 0.5f) / aspect) * Mathf.Rad2Deg;
            Vector3 lw = Quaternion.AngleAxis(sx * yaw, Vector3.up) * lightLocal;          // the sun turns with the camera
            foreach (var m in lightMaterials) if (m != null) m.SetVector("_LightDir", lw);
        }

        void Inputs(float blink, float eyeSmile, float gaze, float smile = 0f)
        {
            foreach (var c in chars)
            {
                c.blink = blink; c.eyeSmile = eyeSmile; c.gaze = gaze; c.smile = smile; c.surprise = 0f;
            }
        }

        string Apply(RS s)
        {
            if (urp == null) return "no URP asset";
            urp.msaaSampleCount = s.msaa;
            urp.renderScale = s.scale;
            var desc = new RenderTextureDescriptor(Mathf.RoundToInt(Screen.width * s.scale), Mathf.RoundToInt(Screen.height * s.scale), RenderTextureFormat.ARGB32, 24) { msaaSamples = s.msaa };
            int sup = SystemInfo.GetRenderTextureSupportedMSAASampleCount(desc);
            return $"{s.name}: asset msaa {urp.msaaSampleCount}, render scale {urp.renderScale:F2}, device supports {sup}x for {desc.width}x{desc.height}";
        }

        IEnumerator Shot(string name)
        {
            yield return null;
            yield return null;
            yield return null;
            if (hostCapture)
            {
                // the host takes "adb shell screencap" of the screen, then creates <name>.done
                string ready = Path.Combine(dir, "shot_ready.txt"), done = Path.Combine(dir, "shots", name + ".done");
                File.WriteAllText(ready, name);
                float t0 = Time.realtimeSinceStartup;
                while (!File.Exists(done) && Time.realtimeSinceStartup - t0 < 30f) yield return null;
                File.Delete(ready);
                if (!File.Exists(done)) Log("host capture timed out: " + name);
                yield break;
            }
            yield return new WaitForEndOfFrame();
            if (rtCapture)
            {
                int msaa = urp != null ? urp.msaaSampleCount : 1;
                var rt = new RenderTexture(CapW, CapH, 24, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB) { antiAliasing = msaa };
                var prevT = cam.targetTexture;
                cam.targetTexture = rt;
                cam.Render();
                cam.targetTexture = prevT;
                var prevA = RenderTexture.active;
                RenderTexture.active = rt;
                var t2 = new Texture2D(CapW, CapH, TextureFormat.RGB24, false);
                t2.ReadPixels(new Rect(0, 0, CapW, CapH), 0, 0);
                t2.Apply();
                RenderTexture.active = prevA;
                File.WriteAllBytes(Path.Combine(dir, "shots", name + ".png"), t2.EncodeToPNG());
                Destroy(t2);
                rt.Release();
                Destroy(rt);
                yield break;
            }
            var tex = ScreenCapture.CaptureScreenshotAsTexture();
            File.WriteAllBytes(Path.Combine(dir, "shots", name + ".png"), tex.EncodeToPNG());
            Destroy(tex);
        }

        // ------------------------------------------------------------------ quality
        IEnumerator Quality()
        {
            Spawn(1);
            if (debugMats) DebugMats(chars[0].gameObject);
            var c = chars[0];
            var shots = new (string n, float yaw, float pitch, float width, float blink, float es)[]
            {
                ("front_eye", 0, 0, 0.36f, 0, 0), ("front_face", 0, 0, 0.62f, 0, 0), ("far35R_eye", 35, 0, 0.36f, 0, 0),
                ("far35L_eye", -35, 0, 0.36f, 0, 0), ("far45R_eye", 45, 0, 0.36f, 0, 0), ("far45L_eye", -45, 0, 0.36f, 0, 0),
                ("blink35_eye", 35, 0, 0.36f, 1, 0), ("blink50_35_eye", 35, 0, 0.36f, 0.5f, 0), ("eyesmile35_eye", 35, 0, 0.36f, 0, 1),
                ("face35", 35, 0, 0.62f, 0, 0),
            };
            foreach (var s in Settings)
            {
                Log("quality " + Apply(s));
                foreach (var sh in shots)
                {
                    Inputs(sh.blink, sh.es, 0);
                    Place(cam, Pivot(c), sh.yaw, sh.pitch, 0.7f, sh.width);
                    yield return Shot($"{s.name}_{sh.n}");
                }
            }
        }

        // ------------------------------------------------------------------ perf
        sealed class Rec
        {
            public readonly List<float> dt = new List<float>(), main = new List<float>(), cpu = new List<float>(), gpu = new List<float>(),
                eye = new List<float>(), skin = new List<float>();
        }

        List<ProfilerRecorder> skinRecs;
        double[] markerSum;
        List<string> skinNames;

        void StartRecorders()
        {
            skinRecs = new List<ProfilerRecorder>();
            skinNames = new List<string>();
            var all = new List<ProfilerRecorderHandle>();
            ProfilerRecorderHandle.GetAvailable(all);
            foreach (var h in all)
            {
                var d = ProfilerRecorderHandle.GetDescription(h);
                string n = d.Name;
                if (n.Contains("Skin") || n.Contains("BlendShape"))
                {
                    if (d.UnitType != ProfilerMarkerDataUnit.TimeNanoseconds) continue;
                    skinRecs.Add(ProfilerRecorder.StartNew(d.Category, n, 4));
                    skinNames.Add(n);
                }
            }
        }

        void StopRecorders()
        {
            foreach (var r in skinRecs) r.Dispose();
        }

        IEnumerator Measure(string label, float seconds, System.Action<float> drive, string extra = "")
        {
            var rec = new Rec();
            markerSum = new double[skinRecs.Count];
            var timings = new FrameTiming[1];
            float t0 = Time.realtimeSinceStartup;
            // settle
            while (Time.realtimeSinceStartup - t0 < 3f) { drive(Time.realtimeSinceStartup - t0); yield return null; }
            t0 = Time.realtimeSinceStartup;
            var csv = new StringBuilder("t,dt_ms,cpu_main_ms,cpu_frame_ms,gpu_ms,eye_us,skin_ms\n");
            float last = Time.realtimeSinceStartup;
            while (Time.realtimeSinceStartup - t0 < seconds)
            {
                drive(Time.realtimeSinceStartup - t0);
                yield return null;
                float now = Time.realtimeSinceStartup;
                float dt = (now - last) * 1000f;
                last = now;
                FrameTimingManager.CaptureFrameTimings();
                uint got = FrameTimingManager.GetLatestTimings(1, timings);
                float main = got > 0 ? (float)timings[0].cpuMainThreadFrameTime : -1f;
                float cpu = got > 0 ? (float)timings[0].cpuFrameTime : -1f;
                float gpu = got > 0 ? (float)timings[0].gpuFrameTime : -1f;
                double eye = 0;
                foreach (var c in chars) eye += c.LastCostMicroseconds;
                double skin = 0;
                for (int k = 0; k < skinRecs.Count; k++)
                {
                    long v = skinRecs[k].LastValue;
                    markerSum[k] += v;
                    if (skinNames[k] == "PostLateUpdate.UpdateAllSkinnedMeshes") skin = v;
                }
                rec.dt.Add(dt); rec.main.Add(main); rec.cpu.Add(cpu); rec.gpu.Add(gpu); rec.eye.Add((float)eye); rec.skin.Add((float)(skin / 1e6));
                csv.AppendLine($"{now - t0:F3},{dt:F3},{main:F3},{cpu:F3},{gpu:F3},{eye:F1},{skin / 1e6:F3}");
            }
            File.WriteAllText(Path.Combine(dir, $"perf_{label}.csv"), csv.ToString());
            float Avg(List<float> v) { double s = 0; int n = 0; foreach (var x in v) if (x >= 0) { s += x; n++; } return n > 0 ? (float)(s / n) : -1f; }
            float P95(List<float> v) { var a = v.FindAll(x => x >= 0); if (a.Count == 0) return -1f; a.Sort(); return a[Mathf.Min(a.Count - 1, (int)(a.Count * 0.95f))]; }
            float avgDt = Avg(rec.dt);
            Log($"PERF {label}: frames {rec.dt.Count}, fps {1000f / avgDt:F1}, frame ms avg {avgDt:F2} p95 {P95(rec.dt):F2}, cpu main avg {Avg(rec.main):F2} p95 {P95(rec.main):F2}, " +
                $"cpu frame avg {Avg(rec.cpu):F2}, gpu avg {Avg(rec.gpu):F2} p95 {P95(rec.gpu):F2}, eye controllers avg {Avg(rec.eye):F1} us p95 {P95(rec.eye):F1} us, " +
                $"UpdateAllSkinnedMeshes avg {Avg(rec.skin):F3} ms p95 {P95(rec.skin):F3} ms {extra}");
            var ms = new StringBuilder();
            for (int k = 0; k < skinNames.Count; k++)
                if (markerSum[k] > 0) ms.Append($"{skinNames[k]} {markerSum[k] / rec.dt.Count / 1e6:F3} ms; ");
            Log($"MARKERS {label}: {ms}");
        }

        void Expressions(float t)
        {
            float blink = Mathf.Clamp01(1f - Mathf.Abs((t % 2.5f) - 0.15f) / 0.12f);
            float es = (t % 7f) > 5.5f ? Mathf.Sin(((t % 7f) - 5.5f) / 1.5f * Mathf.PI) : 0f;
            Inputs(blink, Mathf.Clamp01(es), 0.2f * Mathf.Sin(t * 1.3f));
        }

        void Memory()
        {
            var meshes = new HashSet<Mesh>();
            var texs = new HashSet<Texture>();
            foreach (var r in chars[0].GetComponentsInChildren<Renderer>(true))
            {
                if (r is SkinnedMeshRenderer s && s.sharedMesh) meshes.Add(s.sharedMesh);
                else if (r.TryGetComponent<MeshFilter>(out var mf) && mf.sharedMesh) meshes.Add(mf.sharedMesh);
                foreach (var m in r.sharedMaterials)
                {
                    if (m == null) continue;
                    foreach (var id in m.GetTexturePropertyNameIDs())
                    {
                        var t = m.GetTexture(id);
                        if (t) texs.Add(t);
                    }
                }
            }
            long mb = 0, tb = 0, eyeMesh = 0;
            foreach (var m in meshes)
            {
                long sz = Profiler.GetRuntimeMemorySizeLong(m);
                mb += sz;
                if (m.name.StartsWith("Eye_Lids") || m.name.StartsWith("Eye_Lash")) eyeMesh += sz;
            }
            foreach (var t in texs) tb += Profiler.GetRuntimeMemorySizeLong(t);
            int shapes = 0;
            foreach (var m in meshes) shapes += m.blendShapeCount;
            Log($"MEMORY one character: meshes {meshes.Count} = {mb / 1024.0:F0} KB (eye lids + lash {eyeMesh / 1024.0:F0} KB), blend shapes {shapes}, textures {texs.Count} = {tb / 1024.0:F0} KB; " +
                $"process: total allocated {Profiler.GetTotalAllocatedMemoryLong() / 1048576.0:F1} MB, reserved {Profiler.GetTotalReservedMemoryLong() / 1048576.0:F1} MB, graphics driver {Profiler.GetAllocatedMemoryForGraphicsDriver() / 1048576.0:F1} MB");
        }

        IEnumerator Perf()
        {
            StartRecorders();
            // one character, camera orbits +-60 deg, expressions running, correction always on
            Spawn(1);
            yield return null;
            Memory();
            foreach (var s in Settings)
            {
                Log("perf1 " + Apply(s));
                yield return Measure("1char_" + s.name, perfSeconds, t =>
                {
                    Place(cam, Pivot(chars[0]), 60f * Mathf.Sin(t * Mathf.PI * 2f / 8f), 0, 1.1f, 0.62f);
                    Expressions(t);
                });
            }
            // twelve characters, camera fixed, every head turns +-60 deg the same way (same distance and screen size)
            Spawn(12);
            yield return null;
            Vector3 centre = new Vector3(0, Pivot(chars[0]).y - 1.125f, 0);
            void Drive12(float t)
            {
                float yaw = 60f * Mathf.Sin(t * Mathf.PI * 2f / 8f);
                foreach (var c in chars) c.transform.rotation = Quaternion.AngleAxis(-sx * yaw, Vector3.up);
                Place(cam, centre, 0, 0, 4.2f, 3.0f);
                Expressions(t);
            }
            yield return null;
            Place(cam, centre, 0, 0, 4.2f, 3.0f);
            yield return null;
            float px = 0;
            foreach (var c in chars)
            {
                Vector3 a = cam.WorldToScreenPoint(c.eyeL.position), b = cam.WorldToScreenPoint(c.eyeR.position);
                px += Vector2.Distance(a, b);
            }
            string size = $"eye distance on screen avg {px / chars.Count:F0} px (screen {Screen.width} px wide)";
            foreach (var s in new[] { Settings[0], Settings[2] })
            {
                Log("perf12 " + Apply(s));
                foreach (var c in chars) { c.viewCorrection = true; c.viewUpdateInterval = 1; }
                yield return Measure("12char_on_" + s.name, perfSeconds, Drive12, size);
            }
            // LOD variants (setting C)
            Apply(Settings[2]);
            foreach (var c in chars) { c.viewCorrection = false; c.viewUpdateInterval = 1; }
            yield return Measure("12char_viewoff_" + Settings[2].name, perfSeconds, Drive12, size);
            foreach (var c in chars) { c.viewCorrection = true; c.viewUpdateInterval = 4; }
            yield return Measure("12char_every4_" + Settings[2].name, perfSeconds, Drive12, size);
            foreach (var c in chars) { c.viewCorrection = true; c.viewUpdateInterval = 1; }
            // what the LOD changes on screen at this size: all heads at 35 deg, on / off
            foreach (var c in chars) c.transform.rotation = Quaternion.AngleAxis(-sx * 35f, Vector3.up);
            Inputs(0, 0, 0);
            foreach (var m in lightMaterials) if (m != null) m.SetVector("_LightDir", lightLocal);
            yield return Shot("lod12_on_35");
            foreach (var c in chars) c.viewCorrection = false;
            yield return Shot("lod12_off_35");
            foreach (var c in chars) c.viewCorrection = true;
            StopRecorders();
        }

        IEnumerator Thermal()
        {
            if (chars.Count != 12) Spawn(12);
            yield return null;
            Apply(Settings[2]);
            Vector3 centre = new Vector3(0, Pivot(chars[0]).y - 1.125f, 0);
            var csv = new StringBuilder("t,fps_5s,frame_ms_p95_5s,cpu_main_ms_5s,gpu_ms_5s\n");
            var timings = new FrameTiming[1];
            double sumMain = 0, sumGpu = 0;
            int nT = 0;
            float t0 = Time.realtimeSinceStartup, w0 = t0;
            var win = new List<float>();
            float last = t0;
            Log($"THERMAL start ({thermalSeconds:F0} s, 12 characters, {Settings[2].name})");
            while (Time.realtimeSinceStartup - t0 < thermalSeconds)
            {
                float t = Time.realtimeSinceStartup - t0;
                float yaw = 60f * Mathf.Sin(t * Mathf.PI * 2f / 8f);
                foreach (var c in chars) c.transform.rotation = Quaternion.AngleAxis(-sx * yaw, Vector3.up);
                Place(cam, centre, 0, 0, 4.2f, 3.0f);
                Expressions(t);
                yield return null;
                float now = Time.realtimeSinceStartup;
                win.Add((now - last) * 1000f);
                last = now;
                FrameTimingManager.CaptureFrameTimings();
                if (FrameTimingManager.GetLatestTimings(1, timings) > 0) { sumMain += timings[0].cpuMainThreadFrameTime; sumGpu += timings[0].gpuFrameTime; nT++; }
                if (now - w0 >= 5f)
                {
                    win.Sort();
                    csv.AppendLine($"{now - t0:F1},{win.Count / (now - w0):F1},{win[(int)(win.Count * 0.95f)]:F2},{sumMain / Mathf.Max(nT, 1):F2},{sumGpu / Mathf.Max(nT, 1):F2}");
                    sumMain = sumGpu = 0; nT = 0;
                    win.Clear();
                    w0 = now;
                }
            }
            File.WriteAllText(Path.Combine(dir, "thermal.csv"), csv.ToString());
            Log("THERMAL done");
        }

        // ------------------------------------------------------------------ stability
        void Check(ScriptableRenderContext ctx, List<Camera> cams)
        {
            if (!checking || chars.Count == 0) return;
            chkFrames++;
            foreach (var c in chars)
            {
                if (c == null || !c.isActiveAndEnabled) continue;
                if (c.ComposedFrame != Time.frameCount) chkMissed++;
                var w = c.Written;
                foreach (var r in c.renderers)
                {
                    var m = r.sharedMesh;
                    float sumL = 0, sumR = 0, b = 0, es = 0;
                    bool bad = false;
                    for (int i = 0; i < m.blendShapeCount; i++)
                    {
                        string n = m.GetBlendShapeName(i);
                        float v = r.GetBlendShapeWeight(i) / 100f;
                        if (n == "Blink") b = v;
                        else if (n == "EyeSmile") es = v;
                        else if (n.StartsWith("View"))
                        {
                            if (w.TryGetValue(n, out var e) && Mathf.Abs(e - v) > 0.001f) bad = true;
                            if (n.EndsWith("L") || n.Contains("L_")) sumL += v; else sumR += v;
                        }
                    }
                    if (bad) chkKeyBad++;
                    if (Mathf.Max(sumL, sumR) > (1 - b) * (1 - es) + 0.001f) chkSumBad++;
                    if (checkBlink && (r.name.StartsWith("Eye_Lids") || r.name.StartsWith("Eye_Lash")) && Mathf.Abs(b - c.blink) > 0.01f) chkBlinkBad++;
                }
            }
        }

        void ResetCheck()
        {
            chkFrames = chkKeyBad = chkSumBad = chkMissed = chkBlinkBad = 0;
        }

        string CheckResult() => $"frames {chkFrames}, view key overwritten {chkKeyBad}, closing over Blink100 {chkSumBad}, frames without compose {chkMissed}, blink mismatch {chkBlinkBad}";

        IEnumerator Run(int frames, System.Action<int> step)
        {
            for (int i = 0; i < frames; i++)
            {
                step(i);
                yield return null;
            }
        }

        IEnumerator Stability()
        {
            Spawn(1);
            Apply(Settings[0]);
            var c = chars[0];
            var go = c.gameObject;
            yield return null;
            Place(cam, Pivot(c), 35, 0, 0.9f, 0.62f);
            checking = true;
            checkBlink = true;

            // baseline with expressions
            ResetCheck();
            yield return Run(120, i => { Expressions(i / 60f); });
            Log("STAB baseline: " + CheckResult());

            // duplicate driver on the same renderers
            var dup = go.AddComponent<EyeViewController>();
            dup.head = c.head; dup.eyeL = c.eyeL; dup.eyeR = c.eyeR; dup.renderers = new List<SkinnedMeshRenderer>(c.renderers);
            dup.faceForwardLocal = c.faceForwardLocal; dup.characterLeftLocal = c.characterLeftLocal; dup.viewCamera = cam;
            yield return null;
            ResetCheck();
            yield return Run(60, i => { Expressions(i / 60f); });
            Log($"STAB duplicate controller: registered {dup.Registered}, enabled {dup.enabled}, active drivers {EyeViewLoop.ActiveCount}; " + CheckResult());
            Destroy(dup);
            yield return null;

            // enable / disable every frame
            ResetCheck();
            checking = false;
            yield return Run(200, i => { c.enabled = i % 2 == 0; });
            c.enabled = true;
            yield return null;
            checking = true;
            yield return Run(60, i => { Expressions(i / 60f); });
            Log($"STAB enable/disable x200: active drivers {EyeViewLoop.ActiveCount} (expect 1); after: " + CheckResult());

            // junk writers before and after every LateUpdate
            var early = go.AddComponent<EyeViewJunkWriterEarly>();
            var late = go.AddComponent<EyeViewJunkWriterLate>();
            early.target = late.target = c;
            early.writeBlink = late.writeBlink = true;
            ResetCheck();
            int foreign0 = c.ForeignWrites;
            yield return Run(120, i => { Expressions(i / 60f); });
            Log($"STAB junk writers (view keys + Blink, order -30000 / +30000): foreign writes seen {c.ForeignWrites - foreign0}; " + CheckResult());
            Destroy(early);
            Destroy(late);
            yield return null;

            // Animator animating the controller fields
            var anim = go.GetComponent<Animator>();
            if (anim == null) anim = go.AddComponent<Animator>();
            anim.runtimeAnimatorController = animController;
            anim.enabled = true;
            float bmin = 1, bmax = 0;
            ResetCheck();
            yield return Run(180, i => { bmin = Mathf.Min(bmin, c.blink); bmax = Mathf.Max(bmax, c.blink); });
            Log($"STAB Animator -> controller fields: blink range {bmin:F2}..{bmax:F2}; " + CheckResult());
            anim.runtimeAnimatorController = null;
            yield return null;

            // PlayableDirector (no Timeline package): custom PlayableAsset -> AnimationClipPlayable -> Animator
            var dirc = go.AddComponent<PlayableDirector>();
            dirc.playableAsset = directorAsset;
            dirc.extrapolationMode = DirectorWrapMode.Loop;
            dirc.timeUpdateMode = DirectorUpdateMode.GameTime;
            dirc.Play();
            bmin = 1; bmax = 0;
            ResetCheck();
            yield return Run(180, i => { bmin = Mathf.Min(bmin, c.blink); bmax = Mathf.Max(bmax, c.blink); });
            Log($"STAB PlayableDirector -> controller fields: playing {dirc.state}, blink range {bmin:F2}..{bmax:F2}; " + CheckResult());
            dirc.Stop();
            Destroy(dirc);
            anim.enabled = false;
            checkBlink = false;
            yield return null;

            // camera switches and a missing camera (falls back to Camera.main)
            ResetCheck();
            var used = new HashSet<string>();
            yield return Run(240, i =>
            {
                int k = (i / 30) % 3;
                Place(cam, Pivot(c), 35, 0, 0.9f, 0.62f);
                Place(cam2, Pivot(c), -45, 0, 0.9f, 0.62f);
                cam.enabled = k != 1; cam2.enabled = k == 1;
                c.viewCamera = k == 0 ? cam : k == 1 ? cam2 : null;
                if (c.UsedCamera) used.Add($"{c.UsedCamera.name} farL {c.FarL:F2} farR {c.FarR:F2}");
                Inputs(0, 0, 0);
            });
            cam.enabled = true; cam2.enabled = false; c.viewCamera = cam;
            Log($"STAB camera switch (cam 35 / cam2 -45 / none -> Camera.main): [{string.Join("; ", used)}]; " + CheckResult());

            // camera above / below the head
            var pitchLog = new StringBuilder();
            ResetCheck();
            yield return Run(161, i =>
            {
                float p = -80 + i;
                Place(cam, Pivot(c), 35, p, 0.9f, 0.62f);
                if (i % 20 == 0) pitchLog.Append($"{p:F0}:{c.FarR:F2}/{c.PitchR:F0} ");
            });
            Log($"STAB pitch -80..+80 at yaw 35 (pitch: farR / measured pitch): {pitchLog}; " + CheckResult());

            // player loop replaced by the default one (our step removed)
            Place(cam, Pivot(c), 35, 0, 0.9f, 0.62f);
            int fb0 = c.FallbackComposes, re0 = EyeViewLoop.Reinstalls;
            ResetCheck();
            PlayerLoop.SetPlayerLoop(PlayerLoop.GetDefaultPlayerLoop());
            yield return Run(120, i => { Expressions(i / 60f); });
            Log($"STAB player loop replaced: installed again {EyeViewLoop.IsInstalled()}, reinstalls {EyeViewLoop.Reinstalls - re0}, fallback composes {c.FallbackComposes - fb0}; " + CheckResult());
            checking = false;
            checkBlink = false;
        }

        IEnumerator SceneReentryStep()
        {
            Spawn(1);
            yield return null;
            yield return null;
            Place(cam, Pivot(chars[0]), 35, 0, 0.9f, 0.62f);
            checking = true;
            checkBlink = true;
            ResetCheck();
            yield return Run(90, i => { Expressions(i / 60f); });
            checking = false;
            checkBlink = false;
            Log($"REENTRY {reloadStage}: loop installed {EyeViewLoop.IsInstalled()}, installs {EyeViewLoop.Installs}, active drivers {EyeViewLoop.ActiveCount} (expect 1); " + CheckResult());
            if (reloadStage < 3)
            {
                reloadStage++;
                SceneManager.LoadScene(SceneManager.GetActiveScene().name);
                yield break;
            }
            reloadStage = 0;
            yield return Finish();
        }

        IEnumerator Background()
        {
            if (chars.Count == 0) Spawn(1);
            Place(cam, Pivot(chars[0]), 35, 0, 0.9f, 0.62f);
            Log("READY_FOR_BACKGROUND (send HOME, then bring the app back)");
            File.WriteAllText(Path.Combine(dir, "ready_background.txt"), "ok");
            float t0 = Time.realtimeSinceStartup;
            bool sawPause = false;
            int frames0 = Time.frameCount;
            while (Time.realtimeSinceStartup - t0 < 120f)
            {
                if (Time.frameCount - frames0 > 5 && Time.unscaledDeltaTime > 1.5f) sawPause = true;
                if (sawPause) break;
                yield return null;
            }
            checking = true;
            checkBlink = true;
            ResetCheck();
            yield return Run(150, i => { Expressions(i / 60f); });
            checking = false;
            checkBlink = false;
            Log($"BACKGROUND resumed {sawPause}: loop installed {EyeViewLoop.IsInstalled()}, active drivers {EyeViewLoop.ActiveCount}; " + CheckResult());
        }
    }
}
