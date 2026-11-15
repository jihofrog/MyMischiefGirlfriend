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
using MMG.Characters.Avatar3D;

namespace MMG.Experiments.Race3DFormal
{
    /// <summary>
    /// Android device test of the formal MainGirlfriend_Race3D_v1 prefab (ExpressionController + EyeViewController).
    /// Phases: quality, isolation, perf (short), soak (12 chars, long). hostcapture via shot_ready.txt.
    /// </summary>
    public sealed class FormalExprDeviceTest : MonoBehaviour
    {
        public GameObject formalPrefab;
        public float perfSeconds = 12f;
        public float soakSeconds = 780f; // 13 minutes

        struct RS { public string name; public int msaa; public float scale; }
        static readonly RS SettingC = new RS { name = "C_msaa4_rs080", msaa = 4, scale = 0.8f };

        string dir;
        Camera cam;
        readonly List<ExpressionController> chars = new List<ExpressionController>();
        UniversalRenderPipelineAsset urp;
        int origMsaa = 1;
        float origScale = 1f, sx = 1f, front = 1f;
        HashSet<string> phases;
        bool hostCapture;
        readonly StringBuilder logBuf = new StringBuilder();

        void Log(string s)
        {
            string line = $"[{Time.realtimeSinceStartup:F1}s f{Time.frameCount}] {s}";
            Debug.Log("[FormalExprDevice] " + line);
            logBuf.AppendLine(line);
            File.AppendAllText(Path.Combine(dir, "log.txt"), line + "\n");
        }

        void Awake()
        {
            dir = Path.Combine(Application.persistentDataPath, "formalexpr");
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
            string cfg = Path.Combine(Application.persistentDataPath, "formalexpr_phases.txt");
            if (string.IsNullOrEmpty(arg) && File.Exists(cfg))
            {
                var parts = File.ReadAllText(cfg).Trim().Split(';');
                arg = parts[0];
                foreach (var p in parts)
                {
                    if (p.StartsWith("perf=")) perfSeconds = float.Parse(p.Substring(5), System.Globalization.CultureInfo.InvariantCulture);
                    if (p.StartsWith("soak=")) soakSeconds = float.Parse(p.Substring(5), System.Globalization.CultureInfo.InvariantCulture);
                }
            }
            phases = new HashSet<string>(arg.Split(new[] { ',' }, System.StringSplitOptions.RemoveEmptyEntries));
            hostCapture = phases.Remove("hostcapture");
            if (phases.Count == 0) { phases.Add("quality"); phases.Add("isolation"); phases.Add("perf"); phases.Add("soak"); }
        }

        bool Want(string p) => phases.Contains(p);
        void OnDestroy() { if (urp != null) { urp.msaaSampleCount = origMsaa; urp.renderScale = origScale; } }

        IEnumerator Start()
        {
            var go = new GameObject("FormalExprCam") { tag = "MainCamera" };
            cam = go.AddComponent<Camera>();
            cam.clearFlags = CameraClearFlags.SolidColor;
            cam.backgroundColor = new Color(0.93f, 0.93f, 0.95f);
            cam.nearClipPlane = 0.02f; cam.farClipPlane = 50f; cam.allowMSAA = true;
            Log($"START device {SystemInfo.deviceModel}, OS {SystemInfo.operatingSystem}, GPU {SystemInfo.graphicsDeviceName} ({SystemInfo.graphicsDeviceType}), " +
                $"RAM {SystemInfo.systemMemorySize} MB, screen {Screen.width}x{Screen.height}, URP {(urp ? urp.name : "none")} msaa {origMsaa} rs {origScale:F2}, " +
                $"hostcapture {hostCapture}, phases [{string.Join(",", phases)}], soakSec {soakSeconds}");
            Spawn(1);
            yield return null;
            var eye = chars[0].GetComponent<EyeViewController>();
            sx = Mathf.Sign(Vector3.Dot(eye.characterLeftLocal, Vector3.right));
            front = Mathf.Sign(chars[0].GetComponent<EyeViewController>().faceForwardLocal.z);
            Log($"actor0 pull {chars[0].BrowPullMeters:F3} m mats {chars[0].OwnedMaterials.Count}");
            if (Want("quality")) yield return Quality();
            if (Want("isolation")) yield return Isolation();
            if (Want("perf")) yield return PerfShort();
            if (Want("soak")) yield return Soak();
            Log("ALL_DONE");
            File.WriteAllText(Path.Combine(dir, "done.txt"), "ok");
        }

        void Spawn(int n)
        {
            foreach (var c in chars) if (c != null) Destroy(c.gameObject);
            chars.Clear();
            for (int i = 0; i < n; i++)
            {
                var go = Instantiate(formalPrefab);
                go.name = $"FormalChar_{i}";
                if (n > 1)
                {
                    int col = i % 3, row = i / 3;
                    go.transform.position = new Vector3((col - 1) * 0.9f, -row * 0.75f, 0f);
                }
                var expr = go.GetComponent<ExpressionController>();
                var eye = go.GetComponent<EyeViewController>();
                eye.viewCamera = cam;
                expr.Build();
                chars.Add(expr);
            }
        }

        Vector3 Pivot(ExpressionController a)
        {
            var e = a.GetComponent<EyeViewController>();
            return (e.eyeL.position + e.eyeR.position) * 0.5f;
        }

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
            urp.msaaSampleCount = s.msaa; urp.renderScale = s.scale;
            return $"{s.name}: msaa {urp.msaaSampleCount}, rs {urp.renderScale:F2}";
        }

        IEnumerator CaptureShot(string name)
        {
            yield return null; yield return null; yield return null;
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
            Spawn(1); yield return null;
            Log("quality " + Apply(SettingC));
            var a = chars[0];
            foreach (float h in new[] { 0.6f, 0.8f, 1.0f })
            {
                a.state = ExpressionController.St(happy: h);
                Place(Pivot(a), 0, 0.55f, 0.36f); yield return CaptureShot($"happy_{Mathf.RoundToInt(h * 100):000}_0");
                Place(Pivot(a), 35, 0.55f, 0.36f); yield return CaptureShot($"happy_{Mathf.RoundToInt(h * 100):000}_35");
            }
            foreach (var (tag, st) in new[] { ("angry2", ExpressionController.St(angry2: 1)), ("angry", ExpressionController.St(angry: 1)) })
            {
                a.state = st;
                foreach (float yaw in new[] { 0f, 35f, -35f, 45f, -45f, 60f, -60f })
                {
                    if (tag == "angry" && Mathf.Abs(yaw) > 45.1f) continue;
                    Place(Pivot(a), yaw, 0.7f, 0.55f);
                    yield return CaptureShot($"{tag}_pull_{yaw:0}");
                }
            }
            foreach (var (tag, st) in new[]
                     {
                         ("sad", ExpressionController.St(sad: 1)),
                         ("cry", ExpressionController.St(sad: 1, cry: 1, flow: 1)),
                         ("surprise", ExpressionController.St(surprise: 1)),
                         ("surprise_gL", ExpressionController.St(surprise: 1, gaze: 0.25f)),
                         ("surprise_blink", ExpressionController.St(surprise: 1, blink: 1)),
                         ("conflict_aa2", ExpressionController.St(angry: 1, angry2: 1)),
                     })
            {
                a.state = st;
                Place(Pivot(a), 0, 0.55f, 0.36f); yield return CaptureShot($"{tag}_0");
                Place(Pivot(a), 35, 0.55f, 0.36f); yield return CaptureShot($"{tag}_35");
            }
            Log("quality done");
        }

        IEnumerator Isolation()
        {
            Spawn(2); yield return null;
            chars[0].transform.position = new Vector3(-0.35f, 0, 0);
            chars[1].transform.position = new Vector3(0.35f, 0, 0);
            chars[0].state = ExpressionController.St(surprise: 1, gaze: 0.25f);
            chars[1].state = ExpressionController.St(sad: 1, cry: 1, flow: 1);
            chars[0].browPullOverride = 0.03f;
            chars[1].browPullOverride = 0.045f;
            Place((Pivot(chars[0]) + Pivot(chars[1])) * 0.5f, 0, 0.9f, 0.9f);
            yield return null; yield return null;
            bool ok = chars[0].Sparkle > 0.9f && chars[1].Sparkle < 0.05f
                      && chars[0].Flow < 0.05f && chars[1].Flow > 0.9f
                      && !ReferenceEquals(chars[0].OwnedMaterials[0], chars[1].OwnedMaterials[0]);
            Log($"ISOLATION ok={ok}");
            File.WriteAllText(Path.Combine(dir, "isolation.txt"), $"ok={ok}\n");
            yield return CaptureShot("isolation_formal");
        }

        void DriveExpr(float t)
        {
            float cycle = t % 14f;
            ExpressionController.State st;
            if (cycle < 2.5f) st = ExpressionController.St(happy: Mathf.Clamp01(cycle / 2.5f));
            else if (cycle < 5f) st = ExpressionController.St(angry2: Mathf.Clamp01((cycle - 2.5f) / 2.5f));
            else if (cycle < 6.5f) st = ExpressionController.St(angry: 1);
            else if (cycle < 9.5f) st = ExpressionController.St(sad: 1, cry: Mathf.Clamp01((cycle - 6.5f) / 1.5f));
            else if (cycle < 12f) st = ExpressionController.St(surprise: 1, gaze: 0.25f * Mathf.Sin(t * 2f));
            else st = ExpressionController.St();
            st.blink = Mathf.Clamp01(1f - Mathf.Abs((t % 2.7f) - 0.12f) / 0.12f);
            foreach (var c in chars) c.state = st;
        }

        IEnumerator Measure(string label, float seconds, System.Action<float> drive)
        {
            var dt = new List<float>(); var main = new List<float>(); var gpu = new List<float>(); var eye = new List<float>();
            var timings = new FrameTiming[1];
            float t0 = Time.realtimeSinceStartup;
            while (Time.realtimeSinceStartup - t0 < 2f) { drive(Time.realtimeSinceStartup - t0); yield return null; }
            t0 = Time.realtimeSinceStartup;
            var csv = new StringBuilder("t,dt_ms,cpu_main_ms,gpu_ms,expr_us,alloc_mb\n");
            float last = Time.realtimeSinceStartup;
            float nextMem = 0f;
            while (Time.realtimeSinceStartup - t0 < seconds)
            {
                drive(Time.realtimeSinceStartup - t0);
                yield return null;
                float now = Time.realtimeSinceStartup;
                float dti = (now - last) * 1000f; last = now;
                FrameTimingManager.CaptureFrameTimings();
                uint got = FrameTimingManager.GetLatestTimings(1, timings);
                float m = got > 0 ? (float)timings[0].cpuMainThreadFrameTime : -1f;
                float g = got > 0 ? (float)timings[0].gpuFrameTime : -1f;
                float e = chars.Sum(x => x.LastCostMicroseconds);
                dt.Add(dti); main.Add(m); gpu.Add(g); eye.Add(e);
                float alloc = Profiler.GetTotalAllocatedMemoryLong() / 1048576f;
                if (now - t0 >= nextMem)
                {
                    csv.AppendLine($"{now - t0:F3},{dti:F3},{m:F3},{g:F3},{e:F1},{alloc:F1}");
                    nextMem = now - t0 + 1f;
                }
                else csv.AppendLine($"{now - t0:F3},{dti:F3},{m:F3},{g:F3},{e:F1},{alloc:F1}");
            }
            File.WriteAllText(Path.Combine(dir, $"perf_{label}.csv"), csv.ToString());
            float Avg(List<float> v) { double s = 0; int n = 0; foreach (var x in v) if (x >= 0) { s += x; n++; } return n > 0 ? (float)(s / n) : -1f; }
            float P95(List<float> v) { var a = v.FindAll(x => x >= 0); if (a.Count == 0) return -1f; a.Sort(); return a[Mathf.Min(a.Count - 1, (int)(a.Count * 0.95f))]; }
            float avg = Avg(dt);
            Log($"PERF {label}: frames {dt.Count}, fps {1000f / avg:F1}, frame ms avg {avg:F2} p95 {P95(dt):F2}, " +
                $"cpu main avg {Avg(main):F2} p95 {P95(main):F2}, gpu avg {Avg(gpu):F2} p95 {P95(gpu):F2}, " +
                $"expr avg {Avg(eye):F1} us, alloc {Profiler.GetTotalAllocatedMemoryLong() / 1048576.0:F1} MB");
        }

        IEnumerator PerfShort()
        {
            Spawn(1); yield return null;
            Log("perf1 " + Apply(SettingC));
            yield return Measure("1char_C_short12s", perfSeconds, t =>
            {
                Place(Pivot(chars[0]), 60f * Mathf.Sin(t * Mathf.PI * 2f / 8f), 1.1f, 0.62f);
                DriveExpr(t);
            });
            Spawn(12); yield return null;
            Vector3 centre = new Vector3(0, Pivot(chars[0]).y - 1.125f, 0);
            Log("perf12 " + Apply(SettingC));
            yield return Measure("12char_C_short12s", perfSeconds, t =>
            {
                float yaw = 60f * Mathf.Sin(t * Mathf.PI * 2f / 8f);
                foreach (var c in chars) c.transform.rotation = Quaternion.AngleAxis(-sx * yaw, Vector3.up);
                Place(centre, 0, 4.2f, 3.0f);
                DriveExpr(t);
            });
            yield return CaptureShot("perf12_short_end");
        }

        IEnumerator Soak()
        {
            Spawn(12); yield return null;
            Vector3 centre = new Vector3(0, Pivot(chars[0]).y - 1.125f, 0);
            Log("SOAK start " + Apply(SettingC) + $" duration {soakSeconds:F0}s");
            File.WriteAllText(Path.Combine(dir, "soak_start.txt"), System.DateTime.UtcNow.ToString("o"));
            yield return Measure("12char_C_soak", soakSeconds, t =>
            {
                float yaw = 60f * Mathf.Sin(t * Mathf.PI * 2f / 8f);
                foreach (var c in chars) c.transform.rotation = Quaternion.AngleAxis(-sx * yaw, Vector3.up);
                Place(centre, 0, 4.2f, 3.0f);
                DriveExpr(t);
            });
            File.WriteAllText(Path.Combine(dir, "soak_end.txt"), System.DateTime.UtcNow.ToString("o"));
            yield return CaptureShot("soak_12char_end");
            Log("SOAK done");
        }
    }
}
