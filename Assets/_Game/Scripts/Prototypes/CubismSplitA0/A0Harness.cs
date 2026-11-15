using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using Live2D.Cubism.Core;
using Live2D.Cubism.Rendering;
using Unity.Profiling;
using UnityEngine;

namespace MMG.Prototypes.CubismSplit
{
    /// <summary>
    /// A0 prototype runner (05 document 17-1): one reference model ("Single") beside a split pair at the origin
    /// ("Body" without the blouse + "Blouse" with only the blouse), all three instances of the same imported model.
    /// Drives poses, captures the reference and the pair with identical camera framing, logs parameter / vertex
    /// differences, sorting variations, a mask case, independent physics, draw calls, CPU time and memory.
    /// Proves nothing about separate moc3 files (A1).
    /// </summary>
    [DefaultExecutionOrder(-1000)]
    public sealed class A0Harness : MonoBehaviour
    {
        public CubismModel Single;
        public CubismModel Body;
        public CubismModel Blouse;
        public A0DrawableFilter BodyFilter;
        public A0DrawableFilter BlouseFilter;
        public A0ParameterMirror Mirror;
        public GameObject PrefabForMemoryTest;
        public string OutputDir;
        public int SettleFrames = 120;

        [Header("Run 2")]
        /// <summary>Second full reference model (control): Single vs Single2 shows the noise from placement alone.</summary>
        public CubismModel Single2;
        public A0ParamProbe Probe;
        public bool AllStaticPoses = true;
        public bool DoVariations = true;
        public bool DoMask = true;
        public bool DoIndependent = true;

        public static readonly string[] BlouseIds =
        {
            "Blouse", "Blouse_AI", "Blouse_Ext", "Top_Blouse_Bust", "Shoulder_L", "Shoulder_R",
            "Sleeve_Cuff_L", "Sleeve_Cuff_R", "UpperArm_Sleeve_L", "UpperArm_Sleeve_R"
        };

        static readonly string[] MaskedEyeIds =
        {
            "Iris_L", "Iris_L_AI", "Iris_Rim_L", "Pupil_L", "EyeHighlight_L",
            "Iris_R", "Iris_R_AI", "Iris_Rim_R", "Pupil_R", "EyeHighlight_R"
        };

        static readonly string[] EyeWhiteIds = { "EyeWhite_L", "EyeWhite_L_AI", "EyeWhite_Clean_L", "EyeWhite_R", "EyeWhite_R_AI", "EyeWhite_Clean_R" };

        Dictionary<string, float> pose = new Dictionary<string, float>();
        StreamWriter log;
        Rect fullRegion, torsoRegion, faceRegion;   // in model-local world units, model at origin
        Vector3 singleOffset;
        readonly List<ProfilerRecorder> recorders = new List<ProfilerRecorder>();
        readonly List<string> recorderNames = new List<string>();
        int frame;

        public bool Done { get; private set; }

        // ---------------------------------------------------------------- pose driving

        void Update()
        {
            frame++;
            Apply(Single);
            Apply(Single2);
            Apply(Body);
            if (Mirror != null && !Mirror.Mirror) Apply(Blouse);
        }

        void Apply(CubismModel m)
        {
            if (m == null || !m.isActiveAndEnabled) return;
            foreach (var p in m.Parameters) p.Value = pose.TryGetValue(p.Id, out var v) ? v : p.DefaultValue;
        }

        /// <summary>Value from a fraction of the range: +1 = maximum, -1 = minimum, 0 = default.</summary>
        float Frac(string id, float f)
        {
            foreach (var p in Body.Parameters)
                if (p.Id == id)
                    return f >= 0 ? p.DefaultValue + (p.MaximumValue - p.DefaultValue) * f : p.DefaultValue + (p.DefaultValue - p.MinimumValue) * f;
            throw new ArgumentException("no parameter " + id);
        }

        Dictionary<string, float> Pose(params (string id, float frac)[] values)
        {
            var d = new Dictionary<string, float>();
            foreach (var (id, f) in values) d[id] = Frac(id, f);
            return d;
        }

        Dictionary<string, float> Dynamic(int f)
        {
            float t = f / 120f * 2f * Mathf.PI;
            return Pose(("ParamAngleX", Mathf.Sin(t)), ("ParamAngleY", 0.6f * Mathf.Sin(t * 0.5f)), ("ParamAngleZ", 0.7f * Mathf.Sin(t * 1.5f)),
                ("ParamBodyAngleX", Mathf.Sin(t + 1f)), ("ParamBodyAngleZ", 0.8f * Mathf.Sin(t * 0.75f)), ("ParamBreath", 0.5f + 0.5f * Mathf.Sin(t * 2f)));
        }

        // ---------------------------------------------------------------- run

        IEnumerator Start()
        {
            Directory.CreateDirectory(OutputDir);
            log = new StreamWriter(Path.Combine(OutputDir, "a0_log.jsonl"), false, new UTF8Encoding(false));
            StartRecorders();
            yield return Frames(10);

            singleOffset = Single.transform.position - Body.transform.position;
            fullRegion = BoundsOf(Body, null, 0.02f);
            torsoRegion = BoundsOf(Blouse, BlouseIds, 0.12f);
            faceRegion = BoundsOf(Body, new[] { "Head_Skin" }, 0.02f);
            var rc = Body.GetComponent<CubismRenderController>();
            Log("setup", "\"idsMatch\":" + B(Mirror.IdsMatch) + ",\"drawables\":" + Body.Drawables.Length + ",\"parameters\":" + Body.Parameters.Length +
                ",\"parts\":" + Body.Parts.Length + ",\"sortingMode\":\"" + rc.SortingMode + "\",\"sortingOrder\":" + rc.SortingOrder +
                ",\"groupedSortingIndex\":" + rc.GroupedSortingIndex + ",\"depthOffset\":" + F(rc.DepthOffset) +
                ",\"recorders\":" + RecorderValidity() + ",\"unity\":\"" + Application.unityVersion + "\"");

            var poses = new List<(string name, Dictionary<string, float> p)>
            {
                ("default", Pose()),
                ("angleX_max", Pose(("ParamAngleX", 1))), ("angleX_min", Pose(("ParamAngleX", -1))),
                ("angleY_max", Pose(("ParamAngleY", 1))), ("angleY_min", Pose(("ParamAngleY", -1))),
                ("angleZ_max", Pose(("ParamAngleZ", 1))), ("angleZ_min", Pose(("ParamAngleZ", -1))),
                ("angleXY_max", Pose(("ParamAngleX", 1), ("ParamAngleY", 1))),
                ("bodyX_max", Pose(("ParamBodyAngleX", 1))), ("bodyX_min", Pose(("ParamBodyAngleX", -1))),
                ("bodyY_max", Pose(("ParamBodyAngleY", 1))), ("bodyY_min", Pose(("ParamBodyAngleY", -1))),
                ("bodyZ_max", Pose(("ParamBodyAngleZ", 1))), ("bodyZ_min", Pose(("ParamBodyAngleZ", -1))),
                ("breath_max", Pose(("ParamBreath", 1))),
                ("combo", Pose(("ParamAngleX", 1), ("ParamAngleY", -1), ("ParamBodyAngleX", -1), ("ParamBodyAngleZ", 1), ("ParamBreath", 1))),
                ("eyesClosed_smile", Pose(("ParamEyeLOpen", -1), ("ParamEyeROpen", -1), ("ParamMouthForm", 1)))
            };
            var quick = new HashSet<string> { "default", "angleX_min", "combo", "eyesClosed_smile" };
            foreach (var (name, p) in poses)
            {
                if (!AllStaticPoses && !quick.Contains(name)) continue;
                pose = p;
                yield return Frames(SettleFrames);
                Capture("static_" + name, true);
                if (Single2 != null) CaptureControl("control_" + name);
            }

            // Motion with physics (mirrored): captures in the middle of the movement.
            var dynCaptures = new HashSet<int> { 30, 75, 150, 210 };
            for (int f = 0; f < 240; f++)
            {
                pose = Dynamic(f);
                yield return null;
                LogDiffs("dyn_mirror_frame", f);
                if (dynCaptures.Contains(f))
                {
                    Capture("dyn_mirror_" + f.ToString("000"), true);
                    if (Single2 != null) CaptureControl("control_dyn_" + f.ToString("000"));
                }
            }

            pose = Pose();
            yield return Frames(SettleFrames);
            if (DoVariations) yield return Variations();
            if (DoMask) yield return MaskCase();
            if (DoIndependent) yield return Independent(dynCaptures);

            yield return Performance();
            yield return Memory();

            Log("done", "\"frames\":" + frame);
            log.Flush();
            log.Close();
            log = null;
            foreach (var r in recorders) r.Dispose();
            recorders.Clear();
            File.WriteAllText(Path.Combine(OutputDir, "done.txt"), "ok " + DateTime.Now.ToString("o", CultureInfo.InvariantCulture));
            Done = true;
        }

        IEnumerator Variations()
        {
            var bodyRc = Body.GetComponent<CubismRenderController>();
            var blouseRc = Blouse.GetComponent<CubismRenderController>();
            var singleRc = Single.GetComponent<CubismRenderController>();
            blouseRc.GroupedSortingIndex = 1;
            yield return Frames(3);
            Capture("var_blouseGroup1", false);
            blouseRc.GroupedSortingIndex = 0;
            blouseRc.SortingOrder = 200;
            yield return Frames(3);
            Capture("var_blouseSortingOrder200", false);
            blouseRc.SortingOrder = 0;
            bodyRc.SortingMode = CubismSortingMode.BackToFrontOrder;
            blouseRc.SortingMode = CubismSortingMode.BackToFrontOrder;
            singleRc.SortingMode = CubismSortingMode.BackToFrontOrder;
            yield return Frames(3);
            Capture("var_backToFrontOrder", false);
            bodyRc.SortingMode = CubismSortingMode.BackToFrontZ;
            blouseRc.SortingMode = CubismSortingMode.BackToFrontZ;
            singleRc.SortingMode = CubismSortingMode.BackToFrontZ;
            yield return Frames(3);
            Capture("var_restored", false);
        }

        IEnumerator MaskCase()
        {
            // Mask case: masked eye parts drawn by the blouse model whose own mask sources (eye whites) are hidden.
            var bodyHide = new List<string>(BlouseIds);
            bodyHide.AddRange(MaskedEyeIds);
            BodyFilter.Set(A0DrawableFilter.FilterMode.HideListed, bodyHide);
            var blouseShow = new List<string>(BlouseIds);
            blouseShow.AddRange(MaskedEyeIds);
            BlouseFilter.Reveal(MaskedEyeIds);
            BlouseFilter.Set(A0DrawableFilter.FilterMode.ShowOnlyListed, blouseShow);
            yield return Frames(3);
            CaptureRegion("mask_eyesFromBlouseModel", faceRegion, 1024, 1024);
            // Control: what the masked parts look like with no mask at all (mask sources of both models hidden is
            // not possible to show directly, so record the eye white drawables' own visibility state instead).
            Log("mask_state", "\"blouseModelEyeWhitesHidden\":" + B(AllHidden(Blouse, EyeWhiteIds)) + ",\"bodyModelIrisHidden\":" + B(AllHidden(Body, MaskedEyeIds)));
            BodyFilter.Reveal(MaskedEyeIds);
            BodyFilter.Set(A0DrawableFilter.FilterMode.HideListed, BlouseIds);
            BlouseFilter.Set(A0DrawableFilter.FilterMode.ShowOnlyListed, BlouseIds);
            yield return Frames(3);
            Capture("mask_restored", false);
        }

        IEnumerator Independent(HashSet<int> dynCaptures)
        {
            // Independent physics: the blouse model runs its own physics from the same inputs (no copying).
            Mirror.SetMirror(false);
            yield return Frames(SettleFrames);
            LogDiffs("indep_settled", 0);
            Capture("indep_default", false);
            for (int f = 0; f < 240; f++)
            {
                pose = Dynamic(f);
                yield return null;
                LogDiffs("dyn_indep_frame", f);
                if (dynCaptures.Contains(f)) Capture("dyn_indep_" + f.ToString("000"), true);
            }
            Mirror.SetMirror(true);
            pose = Pose();
            yield return Frames(SettleFrames);
        }

        static IEnumerator Frames(int n)
        {
            for (int i = 0; i < n; i++) yield return null;
        }

        // ---------------------------------------------------------------- capture

        void Capture(string name, bool withTorso)
        {
            LogDiffs(name, 0);
            CaptureRegion(name + "_full", fullRegion, 768, Mathf.RoundToInt(768 * fullRegion.height / fullRegion.width));
            if (withTorso) CaptureRegion(name + "_torso", torsoRegion, 1024, 1024);
        }

        /// <summary>Single (x = +3) vs Single2 (x = -3): two full models, so any difference is placement noise.</summary>
        void CaptureControl(string name)
        {
            int w = 768, h = Mathf.RoundToInt(768 * fullRegion.height / fullRegion.width);
            RenderTo(Path.Combine(OutputDir, name + "_full_single.png"), fullRegion, singleOffset, w, h);
            RenderTo(Path.Combine(OutputDir, name + "_full_split.png"), fullRegion, Single2.transform.position - Body.transform.position, w, h);
            RenderTo(Path.Combine(OutputDir, name + "_torso_single.png"), torsoRegion, singleOffset, 1024, 1024);
            RenderTo(Path.Combine(OutputDir, name + "_torso_split.png"), torsoRegion, Single2.transform.position - Body.transform.position, 1024, 1024);
        }

        void CaptureRegion(string name, Rect region, int w, int h)
        {
            RenderTo(Path.Combine(OutputDir, name + "_single.png"), region, singleOffset, w, h);
            RenderTo(Path.Combine(OutputDir, name + "_split.png"), region, Vector3.zero, w, h);
        }

        void RenderTo(string path, Rect region, Vector3 offset, int w, int h)
        {
            var cam = Camera.main;
            var prevPos = cam.transform.position;
            var prevSize = cam.orthographicSize;
            var prevTarget = cam.targetTexture;
            var rt = new RenderTexture(w, h, 24, RenderTextureFormat.ARGB32);
            var tex = new Texture2D(w, h, TextureFormat.RGBA32, false);
            cam.transform.position = new Vector3(region.center.x + offset.x, region.center.y + offset.y, prevPos.z);
            cam.orthographicSize = region.height * 0.5f;
            cam.targetTexture = rt;
            cam.aspect = (float)w / h;
            cam.Render();
            RenderTexture.active = rt;
            tex.ReadPixels(new Rect(0, 0, w, h), 0, 0);
            tex.Apply();
            RenderTexture.active = null;
            File.WriteAllBytes(path, tex.EncodeToPNG());
            cam.targetTexture = prevTarget;
            cam.ResetAspect();
            cam.orthographicSize = prevSize;
            cam.transform.position = prevPos;
            rt.Release();
            Destroy(rt);
            Destroy(tex);
        }

        static Rect BoundsOf(CubismModel m, string[] ids, float margin)
        {
            var set = ids == null ? null : new HashSet<string>(ids);
            bool any = false;
            var b = new Bounds();
            foreach (var d in m.Drawables)
            {
                if (set != null && !set.Contains(d.name)) continue;
                var r = d.GetComponent<MeshRenderer>();
                if (r == null) continue;
                if (!any) { b = r.bounds; any = true; } else b.Encapsulate(r.bounds);
            }
            var c = b.center - m.transform.position;
            float half = Mathf.Max(b.extents.x, b.extents.y / 1.0f) * (1 + margin);
            float halfW = set == null ? b.extents.x * (1 + margin) : half;
            float halfH = set == null ? b.extents.y * (1 + margin) : half;
            return new Rect(c.x - halfW, c.y - halfH, halfW * 2, halfH * 2);
        }

        static bool AllHidden(CubismModel m, string[] ids)
        {
            var set = new HashSet<string>(ids);
            foreach (var d in m.Drawables)
                if (set.Contains(d.name) && d.GetComponent<MeshRenderer>().enabled) return false;
            return true;
        }

        // ---------------------------------------------------------------- differences

        void LogDiffs(string tag, int f)
        {
            float pSingleBody = MaxParamDiff(Single, Body, out string pSB);
            float pBodyBlouse = MaxParamDiff(Body, Blouse, out string pBB);
            var blouseSet = new HashSet<string>(BlouseIds);
            float vBody = 0, vBlouse = 0;
            string vBodyId = "", vBlouseId = "";
            for (int i = 0; i < Single.Drawables.Length; i++)
            {
                var a = Single.Drawables[i].VertexPositions;
                bool isBlouse = blouseSet.Contains(Single.Drawables[i].name);
                var other = (isBlouse ? Blouse : Body).Drawables[i].VertexPositions;
                float d = 0;
                for (int k = 0; k < a.Length; k++) d = Mathf.Max(d, (a[k] - other[k]).magnitude);
                if (isBlouse && d > vBlouse) { vBlouse = d; vBlouseId = Single.Drawables[i].name; }
                if (!isBlouse && d > vBody) { vBody = d; vBodyId = Single.Drawables[i].name; }
            }
            string probe = Probe == null ? "" :
                ",\"lateParamSingleVsBody\":" + F(Probe.SingleVsBody) + ",\"lateParamSingleVsBodyId\":\"" + Probe.SingleVsBodyId + "\"" +
                ",\"lateParamBodyVsBlouse\":" + F(Probe.BodyVsBlouse) + ",\"lateParamBodyVsBlouseId\":\"" + Probe.BodyVsBlouseId + "\"";
            Log(tag, "\"frame\":" + f + probe + ",\"paramSingleVsBody\":" + F(pSingleBody) + ",\"paramSingleVsBodyId\":\"" + pSB + "\"" +
                     ",\"paramBodyVsBlouse\":" + F(pBodyBlouse) + ",\"paramBodyVsBlouseId\":\"" + pBB + "\"" +
                     ",\"vertexBodyDrawables\":" + F(vBody) + ",\"vertexBodyId\":\"" + vBodyId + "\"" +
                     ",\"vertexBlouseDrawables\":" + F(vBlouse) + ",\"vertexBlouseId\":\"" + vBlouseId + "\"");
        }

        static float MaxParamDiff(CubismModel a, CubismModel b, out string id)
        {
            float max = 0;
            id = "";
            for (int i = 0; i < a.Parameters.Length; i++)
            {
                float d = Mathf.Abs(a.Parameters[i].Value - b.Parameters[i].Value);
                if (d > max) { max = d; id = a.Parameters[i].Id; }
            }
            return max;
        }

        // ---------------------------------------------------------------- performance and memory

        void StartRecorders()
        {
            void Add(ProfilerCategory cat, string name)
            {
                recorders.Add(ProfilerRecorder.StartNew(cat, name, 1));
                recorderNames.Add(name);
            }
            Add(ProfilerCategory.Internal, "Main Thread");
            Add(ProfilerCategory.Scripts, "PreLateUpdate.ScriptRunBehaviourLateUpdate");
            Add(ProfilerCategory.Render, "Draw Calls Count");
            Add(ProfilerCategory.Render, "Batches Count");
            Add(ProfilerCategory.Render, "SetPass Calls Count");
            Add(ProfilerCategory.Render, "Vertices Count");
            Add(ProfilerCategory.Memory, "Total Used Memory");
            Add(ProfilerCategory.Memory, "GC Used Memory");
            Add(ProfilerCategory.Memory, "Mesh Memory");
            Add(ProfilerCategory.Memory, "Texture Memory");
            // Cubism's own player-loop entries (schedule after PreLateUpdate, complete in PreUpdate); names are guesses.
            Add(ProfilerCategory.Scripts, "PreLateUpdate.CubismModel");
            Add(ProfilerCategory.Scripts, "PreUpdate.CubismModel");
            Add(ProfilerCategory.Scripts, "CubismModel");
        }

        string RecorderValidity()
        {
            var sb = new StringBuilder("{");
            for (int i = 0; i < recorders.Count; i++)
                sb.Append(i > 0 ? "," : "").Append('"').Append(recorderNames[i]).Append("\":").Append(B(recorders[i].Valid));
            return sb.Append('}').ToString();
        }

        IEnumerator Performance()
        {
            // The measured configuration is moved to the camera centre; everything else is deactivated.
            var singlePos = Single.transform.position;
            var configs = new (string name, bool single, bool pair, bool unfilteredPair)[]
            {
                ("singleOnly", true, false, false),
                ("splitPair", false, true, false),
                ("singleOnly_again", true, false, false),
                ("splitPair_again", false, true, false),
                ("twoFullModels", false, true, true),
            };
            foreach (var cfg in configs)
            {
                Single.transform.position = cfg.single ? Body.transform.position : singlePos;
                Single.gameObject.SetActive(cfg.single);
                if (Single2 != null) Single2.gameObject.SetActive(false);
                Body.gameObject.SetActive(cfg.pair);
                Blouse.gameObject.SetActive(cfg.pair);
                if (cfg.unfilteredPair)
                {
                    BodyFilter.enabled = false;
                    BlouseFilter.enabled = false;
                    BodyFilter.Reveal(BlouseIds);
                    BlouseFilter.Reveal(AllIds(Blouse));
                }
                yield return Frames(60);
                var sums = new double[recorders.Count];
                int n = 300;
                for (int i = 0; i < n; i++)
                {
                    yield return null;
                    for (int r = 0; r < recorders.Count; r++) sums[r] += recorders[r].LastValue;
                }
                var sb = new StringBuilder("\"config\":\"" + cfg.name + "\",\"frames\":" + n);
                for (int r = 0; r < recorders.Count; r++)
                    sb.Append(",\"").Append(recorderNames[r]).Append("\":").Append(F(sums[r] / n));
                sb.Append(",\"enabledRenderers\":").Append(EnabledRenderers(Single) + EnabledRenderers(Body) + EnabledRenderers(Blouse));
                sb.Append(",\"activeModels\":").Append((cfg.single ? 1 : 0) + (cfg.pair ? 2 : 0));
                Log("perf", sb.ToString());
            }
            Single.transform.position = singlePos;
            Single.gameObject.SetActive(true);
            if (Single2 != null) Single2.gameObject.SetActive(true);
            Body.gameObject.SetActive(true);
            Blouse.gameObject.SetActive(true);
            BodyFilter.enabled = true;
            BlouseFilter.enabled = true;
        }

        static int EnabledRenderers(CubismModel m)
        {
            if (m == null || !m.gameObject.activeInHierarchy) return 0;
            int n = 0;
            foreach (var d in m.Drawables)
            {
                var r = d.GetComponent<MeshRenderer>();
                if (r != null && r.enabled) n++;
            }
            return n;
        }

        static List<string> AllIds(CubismModel m)
        {
            var list = new List<string>();
            foreach (var d in m.Drawables) list.Add(d.name);
            return list;
        }

        IEnumerator Memory()
        {
            string Sample(string tag)
            {
                var sb = new StringBuilder("\"step\":\"" + tag + "\"");
                for (int r = 0; r < recorders.Count; r++)
                    if (recorderNames[r].Contains("Memory")) sb.Append(",\"").Append(recorderNames[r]).Append("\":").Append(recorders[r].LastValue);
                sb.Append(",\"totalAllocated\":").Append(UnityEngine.Profiling.Profiler.GetTotalAllocatedMemoryLong());
                sb.Append(",\"monoUsed\":").Append(UnityEngine.Profiling.Profiler.GetMonoUsedSizeLong());
                return sb.ToString();
            }

            GC.Collect();
            yield return Frames(30);
            Log("memory", Sample("before_extra_instance"));
            var extra = Instantiate(PrefabForMemoryTest, new Vector3(6f, 0f, 0f), Quaternion.identity);
            yield return Frames(60);
            Log("memory", Sample("with_extra_instance"));

            long meshBytes = 0;
            int meshes = 0, sharedTextures = 0, sharedMaterials = 0;
            var singleTex = Single.Drawables[0].GetComponent<CubismRenderer>().MainTexture;
            foreach (var mf in extra.GetComponentsInChildren<MeshFilter>(true))
            {
                if (mf.sharedMesh == null) continue;
                meshes++;
                meshBytes += UnityEngine.Profiling.Profiler.GetRuntimeMemorySizeLong(mf.sharedMesh);
            }
            var singleMats = new HashSet<Material>();
            foreach (var r in Single.GetComponentsInChildren<MeshRenderer>(true)) singleMats.Add(r.sharedMaterial);
            foreach (var r in extra.GetComponentsInChildren<CubismRenderer>(true))
            {
                if (r.MainTexture == singleTex) sharedTextures++;
                if (r.MeshRenderer != null && singleMats.Contains(r.MeshRenderer.sharedMaterial)) sharedMaterials++;
            }
            var meshSet = new HashSet<Mesh>();
            foreach (var mf in Single.GetComponentsInChildren<MeshFilter>(true)) if (mf.sharedMesh != null) meshSet.Add(mf.sharedMesh);
            int sharedMeshes = 0;
            foreach (var mf in extra.GetComponentsInChildren<MeshFilter>(true)) if (mf.sharedMesh != null && meshSet.Contains(mf.sharedMesh)) sharedMeshes++;
            Log("memory_instance", "\"meshes\":" + meshes + ",\"meshBytes\":" + meshBytes + ",\"meshesSharedWithSingle\":" + sharedMeshes +
                ",\"renderersUsingSameTexture\":" + sharedTextures + ",\"renderersUsingSameMaterial\":" + sharedMaterials +
                ",\"textureBytes\":" + UnityEngine.Profiling.Profiler.GetRuntimeMemorySizeLong(singleTex));

            Destroy(extra);
            yield return Frames(30);
            GC.Collect();
            yield return Frames(30);
            Log("memory", Sample("after_destroy"));
        }

        // ---------------------------------------------------------------- log helpers

        void Log(string kind, string body)
        {
            log?.WriteLine("{\"kind\":\"" + kind + "\",\"t\":" + frame + (body.Length > 0 ? "," + body : "") + "}");
            log?.Flush();
        }

        static string F(double v) => v.ToString("R", CultureInfo.InvariantCulture);
        static string B(bool v) => v ? "true" : "false";

        void OnDestroy()
        {
            log?.Close();
            foreach (var r in recorders) r.Dispose();
        }
    }
}
