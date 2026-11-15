using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using Live2D.Cubism.Core;
using Live2D.Cubism.Rendering;
using MMG.Prototypes.CubismSplit;
using Unity.Profiling;
using UnityEngine;

namespace MMG.Prototypes.CubismSplitA1
{
    /// <summary>
    /// A1 prototype runner (05 document 17-5): the r28 model ("Single", x = +3) beside a pair of separate moc3 files
    /// exported from copies of r28 at the origin ("Body" without the blouse, "Blouse" with only the blouse meshes).
    /// Drawables, parameters and parts are matched by ID. Captures sorting variations (with and without the master
    /// order map), static poses, motion, independent physics; measures draw calls, CPU and memory for the single
    /// model, the A0 pair (two r28 instances with renderers filtered) and the A1 pair.
    /// </summary>
    [DefaultExecutionOrder(-1000)]
    public sealed class A1Harness : MonoBehaviour
    {
        public CubismModel Single;
        public CubismModel Body;
        public CubismModel Blouse;
        public A1ParameterMirror Mirror;
        public A1SortingMap BodyMap;
        public A1SortingMap BlouseMap;
        public A1ParamProbe Probe;
        public GameObject SinglePrefab;
        public GameObject BodyPrefab;
        public GameObject BlousePrefab;
        public string OutputDir;
        public int SettleFrames = 120;

        static readonly string[] BlouseIds = A0Harness.BlouseIds;

        Dictionary<string, float> pose = new Dictionary<string, float>();
        StreamWriter log;
        Rect fullRegion, torsoRegion, faceRegion;
        Vector3 singleOffset;
        readonly Dictionary<string, int> masterOrder = new Dictionary<string, int>();
        int[] initialSingleOrder;
        readonly List<ProfilerRecorder> recorders = new List<ProfilerRecorder>();
        readonly List<string> recorderNames = new List<string>();
        int frame;
        CubismModel a0Body, a0Blouse;

        public bool Done { get; private set; }

        // ---------------------------------------------------------------- pose driving

        void Update()
        {
            frame++;
            Apply(Single);
            Apply(Body);
            if (Mirror != null && !Mirror.Mirror) Apply(Blouse);
            Apply(a0Body);
        }

        void Apply(CubismModel m)
        {
            if (m == null || !m.isActiveAndEnabled) return;
            foreach (var p in m.Parameters) p.Value = pose.TryGetValue(p.Id, out var v) ? v : p.DefaultValue;
        }

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
            log = new StreamWriter(Path.Combine(OutputDir, "a1_log.jsonl"), false, new UTF8Encoding(false));
            StartRecorders();
            yield return Frames(10);

            singleOffset = Single.transform.position - Body.transform.position;
            fullRegion = BoundsOf(Single, null, 0.02f, -singleOffset);
            torsoRegion = BoundsOf(Blouse, BlouseIds, 0.12f, Vector3.zero);
            faceRegion = BoundsOf(Body, new[] { "Head_Skin" }, 0.02f, Vector3.zero);

            var singleOrder = Single.AllDrawObjectsRenderOrder;
            initialSingleOrder = (int[])singleOrder.Clone();
            for (int i = 0; i < Single.Drawables.Length; i++) masterOrder[Single.Drawables[i].Id] = singleOrder[i];
            BodyMap.SetMaster(masterOrder);
            BlouseMap.SetMaster(masterOrder);
            LogSetup();

            yield return SortingVariations();
            SetSorting(CubismSortingMode.BackToFrontOrder, A1SortingMap.MapMode.OrderDelta);
            yield return Frames(3);

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
            var withFace = new HashSet<string> { "default", "angleXY_max", "eyesClosed_smile", "combo" };
            foreach (var (name, p) in poses)
            {
                pose = p;
                yield return Frames(SettleFrames);
                Capture("static_" + name, true, withFace.Contains(name));
            }

            var dynCaptures = new HashSet<int> { 30, 75, 150, 210 };
            for (int f = 0; f < 240; f++)
            {
                pose = Dynamic(f);
                yield return null;
                LogDiffs("dyn_mirror_frame", f);
                if (dynCaptures.Contains(f)) Capture("dyn_mirror_" + f.ToString("000"), true, false);
            }

            pose = Pose();
            yield return Frames(SettleFrames);
            yield return Independent(dynCaptures);
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

        void LogSetup()
        {
            var bodyRc = Body.GetComponent<CubismRenderController>();
            var blouseRc = Blouse.GetComponent<CubismRenderController>();
            var sb = new StringBuilder();
            sb.Append("\"drawables\":{\"single\":").Append(Single.Drawables.Length).Append(",\"body\":").Append(Body.Drawables.Length)
              .Append(",\"blouse\":").Append(Blouse.Drawables.Length).Append('}');
            sb.Append(",\"parameters\":{\"single\":").Append(Single.Parameters.Length).Append(",\"body\":").Append(Body.Parameters.Length)
              .Append(",\"blouse\":").Append(Blouse.Parameters.Length).Append('}');
            sb.Append(",\"parts\":{\"single\":").Append(Single.Parts.Length).Append(",\"body\":").Append(Body.Parts.Length)
              .Append(",\"blouse\":").Append(Blouse.Parts.Length).Append('}');
            sb.Append(",\"mirrorMatchedParameters\":").Append(Mirror.MatchedParameters).Append(",\"mirrorMatchedParts\":").Append(Mirror.MatchedParts);
            sb.Append(",\"mirrorUnmatchedParts\":").Append(Json(Mirror.UnmatchedParts));
            sb.Append(",\"unmappedBody\":").Append(BodyMap.Unmapped).Append(",\"unmappedBlouse\":").Append(BlouseMap.Unmapped);
            sb.Append(",\"bodyMasked\":").Append(CountMasked(Body)).Append(",\"blouseMasked\":").Append(CountMasked(Blouse));
            sb.Append(",\"sorting\":{\"body\":\"").Append(bodyRc.SortingMode).Append('/').Append(bodyRc.SortingOrder).Append('/').Append(bodyRc.GroupedSortingIndex)
              .Append("\",\"blouse\":\"").Append(blouseRc.SortingMode).Append('/').Append(blouseRc.SortingOrder).Append('/').Append(blouseRc.GroupedSortingIndex).Append("\"}");
            var orders = new StringBuilder("{");
            foreach (var m in new[] { Body, Blouse })
            {
                var own = m.AllDrawObjectsRenderOrder;
                for (int i = 0; i < m.Drawables.Length; i++)
                {
                    if (Array.IndexOf(BlouseIds, m.Drawables[i].Id) < 0 && m == Body && (i % 8) != 0) continue;
                    orders.Append(orders.Length > 1 ? "," : "").Append('"').Append(m == Body ? "body:" : "blouse:").Append(m.Drawables[i].Id)
                          .Append("\":[").Append(masterOrder[m.Drawables[i].Id]).Append(',').Append(own[i]).Append(']');
                }
            }
            sb.Append(",\"masterVsOwnOrderSample\":").Append(orders.Append('}'));
            sb.Append(",\"recorders\":").Append(RecorderValidity()).Append(",\"unity\":\"").Append(Application.unityVersion).Append('"');
            Log("setup", sb.ToString());
        }

        static int CountMasked(CubismModel m)
        {
            int n = 0;
            foreach (var d in m.Drawables) if (d.IsMasked) n++;
            return n;
        }

        void SetSorting(CubismSortingMode mode, A1SortingMap.MapMode map)
        {
            Body.GetComponent<CubismRenderController>().SortingMode = mode;
            Blouse.GetComponent<CubismRenderController>().SortingMode = mode;
            BodyMap.SetMode(map);
            BlouseMap.SetMode(map);
        }

        IEnumerator SortingVariations()
        {
            pose = Pose();
            yield return Frames(SettleFrames);
            var variants = new (string name, CubismSortingMode mode, A1SortingMap.MapMode map)[]
            {
                ("sort_noMap_Z", CubismSortingMode.BackToFrontZ, A1SortingMap.MapMode.None),
                ("sort_noMap_Order", CubismSortingMode.BackToFrontOrder, A1SortingMap.MapMode.None),
                ("sort_map_Z", CubismSortingMode.BackToFrontZ, A1SortingMap.MapMode.ZReference),
                ("sort_map_Order", CubismSortingMode.BackToFrontOrder, A1SortingMap.MapMode.OrderDelta),
            };
            foreach (var v in variants)
            {
                SetSorting(v.mode, v.map);
                yield return Frames(3);
                Capture(v.name, true, false);
            }
            var blouseRc = Blouse.GetComponent<CubismRenderController>();
            blouseRc.GroupedSortingIndex = 1;
            yield return Frames(3);
            Capture("sort_map_Order_blouseGroup1", true, false);
            blouseRc.GroupedSortingIndex = 0;
            yield return Frames(3);
        }

        IEnumerator Independent(HashSet<int> dynCaptures)
        {
            Mirror.SetMirror(false);
            yield return Frames(SettleFrames);
            LogDiffs("indep_settled", 0);
            Capture("indep_default", true, false);
            for (int f = 0; f < 240; f++)
            {
                pose = Dynamic(f);
                yield return null;
                LogDiffs("dyn_indep_frame", f);
                if (dynCaptures.Contains(f)) Capture("dyn_indep_" + f.ToString("000"), true, false);
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

        void Capture(string name, bool withTorso, bool withFace)
        {
            LogDiffs(name, 0);
            CaptureRegion(name + "_full", fullRegion, 768, Mathf.RoundToInt(768 * fullRegion.height / fullRegion.width));
            if (withTorso) CaptureRegion(name + "_torso", torsoRegion, 1024, 1024);
            if (withFace) CaptureRegion(name + "_face", faceRegion, 1024, 1024);
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

        /// <summary>Bounds in the frame of a model at the origin; <paramref name="shift"/> moves a model elsewhere back to it.</summary>
        static Rect BoundsOf(CubismModel m, string[] ids, float margin, Vector3 shift)
        {
            var set = ids == null ? null : new HashSet<string>(ids);
            bool any = false;
            var b = new Bounds();
            foreach (var d in m.Drawables)
            {
                if (set != null && !set.Contains(d.Id)) continue;
                var r = d.GetComponent<MeshRenderer>();
                if (r == null) continue;
                if (!any) { b = r.bounds; any = true; } else b.Encapsulate(r.bounds);
            }
            var c = b.center + shift;
            float half = Mathf.Max(b.extents.x, b.extents.y) * (1 + margin);
            float halfW = set == null ? b.extents.x * (1 + margin) : half;
            float halfH = set == null ? b.extents.y * (1 + margin) : half;
            return new Rect(c.x - halfW, c.y - halfH, halfW * 2, halfH * 2);
        }

        // ---------------------------------------------------------------- differences

        void LogDiffs(string tag, int f)
        {
            float pSingleBody = MaxParamDiff(Single, Body, out string pSB);
            float pBodyBlouse = MaxParamDiff(Body, Blouse, out string pBB);
            float vBody = MaxVertexDiff(Body, out string vBodyId);
            float vBlouse = MaxVertexDiff(Blouse, out string vBlouseId);
            int orderChange = 0;
            var now = Single.AllDrawObjectsRenderOrder;
            for (int i = 0; i < now.Length; i++) orderChange = Math.Max(orderChange, Math.Abs(now[i] - initialSingleOrder[i]));
            string probe = Probe == null ? "" :
                ",\"lateParamSingleVsBody\":" + F(Probe.SingleVsBody) + ",\"lateParamSingleVsBodyId\":\"" + Probe.SingleVsBodyId + "\"" +
                ",\"lateParamBodyVsBlouse\":" + F(Probe.BodyVsBlouse) + ",\"lateParamBodyVsBlouseId\":\"" + Probe.BodyVsBlouseId + "\"";
            Log(tag, "\"frame\":" + f + probe + ",\"paramSingleVsBody\":" + F(pSingleBody) + ",\"paramSingleVsBodyId\":\"" + pSB + "\"" +
                     ",\"paramBodyVsBlouse\":" + F(pBodyBlouse) + ",\"paramBodyVsBlouseId\":\"" + pBB + "\"" +
                     ",\"vertexBodyDrawables\":" + F(vBody) + ",\"vertexBodyId\":\"" + vBodyId + "\"" +
                     ",\"vertexBlouseDrawables\":" + F(vBlouse) + ",\"vertexBlouseId\":\"" + vBlouseId + "\"" +
                     ",\"singleRenderOrderMaxChange\":" + orderChange);
        }

        float MaxVertexDiff(CubismModel m, out string worst)
        {
            float max = 0;
            worst = "";
            var singleById = new Dictionary<string, CubismDrawable>();
            foreach (var d in Single.Drawables) singleById[d.Id] = d;
            foreach (var d in m.Drawables)
            {
                if (!singleById.TryGetValue(d.Id, out var s)) { worst = "missing:" + d.Id; return float.PositiveInfinity; }
                var a = s.VertexPositions;
                var b = d.VertexPositions;
                if (a.Length != b.Length) { worst = "count:" + d.Id; return float.PositiveInfinity; }
                for (int k = 0; k < a.Length; k++)
                {
                    float diff = (a[k] - b[k]).magnitude;
                    if (diff > max) { max = diff; worst = d.Id; }
                }
            }
            return max;
        }

        internal static float MaxParamDiff(CubismModel a, CubismModel b, out string id)
        {
            float max = 0;
            id = "";
            var byId = new Dictionary<string, CubismParameter>();
            foreach (var p in b.Parameters) byId[p.Id] = p;
            foreach (var p in a.Parameters)
            {
                if (!byId.TryGetValue(p.Id, out var q)) continue;
                float d = Mathf.Abs(p.Value - q.Value);
                if (d > max) { max = d; id = p.Id; }
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
            Add(ProfilerCategory.Scripts, "CubismModel");
        }

        string RecorderValidity()
        {
            var sb = new StringBuilder("{");
            for (int i = 0; i < recorders.Count; i++)
                sb.Append(i > 0 ? "," : "").Append('"').Append(recorderNames[i]).Append("\":").Append(B(recorders[i].Valid));
            return sb.Append('}').ToString();
        }

        void CreateA0Pair()
        {
            var body = Instantiate(SinglePrefab, Vector3.zero, Quaternion.identity);
            body.name = "A0_Body_runtime";
            var blouse = Instantiate(SinglePrefab, Vector3.zero, Quaternion.identity);
            blouse.name = "A0_Blouse_runtime";
            body.AddComponent<A0DrawableFilter>().Set(A0DrawableFilter.FilterMode.HideListed, BlouseIds);
            blouse.AddComponent<A0DrawableFilter>().Set(A0DrawableFilter.FilterMode.ShowOnlyListed, BlouseIds);
            var mirror = blouse.AddComponent<A0ParameterMirror>();
            mirror.Source = body.GetComponent<CubismModel>();
            a0Body = body.GetComponent<CubismModel>();
            a0Blouse = blouse.GetComponent<CubismModel>();
        }

        IEnumerator Performance()
        {
            CreateA0Pair();
            yield return Frames(10);
            var singlePos = Single.transform.position;
            var configs = new (string name, int which)[]
            {
                ("singleOnly", 0), ("a0Pair", 1), ("a1Pair", 2),
                ("singleOnly_again", 0), ("a0Pair_again", 1), ("a1Pair_again", 2),
            };
            foreach (var cfg in configs)
            {
                Single.transform.position = cfg.which == 0 ? Body.transform.position : singlePos;
                Single.gameObject.SetActive(cfg.which == 0);
                a0Body.gameObject.SetActive(cfg.which == 1);
                a0Blouse.gameObject.SetActive(cfg.which == 1);
                Body.gameObject.SetActive(cfg.which == 2);
                Blouse.gameObject.SetActive(cfg.which == 2);
                yield return Frames(60);
                var sums = new double[recorders.Count];
                int n = 300;
                for (int i = 0; i < n; i++)
                {
                    yield return null;
                    for (int r = 0; r < recorders.Count; r++) sums[r] += recorders[r].LastValue;
                }
                var models = cfg.which == 0 ? new[] { Single } : cfg.which == 1 ? new[] { a0Body, a0Blouse } : new[] { Body, Blouse };
                var sb = new StringBuilder("\"config\":\"" + cfg.name + "\",\"frames\":" + n);
                for (int r = 0; r < recorders.Count; r++)
                    sb.Append(",\"").Append(recorderNames[r]).Append("\":").Append(F(sums[r] / n));
                sb.Append(',').Append(Resources(models));
                Log("perf", sb.ToString());
            }
            Single.transform.position = singlePos;
            Single.gameObject.SetActive(true);
            Body.gameObject.SetActive(true);
            Blouse.gameObject.SetActive(true);
            Destroy(a0Body.gameObject);
            Destroy(a0Blouse.gameObject);
            a0Body = a0Blouse = null;
            yield return Frames(10);
        }

        /// <summary>Renderers, enabled renderers, vertices, unique meshes / textures / materials and their runtime sizes.</summary>
        static string Resources(CubismModel[] models)
        {
            int renderers = 0, enabled = 0, verts = 0, drawables = 0;
            var meshes = new HashSet<Mesh>();
            var textures = new HashSet<Texture>();
            var materials = new HashSet<Material>();
            foreach (var m in models)
            {
                drawables += m.Drawables.Length;
                foreach (var r in m.GetComponentsInChildren<CubismRenderer>(true))
                {
                    renderers++;
                    if (r.MeshRenderer != null && r.MeshRenderer.enabled) enabled++;
                    if (r.MainTexture != null) textures.Add(r.MainTexture);
                    if (r.MeshRenderer != null && r.MeshRenderer.sharedMaterial != null) materials.Add(r.MeshRenderer.sharedMaterial);
                }
                foreach (var mf in m.GetComponentsInChildren<MeshFilter>(true))
                {
                    if (mf.sharedMesh == null) continue;
                    meshes.Add(mf.sharedMesh);
                    verts += mf.sharedMesh.vertexCount;
                }
            }
            long meshBytes = 0, texBytes = 0;
            foreach (var m in meshes) meshBytes += UnityEngine.Profiling.Profiler.GetRuntimeMemorySizeLong(m);
            foreach (var t in textures) texBytes += UnityEngine.Profiling.Profiler.GetRuntimeMemorySizeLong(t);
            return "\"drawables\":" + drawables + ",\"renderers\":" + renderers + ",\"enabledRenderers\":" + enabled + ",\"meshVertices\":" + verts +
                   ",\"uniqueMeshes\":" + meshes.Count + ",\"meshBytes\":" + meshBytes + ",\"uniqueTextures\":" + textures.Count +
                   ",\"textureBytes\":" + texBytes + ",\"uniqueMaterials\":" + materials.Count;
        }

        IEnumerator Memory()
        {
            string Sample(string tag)
            {
                var sb = new StringBuilder("\"step\":\"" + tag + "\"");
                for (int r = 0; r < recorders.Count; r++)
                    if (recorderNames[r].Contains("Memory")) sb.Append(",\"").Append(recorderNames[r]).Append("\":").Append(recorders[r].LastValue);
                sb.Append(",\"totalAllocated\":").Append(UnityEngine.Profiling.Profiler.GetTotalAllocatedMemoryLong());
                return sb.ToString();
            }

            var cases = new (string name, GameObject[] prefabs)[]
            {
                ("extra_single", new[] { SinglePrefab }),
                ("extra_a0Pair", new[] { SinglePrefab, SinglePrefab }),
                ("extra_a1Pair", new[] { BodyPrefab, BlousePrefab }),
                ("extra_a1Blouse", new[] { BlousePrefab }),
            };
            foreach (var c in cases)
            {
                GC.Collect();
                yield return Frames(30);
                Log("memory", Sample("before_" + c.name));
                var made = new List<GameObject>();
                foreach (var p in c.prefabs) made.Add(Instantiate(p, new Vector3(6f, 0f, 0f), Quaternion.identity));
                yield return Frames(60);
                var ms = new List<CubismModel>();
                foreach (var g in made) ms.Add(g.GetComponent<CubismModel>());
                Log("memory", Sample("with_" + c.name) + "," + Resources(ms.ToArray()));
                foreach (var g in made) Destroy(g);
                yield return Frames(30);
            }
            GC.Collect();
            yield return Frames(30);
            Log("memory", Sample("after_all"));
        }

        // ---------------------------------------------------------------- log helpers

        void Log(string kind, string body)
        {
            log?.WriteLine("{\"kind\":\"" + kind + "\",\"t\":" + frame + (body.Length > 0 ? "," + body : "") + "}");
            log?.Flush();
        }

        static string Json(List<string> items)
        {
            var sb = new StringBuilder("[");
            for (int i = 0; i < items.Count; i++) sb.Append(i > 0 ? "," : "").Append('"').Append(items[i]).Append('"');
            return sb.Append(']').ToString();
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
