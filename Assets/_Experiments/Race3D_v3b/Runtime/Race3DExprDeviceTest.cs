using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using Unity.Profiling;
using Unity.Profiling.LowLevel.Unsafe;
using UnityEngine;
using UnityEngine.Profiling;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace MMG.Experiments.Race3DExpr
{
    /// <summary>
    /// Test only (Android device build of Race3D v3b): quality shots (Happy / Angry2 pull / Cry / Surprise×gaze×Blink),
    /// material isolation of two actors, perf for 1 and 12 characters. Writes &lt;persistentDataPath&gt;/race3dexpr/.
    /// Intent / eyeview_phases-style file: race3dexpr_phases.txt with "quality,perf,isolation;perf=12" and hostcapture.
    /// Angry2 = strong angry default; Angry = weak. Brow pull from HairBrowPullTable (not a fixed global).
    /// </summary>
    public sealed class Race3DExprDeviceTest : MonoBehaviour
    {
        public GameObject modelPrefab;
        public GameObject formalPrefab;
        public Shader eyeSparkleShader, hairStencilShader, browCardShader, tearStreamShader, unlitShader;
        public Texture2D sparkleL, sparkleR;
        public TextAsset specJson;
        public HairBrowPullTable browPullTable;
        public float perfSeconds = 12f;
        public Vector3 lightAtFront = new Vector3(0.296f, 0.5f, 0.814f);

        [System.Serializable] class CamShot { public string name; public float yaw, w, h, ortho; public float[] loc; }
        [System.Serializable] class Proj { public string side; public float su, tu, sv, tv, uc, vc; }
        [System.Serializable] class Spec { public CamShot[] shots; public Proj[] proj; public float[] eyeBallL; }

        struct RS { public string name; public int msaa; public float scale; }
        static readonly RS[] Settings =
        {
            new RS { name = "A_msaa1_rs080", msaa = 1, scale = 0.8f },
            new RS { name = "C_msaa4_rs080", msaa = 4, scale = 0.8f },
        };

        string dir;
        Camera cam;
        Spec spec;
        Race3DExprActor.Proj[] projData;
        readonly List<Race3DExprActor> chars = new List<Race3DExprActor>();
        UniversalRenderPipelineAsset urp;
        int origMsaa = 1;
        float origScale = 1f, sx = 1f, front = 1f;
        HashSet<string> phases;
        bool hostCapture;
        readonly StringBuilder logBuf = new StringBuilder();

        void Log(string s)
        {
            string line = $"[{Time.realtimeSinceStartup:F1}s f{Time.frameCount}] {s}";
            Debug.Log("[Race3DExprDevice] " + line);
            logBuf.AppendLine(line);
            File.AppendAllText(Path.Combine(dir, "log.txt"), line + "\n");
        }

        void Awake()
        {
            dir = Path.Combine(Application.persistentDataPath, "race3dexpr");
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
            string cfg = Path.Combine(Application.persistentDataPath, "race3dexpr_phases.txt");
            if (string.IsNullOrEmpty(arg) && File.Exists(cfg))
            {
                var parts = File.ReadAllText(cfg).Trim().Split(';');
                arg = parts[0];
                foreach (var p in parts)
                    if (p.StartsWith("perf=")) perfSeconds = float.Parse(p.Substring(5), System.Globalization.CultureInfo.InvariantCulture);
            }
            phases = new HashSet<string>(arg.Split(new[] { ',' }, System.StringSplitOptions.RemoveEmptyEntries));
            hostCapture = phases.Remove("hostcapture");
            if (phases.Count == 0) { phases.Add("quality"); phases.Add("isolation"); phases.Add("perf"); }
        }

        bool Want(string p) => phases.Contains(p);
        void OnDestroy() { if (urp != null) { urp.msaaSampleCount = origMsaa; urp.renderScale = origScale; } }

        IEnumerator Start()
        {
            spec = JsonUtility.FromJson<Spec>(specJson.text);
            projData = spec.proj.Select(p => new Race3DExprActor.Proj
            {
                side = p.side, su = p.su, tu = p.tu, sv = p.sv, tv = p.tv, uc = p.uc, vc = p.vc
            }).ToArray();
            var go = new GameObject("Race3DExprCam") { tag = "MainCamera" };
            cam = go.AddComponent<Camera>();
            cam.clearFlags = CameraClearFlags.SolidColor;
            cam.backgroundColor = new Color(0.93f, 0.93f, 0.95f);
            cam.nearClipPlane = 0.02f;
            cam.farClipPlane = 50f;
            cam.allowMSAA = true;
            Log($"START device {SystemInfo.deviceModel}, OS {SystemInfo.operatingSystem}, GPU {SystemInfo.graphicsDeviceName} ({SystemInfo.graphicsDeviceType}), " +
                $"CPU {SystemInfo.processorType} x{SystemInfo.processorCount}, RAM {SystemInfo.systemMemorySize} MB, screen {Screen.width}x{Screen.height} @ {Screen.currentResolution.refreshRateRatio.value:F0} Hz, " +
                $"URP {(urp ? urp.name : "none")} msaa {origMsaa} rs {origScale:F2}, hostcapture {hostCapture}, phases [{string.Join(",", phases)}]");
            Spawn(1);
            yield return null;
            sx = Mathf.Sign(Vector3.Dot(chars[0].CharacterLeftLocal, Vector3.right));
            front = Mathf.Sign(chars[0].FaceForwardLocal.z);
            Log($"actor0 browPull {chars[0].BrowPullMeters:F3} m (hair {chars[0].hairItemId}), mats {chars[0].OwnedMaterials.Count}");
            if (Want("quality")) yield return Quality();
            if (Want("isolation")) yield return Isolation();
            if (Want("perf")) yield return Perf();
            Log("ALL_DONE");
            File.WriteAllText(Path.Combine(dir, "done.txt"), "ok");
        }

        void Spawn(int n)
        {
            foreach (var c in chars) if (c != null) Destroy(c.gameObject);
            chars.Clear();
            for (int i = 0; i < n; i++)
            {
                var go = new GameObject($"ExprChar_{i}");
                if (n > 1)
                {
                    int col = i % 3, row = i / 3;
                    go.transform.position = new Vector3((col - 1) * 0.9f, -row * 0.75f, 0f);
                }
                var a = go.AddComponent<Race3DExprActor>();
                a.modelPrefab = modelPrefab; a.formalPrefab = formalPrefab;
                a.eyeSparkleShader = eyeSparkleShader; a.hairStencilShader = hairStencilShader;
                a.browCardShader = browCardShader; a.tearStreamShader = tearStreamShader; a.unlitShader = unlitShader;
                a.sparkleL = sparkleL; a.sparkleR = sparkleR; a.projData = projData;
                a.browPullTable = browPullTable; a.hairItemId = "hair_bob_01_01";
                a.lightAtFront = lightAtFront; a.viewCamera = cam;
                a.Build();
                chars.Add(a);
            }
        }

        Vector3 Pivot(Race3DExprActor a) => (a.EyeL.position + a.EyeR.position) * 0.5f;

        void Place(Vector3 pivot, float yaw, float dist, float width)
        {
            Vector3 dirv = Quaternion.AngleAxis(sx * yaw, Vector3.up) * new Vector3(0, 0, front);
            cam.transform.position = pivot + dirv * dist;
            cam.transform.rotation = Quaternion.LookRotation(-dirv, Vector3.up);
            float aspect = (float)Screen.width / Screen.height;
            float h = 2f * Mathf.Atan(width * 0.5f / dist);
            cam.fieldOfView = 2f * Mathf.Atan(Mathf.Tan(h * 0.5f) / aspect) * Mathf.Rad2Deg;
        }

        string Apply(RS s)
        {
            if (urp == null) return "no URP";
            urp.msaaSampleCount = s.msaa;
            urp.renderScale = s.scale;
            var desc = new RenderTextureDescriptor(Mathf.RoundToInt(Screen.width * s.scale), Mathf.RoundToInt(Screen.height * s.scale), RenderTextureFormat.ARGB32, 24) { msaaSamples = s.msaa };
            int sup = SystemInfo.GetRenderTextureSupportedMSAASampleCount(desc);
            return $"{s.name}: msaa {urp.msaaSampleCount}, rs {urp.renderScale:F2}, device supports {sup}x for {desc.width}x{desc.height}";
        }

        IEnumerator CaptureShot(string name)
        {
            yield return null;
            yield return null;
            yield return null;
            if (hostCapture)
            {
                string ready = Path.Combine(dir, "shot_ready.txt"), done = Path.Combine(dir, "shots", name + ".done");
                File.WriteAllText(ready, name);
                float t0 = Time.realtimeSinceStartup;
                while (!File.Exists(done) && Time.realtimeSinceStartup - t0 < 45f) yield return null;
                if (File.Exists(ready)) File.Delete(ready);
                if (!File.Exists(done)) Log("host capture timed out: " + name);
                yield break;
            }
            yield return new WaitForEndOfFrame();
            var tex = ScreenCapture.CaptureScreenshotAsTexture();
            File.WriteAllBytes(Path.Combine(dir, "shots", name + ".png"), tex.EncodeToPNG());
            Destroy(tex);
        }

        IEnumerator Quality()
        {
            Spawn(1);
            yield return null;
            Apply(Settings[1]);
            Log("quality " + Apply(Settings[1]));
            var a = chars[0];
            // Happy 0.6..1.0 natural transition
            foreach (float h in new[] { 0.6f, 0.7f, 0.8f, 0.9f, 1.0f })
            {
                a.state = Race3DExprActor.St(happy: h);
                Place(Pivot(a), 0, 0.55f, 0.36f);
                yield return CaptureShot($"happy_{Mathf.RoundToInt(h * 100):000}_0");
                Place(Pivot(a), 35, 0.55f, 0.36f);
                yield return CaptureShot($"happy_{Mathf.RoundToInt(h * 100):000}_35");
            }
            // Angry2 (strong default) pull at 0 / +-35 / +-45 / +-60; weak Angry for comparison at 0/45
            foreach (var (tag, st) in new[] { ("angry2", Race3DExprActor.St(angry2: 1)), ("angry", Race3DExprActor.St(angry: 1)) })
            {
                a.state = st; a.browCards = true; a.hair = true;
                foreach (float yaw in new[] { 0f, 35f, -35f, 45f, -45f, 60f, -60f })
                {
                    if (tag == "angry" && Mathf.Abs(yaw) > 45.1f) continue;
                    Place(Pivot(a), yaw, 0.7f, 0.55f);
                    yield return CaptureShot($"{tag}_pull_{yaw:0}");
                }
            }
            // Cry flow steps (structure kept; cheek-curve path is a later animation stage)
            a.state = Race3DExprActor.St(sad: 1, cry: 1, flow: 0);
            foreach (float f in new[] { 0f, 0.25f, 0.5f, 0.75f, 1f })
            {
                a.state = Race3DExprActor.St(sad: 1, cry: 1, flow: f);
                Place(Pivot(a), 0, 0.7f, 0.55f);
                yield return CaptureShot($"cry_flow_{Mathf.RoundToInt(f * 100):000}_0");
                Place(Pivot(a), 35, 0.7f, 0.55f);
                yield return CaptureShot($"cry_flow_{Mathf.RoundToInt(f * 100):000}_35");
            }
            // Surprise iris/sparkle vs gaze and Blink
            foreach (var (tag, st) in new[]
                     {
                         ("s100_g0", Race3DExprActor.St(surprise: 1)),
                         ("s100_gL", Race3DExprActor.St(surprise: 1, gaze: 0.25f)),
                         ("s100_gR", Race3DExprActor.St(surprise: 1, gaze: -0.25f)),
                         ("s100_blink", Race3DExprActor.St(surprise: 1, blink: 1)),
                         ("s100_gR_b05", Race3DExprActor.St(surprise: 1, gaze: -0.25f, blink: 0.5f)),
                         ("s050_gL", Race3DExprActor.St(surprise: 0.5f, gaze: 0.25f)),
                     })
            {
                a.state = st;
                Place(Pivot(a), 0, 0.55f, 0.36f);
                yield return CaptureShot($"surprise_{tag}_0");
                Place(Pivot(a), 35, 0.55f, 0.36f);
                yield return CaptureShot($"surprise_{tag}_35");
            }
            Log($"quality done; surprise sparkle@{a.Sparkle:F2} iris@{a.IrisScale:F3} (blink1 expects sparkle 0)");
        }

        /// <summary>two actors, different emotions: mutable material values must not cross</summary>
        IEnumerator Isolation()
        {
            Spawn(2);
            yield return null;
            chars[0].transform.position = new Vector3(-0.35f, 0, 0);
            chars[1].transform.position = new Vector3(0.35f, 0, 0);
            chars[0].state = Race3DExprActor.St(surprise: 1, gaze: 0.25f);
            chars[1].state = Race3DExprActor.St(sad: 1, cry: 1, flow: 1);
            chars[0].browPullOverride = 0.03f;
            chars[1].browPullOverride = 0.045f;                          // different pull — must stay on actor1 only
            Place((Pivot(chars[0]) + Pivot(chars[1])) * 0.5f, 0, 0.9f, 0.9f);
            yield return null;
            yield return null;
            float s0 = chars[0].Sparkle, s1 = chars[1].Sparkle, i0 = chars[0].IrisScale, i1 = chars[1].IrisScale;
            float f0 = chars[0].Flow, f1 = chars[1].Flow, p0 = chars[0].BrowPullMeters, p1 = chars[1].BrowPullMeters;
            bool ok = s0 > 0.9f && s1 < 0.05f && i0 < 0.95f && i1 > 0.99f && f0 < 0.05f && f1 > 0.9f
                      && Mathf.Abs(p0 - 0.03f) < 1e-4f && Mathf.Abs(p1 - 0.045f) < 1e-4f
                      && !ReferenceEquals(chars[0].OwnedMaterials[0], chars[1].OwnedMaterials[0]);
            // also check eye material instances differ by reading _Sparkle from each
            float ms0 = chars[0].OwnedMaterials.First(m => m.HasProperty("_Sparkle")).GetFloat("_Sparkle");
            float ms1 = chars[1].OwnedMaterials.First(m => m.HasProperty("_Sparkle")).GetFloat("_Sparkle");
            float mp0 = chars[0].OwnedMaterials.First(m => m.HasProperty("_Pull")).GetFloat("_Pull");
            float mp1 = chars[1].OwnedMaterials.First(m => m.HasProperty("_Pull")).GetFloat("_Pull");
            ok = ok && Mathf.Abs(ms0 - s0) < 1e-4f && Mathf.Abs(ms1 - s1) < 1e-4f && Mathf.Abs(mp0 - p0) < 1e-4f && Mathf.Abs(mp1 - p1) < 1e-4f;
            Log($"ISOLATION ok={ok}: A sparkle {s0:F2}/iris {i0:F3}/flow {f0:F2}/pull {p0:F3} matS {ms0:F2} matP {mp0:F3}; " +
                $"B sparkle {s1:F2}/iris {i1:F3}/flow {f1:F2}/pull {p1:F3} matS {ms1:F2} matP {mp1:F3}");
            yield return CaptureShot("isolation_surprise_vs_cry");
            File.WriteAllText(Path.Combine(dir, "isolation.txt"), $"ok={ok}\nA sparkle={s0} iris={i0} flow={f0} pull={p0}\nB sparkle={s1} iris={i1} flow={f1} pull={p1}\n");
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
            long mb = 0, tb = 0;
            foreach (var m in meshes) mb += Profiler.GetRuntimeMemorySizeLong(m);
            foreach (var t in texs) tb += Profiler.GetRuntimeMemorySizeLong(t);
            int shapes = meshes.Sum(m => m.blendShapeCount);
            Log($"MEMORY one character: meshes {meshes.Count} = {mb / 1024.0:F0} KB, blend shapes {shapes}, textures {texs.Count} = {tb / 1024.0:F0} KB; " +
                $"process allocated {Profiler.GetTotalAllocatedMemoryLong() / 1048576.0:F1} MB, reserved {Profiler.GetTotalReservedMemoryLong() / 1048576.0:F1} MB, graphics {Profiler.GetAllocatedMemoryForGraphicsDriver() / 1048576.0:F1} MB");
        }

        void DriveExpr(float t)
        {
            // Angry2 (strong) as the angry segment; weak Angry is a short side beat
            float cycle = t % 14f;
            Race3DExprActor.State st;
            if (cycle < 2.5f) st = Race3DExprActor.St(happy: Mathf.Clamp01(cycle / 2.5f));
            else if (cycle < 5f) st = Race3DExprActor.St(angry2: Mathf.Clamp01((cycle - 2.5f) / 2.5f));
            else if (cycle < 6.5f) st = Race3DExprActor.St(angry: 1);
            else if (cycle < 9.5f) st = Race3DExprActor.St(sad: 1, cry: Mathf.Clamp01((cycle - 6.5f) / 1.5f));
            else if (cycle < 12f) st = Race3DExprActor.St(surprise: 1, gaze: 0.25f * Mathf.Sin(t * 2f));
            else st = Race3DExprActor.St();
            float blink = Mathf.Clamp01(1f - Mathf.Abs((t % 2.7f) - 0.12f) / 0.12f);
            st.blink = blink;
            foreach (var c in chars) c.state = st;
        }

        IEnumerator Measure(string label, float seconds, System.Action<float> drive)
        {
            var dt = new List<float>(); var main = new List<float>(); var cpu = new List<float>(); var gpu = new List<float>(); var eye = new List<float>();
            var timings = new FrameTiming[1];
            var skinRecs = new List<ProfilerRecorder>();
            var all = new List<ProfilerRecorderHandle>();
            ProfilerRecorderHandle.GetAvailable(all);
            foreach (var h in all)
            {
                var d = ProfilerRecorderHandle.GetDescription(h);
                if ((d.Name.Contains("Skin") || d.Name.Contains("BlendShape")) && d.UnitType == ProfilerMarkerDataUnit.TimeNanoseconds)
                    skinRecs.Add(ProfilerRecorder.StartNew(d.Category, d.Name, 4));
            }
            float t0 = Time.realtimeSinceStartup;
            while (Time.realtimeSinceStartup - t0 < 2f) { drive(Time.realtimeSinceStartup - t0); yield return null; }
            t0 = Time.realtimeSinceStartup;
            var csv = new StringBuilder("t,dt_ms,cpu_main_ms,cpu_frame_ms,gpu_ms,expr_us\n");
            float last = Time.realtimeSinceStartup;
            while (Time.realtimeSinceStartup - t0 < seconds)
            {
                drive(Time.realtimeSinceStartup - t0);
                yield return null;
                float now = Time.realtimeSinceStartup;
                float dti = (now - last) * 1000f; last = now;
                FrameTimingManager.CaptureFrameTimings();
                uint got = FrameTimingManager.GetLatestTimings(1, timings);
                float m = got > 0 ? (float)timings[0].cpuMainThreadFrameTime : -1f;
                float c = got > 0 ? (float)timings[0].cpuFrameTime : -1f;
                float g = got > 0 ? (float)timings[0].gpuFrameTime : -1f;
                float e = chars.Sum(x => x.LastCostMicroseconds);
                dt.Add(dti); main.Add(m); cpu.Add(c); gpu.Add(g); eye.Add(e);
                csv.AppendLine($"{now - t0:F3},{dti:F3},{m:F3},{c:F3},{g:F3},{e:F1}");
            }
            File.WriteAllText(Path.Combine(dir, $"perf_{label}.csv"), csv.ToString());
            float Avg(List<float> v) { double s = 0; int n = 0; foreach (var x in v) if (x >= 0) { s += x; n++; } return n > 0 ? (float)(s / n) : -1f; }
            float P95(List<float> v) { var a = v.FindAll(x => x >= 0); if (a.Count == 0) return -1f; a.Sort(); return a[Mathf.Min(a.Count - 1, (int)(a.Count * 0.95f))]; }
            float avg = Avg(dt);
            Log($"PERF {label}: frames {dt.Count}, fps {1000f / avg:F1}, frame ms avg {avg:F2} p95 {P95(dt):F2}, cpu main avg {Avg(main):F2} p95 {P95(main):F2}, " +
                $"cpu frame avg {Avg(cpu):F2}, gpu avg {Avg(gpu):F2} p95 {P95(gpu):F2}, expr drivers avg {Avg(eye):F1} us p95 {P95(eye):F1} us, " +
                $"allocated {Profiler.GetTotalAllocatedMemoryLong() / 1048576.0:F1} MB");
            foreach (var r in skinRecs) r.Dispose();
        }

        IEnumerator Perf()
        {
            Spawn(1);
            yield return null;
            Memory();
            foreach (var s in Settings)
            {
                Log("perf1 " + Apply(s));
                yield return Measure("1char_" + s.name, perfSeconds, t =>
                {
                    Place(Pivot(chars[0]), 60f * Mathf.Sin(t * Mathf.PI * 2f / 8f), 1.1f, 0.62f);
                    DriveExpr(t);
                });
            }
            Spawn(12);
            yield return null;
            Vector3 centre = new Vector3(0, Pivot(chars[0]).y - 1.125f, 0);
            void Drive12(float t)
            {
                float yaw = 60f * Mathf.Sin(t * Mathf.PI * 2f / 8f);
                foreach (var c in chars) c.transform.rotation = Quaternion.AngleAxis(-sx * yaw, Vector3.up);
                Place(centre, 0, 4.2f, 3.0f);
                DriveExpr(t);
            }
            foreach (var s in Settings)
            {
                Log("perf12 " + Apply(s));
                yield return Measure("12char_" + s.name, perfSeconds, Drive12);
            }
            Place(centre, 0, 4.2f, 3.0f);
            foreach (var c in chars) { c.state = Race3DExprActor.St(angry2: 1); c.transform.rotation = Quaternion.AngleAxis(-sx * 35f, Vector3.up); }
            yield return CaptureShot("perf12_angry2_35");
        }
    }
}
