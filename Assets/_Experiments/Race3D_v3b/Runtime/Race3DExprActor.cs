using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using UnityEngine;

namespace MMG.Experiments.Race3DExpr
{
    /// <summary>
    /// Test only: one Race3D v3b character. Owns material instances (sparkle / proj / pull / flow) so N actors never share
    /// mutable shader values. Brow pull comes from HairBrowPullTable by hairItemId (not a hard-coded global). Tear stream
    /// keeps UV v = path progress for a later cheek-curve mesh without changing _Flow.
    /// </summary>
    public sealed class Race3DExprActor : MonoBehaviour
    {
        [Serializable]
        public class Proj { public string side; public float su, tu, sv, tv, uc, vc; }

        public struct State
        {
            public float happy, angry, angry2, sad, cry, surprise, blink, gaze, eyesmile, smile, flow;
            public bool noview;
            public static State Neutral => new State { flow = -1 };
            public State Lerp(State b, float t)
            {
                float L(float x, float y) => x + (y - x) * t;
                return new State
                {
                    happy = L(happy, b.happy), angry = L(angry, b.angry), angry2 = L(angry2, b.angry2), sad = L(sad, b.sad),
                    cry = L(cry, b.cry), surprise = L(surprise, b.surprise), blink = L(blink, b.blink), gaze = L(gaze, b.gaze),
                    eyesmile = L(eyesmile, b.eyesmile), smile = L(smile, b.smile), flow = -1
                };
            }
        }

        public GameObject modelPrefab;
        public GameObject formalPrefab;
        public Shader eyeSparkleShader, hairStencilShader, browCardShader, tearStreamShader, unlitShader;
        public Texture2D sparkleL, sparkleR;
        public Proj[] projData;
        public HairBrowPullTable browPullTable;
        [Tooltip("worn hair itemId for pull lookup; empty = table default")]
        public string hairItemId = "hair_bob_01_01";
        [Tooltip(">=0 overrides the table for this actor only")]
        public float browPullOverride = -1f;
        public Vector3 lightAtFront = new Vector3(0.296f, 0.5f, 0.814f);
        public Camera viewCamera;
        public bool viewCorrection = true, hair = true, browCards = true;
        public State state = State.Neutral;

        public float ViewYaw { get; private set; }
        public float LastCostMicroseconds { get; private set; }
        public float BrowPullMeters { get; private set; }
        public Transform EyeL { get; private set; }
        public Transform EyeR { get; private set; }
        public Vector3 FaceForwardLocal => fwdLocal;
        public Vector3 CharacterLeftLocal => leftLocal;
        public GameObject Instance => inst;
        public IReadOnlyList<Material> OwnedMaterials => allMats;
        public float Sparkle => sparkle;
        public float IrisScale => irisScale;
        public float Flow => flowV;
        public float CardReveal => browAlpha;

        const int GEye = 0, GLine = 1, GOldSmile = 2, GExSmile = 3, GExO = 4, GTear = 5, GFace = 6;
        GameObject inst;
        Vector3 fwdLocal, leftLocal;
        readonly List<(SkinnedMeshRenderer r, string[] names, int group)> skins = new List<(SkinnedMeshRenderer, string[], int)>();
        readonly List<Renderer> lineR = new List<Renderer>(), exSmileR = new List<Renderer>(), exOR = new List<Renderer>(),
            tearR = new List<Renderer>(), streamR = new List<Renderer>(), cardR = new List<Renderer>(), hairR = new List<Renderer>();
        readonly Dictionary<string, Material> eyeMat = new Dictionary<string, Material>();
        readonly List<Material> streamMats = new List<Material>(), cardMats = new List<Material>(), allMats = new List<Material>();
        readonly Dictionary<string, Proj> proj = new Dictionary<string, Proj>();
        readonly Dictionary<string, float> eye = new Dictionary<string, float>(), face = new Dictionary<string, float>(),
            line = new Dictionary<string, float>(), tear = new Dictionary<string, float>(), empty = new Dictionary<string, float>();
        readonly Stopwatch watch = new Stopwatch();
        float mouthOpen, oVal, flowV, sparkle, irisScale, pitch, browAlpha;
        bool showLine, showO, showTear, showFlow, built;

        public static State St(float happy = 0, float angry = 0, float angry2 = 0, float sad = 0, float cry = 0, float surprise = 0,
                               float blink = 0, float gaze = 0, float flow = -1)
            => new State { happy = happy, angry = angry, angry2 = angry2, sad = sad, cry = cry, surprise = surprise, blink = blink, gaze = gaze, flow = flow };

        static float Sm(float t) { t = Mathf.Clamp01(t); return t * t * (3 - 2 * t); }

        static void HappyStages(float h, out float a, out float c, out float b)
        {
            if (h <= 0.6f) { a = h / 0.6f; c = 0; b = 0; return; }
            if (h <= 0.85f) { float t = (h - 0.6f) / 0.25f; a = 1 - t; c = t; b = 0; return; }
            float u = (h - 0.85f) / 0.15f; a = 0; c = 1 - u; b = u;
        }

        void ViewKeys(float yaw, float gz, float b, float es, Dictionary<string, float> d)
        {
            float w = Sm((Mathf.Abs(yaw) - 20f) / 20f);
            float side = Sm((Mathf.Abs(yaw) - 50f) / 15f) * 0.8f;
            foreach (var (s, sg) in new[] { ("L", 1f), ("R", -1f) })
            {
                float wf = s == "R" ? (yaw > 0 ? w : 0) : (yaw < 0 ? w : 0);
                float sd = wf > 0 ? side : 0f;
                float k = (1 - b) * (1 - es);
                float ws = wf * k * (1 - sd);
                float gOut = sg * gz;
                float to = Mathf.Clamp01(gOut / 0.25f), ti = Mathf.Clamp01(-gOut / 0.12f);
                d["ViewFar" + s] = ws * (1 - to - ti);
                d["ViewFar" + s + "_GO"] = ws * to;
                d["ViewFar" + s + "_GI"] = ws * ti;
                d["ViewSide" + s] = sd * k;
            }
        }

        public float ResolveBrowPull()
        {
            if (browPullOverride >= 0f) return browPullOverride;
            return browPullTable != null ? browPullTable.Resolve(hairItemId) : 0.03f;
        }

        public void Build()
        {
            if (built) return;
            foreach (var p in projData) proj[p.side] = p;
            BrowPullMeters = ResolveBrowPull();
            inst = Instantiate(modelPrefab, transform);
            inst.name = "Race3D_v3b";
            var formal = formalPrefab.GetComponentsInChildren<Renderer>(true).GroupBy(r => r.name)
                .ToDictionary(x => x.Key, x => x.First().sharedMaterials);
            var copies = new Dictionary<Material, Material>();
            Material Cached(Material src)
            {
                if (src == null) return null;
                if (!copies.TryGetValue(src, out var m))
                    copies[src] = m = src.shader != null && src.shader.name == "MMG/Character/ToonHair" ? Copy(src, hairStencilShader) : Copy(src);
                if (m.shader == hairStencilShader) m.renderQueue = 2010;
                return m;
            }
            var exMats = new Dictionary<string, Material>
            {
                ["M_Ex_MouthInside"] = Unlit(new Color32(150, 60, 60, 255), 1, 3000),
                ["M_Ex_Tongue"] = Unlit(new Color32(230, 120, 120, 255), 1, 3001),
                ["M_Ex_Teeth"] = Unlit(new Color32(250, 248, 248, 255), 1, 3001),
                ["M_Ex_MouthRim"] = Unlit(new Color32(150, 70, 62, 255), 1, 3002),
                ["M_Tear"] = Unlit(new Color32(190, 224, 255, 255), 0.6f, 3006),
                ["M_TearHighlight"] = Unlit(new Color32(255, 255, 255, 255), 0.9f, 3007),
            };
            var rends = inst.GetComponentsInChildren<Renderer>(true);
            foreach (var r in rends)
            {
                string n = r.name;
                var src = r.sharedMaterials;
                var dst = new Material[src.Length];
                for (int i = 0; i < src.Length; i++)
                {
                    string mn = src[i] != null ? src[i].name.Replace(" (Instance)", "") : "";
                    if (n.StartsWith("Eye_Ball."))
                    {
                        string s = n.Substring(9, 1);
                        var m = Copy(formal[n][i], eyeSparkleShader);
                        m.SetTexture("_SparkleTex", s == "L" ? sparkleL : sparkleR);
                        eyeMat[s] = m;
                        dst[i] = m;
                    }
                    else if (n.StartsWith("Face_BrowCard."))
                    {
                        var m = new Material(browCardShader);
                        m.SetColor("_BaseColor", new Color(78 / 255f, 38 / 255f, 34 / 255f, 1));
                        allMats.Add(m); cardMats.Add(m);
                        dst[i] = m;
                    }
                    else if (n.StartsWith("Face_TearStream."))
                    {
                        var m = new Material(tearStreamShader);
                        allMats.Add(m); streamMats.Add(m);
                        dst[i] = m;
                    }
                    else if (exMats.TryGetValue(mn, out var em)) dst[i] = em;
                    else if (formal.TryGetValue(n, out var fm) && i < fm.Length) dst[i] = Cached(fm[i]);
                    else dst[i] = src[i];
                }
                r.sharedMaterials = dst;
                if (n == "TT_Mouth_Closed") lineR.Add(r);
                else if (n == "Face_Mouth_ExSmile") exSmileR.Add(r);
                else if (n == "Face_Mouth_ExO") exOR.Add(r);
                else if (n.StartsWith("Face_TearStream.")) streamR.Add(r);
                else if (n.StartsWith("Face_Tear.")) tearR.Add(r);
                else if (n.StartsWith("Face_BrowCard.")) cardR.Add(r);
                else if (n.StartsWith("hair_bob_01") || n.StartsWith("acc_head_hairclip")) hairR.Add(r);
                if (n.StartsWith("Face_Mouth_Smile_")) r.enabled = false;
                if (r is SkinnedMeshRenderer smr && smr.sharedMesh != null && smr.sharedMesh.blendShapeCount > 0)
                {
                    var mesh = smr.sharedMesh;
                    var names = Enumerable.Range(0, mesh.blendShapeCount).Select(mesh.GetBlendShapeName).ToArray();
                    int grp = n.StartsWith("Eye_Lids") || n.StartsWith("Eye_Lash") ? GEye
                        : n == "TT_Mouth_Closed" ? GLine : n.StartsWith("Face_Mouth_Smile_") ? GOldSmile
                        : n == "Face_Mouth_ExSmile" ? GExSmile : n == "Face_Mouth_ExO" ? GExO
                        : n.StartsWith("Face_Tear") ? GTear : GFace;
                    skins.Add((smr, names, grp));
                }
            }
            Renderer R(string n) => rends.First(r => r.name == n);
            var head = R("Blockout_Head").bounds;
            EyeL = R("Eye_Ball.L").transform;
            EyeR = R("Eye_Ball.R").transform;
            float sx = Mathf.Sign(EyeL.position.x - inst.transform.position.x);
            float front = Mathf.Sign(R("TT_Mouth_Closed").bounds.center.z - head.center.z);
            fwdLocal = new Vector3(0, 0, front);
            leftLocal = new Vector3(sx, 0, 0);
            built = true;
        }

        Material Copy(Material src, Shader shader = null)
        {
            var m = new Material(src);
            if (shader != null) { int q = src.renderQueue; m.shader = shader; m.CopyPropertiesFromMaterial(src); m.renderQueue = q; }
            allMats.Add(m);
            return m;
        }

        Material Unlit(Color32 c, float alpha, int queue)
        {
            var m = new Material(unlitShader);
            m.SetColor("_BaseColor", new Color(c.r / 255f, c.g / 255f, c.b / 255f, alpha));
            m.renderQueue = queue;
            allMats.Add(m);
            return m;
        }

        float CameraYaw()
        {
            if (viewCamera == null || inst == null) return 0f;
            Vector3 dir = viewCamera.orthographic ? -viewCamera.transform.forward
                : (viewCamera.transform.position - inst.transform.position).normalized;
            Vector3 d = inst.transform.InverseTransformDirection(dir);
            return Mathf.Atan2(Vector3.Dot(d, leftLocal), Vector3.Dot(d, fwdLocal)) * Mathf.Rad2Deg;
        }

        public void Compose()
        {
            if (!built) return;
            watch.Restart();
            BrowPullMeters = ResolveBrowPull();
            var g = state;
            float h = g.happy, b = g.blink;
            HappyStages(h, out float hA, out float hC, out float hB);
            eye.Clear();
            eye["ExHappyA"] = hA * (1 - b); eye["ExHappyC"] = hC * (1 - b); eye["ExHappyB"] = hB * (1 - b);
            eye["ExAngry"] = g.angry * (1 - b); eye["ExAngry2"] = g.angry2 * (1 - b); eye["ExSad"] = g.sad * (1 - b);
            eye["ExCry"] = g.cry * (1 - b); eye["ExSurprise"] = g.surprise * (1 - b);
            eye["Blink"] = b; eye["EyeSmile"] = g.eyesmile; eye["Smile"] = g.smile;
            ViewYaw = CameraYaw();
            if (viewCorrection && !g.noview) ViewKeys(ViewYaw, g.gaze, b, 1 - (1 - g.eyesmile) * (1 - h), eye);
            face.Clear();
            face["ExHappy"] = h; face["ExAngry"] = g.angry; face["ExAngry2"] = g.angry2; face["ExSad"] = g.sad * (1 - g.cry);
            face["ExCry"] = g.cry; face["ExSurprise"] = g.surprise; face["Blink"] = b; face["EyeSmile"] = g.eyesmile; face["Smile"] = g.smile;
            mouthOpen = Sm((h - 0.35f) / 0.55f);
            line.Clear();
            line["ExHappy"] = Mathf.Min(1, h / 0.35f); line["ExAngry"] = g.angry + g.angry2; line["ExSad"] = g.sad * (1 - g.cry);
            line["ExCry"] = g.cry; line["ExSurprise"] = Mathf.Min(1, g.surprise * 2.5f); line["Smile"] = g.smile;
            tear.Clear();
            tear["ExSad"] = g.sad * (1 - b); tear["ExCry"] = g.cry * (1 - b);
            oVal = g.surprise;
            flowV = g.flow >= 0 ? g.flow : 0.5f * g.cry;
            browAlpha = 0.8f * Mathf.Min(1, Mathf.Max(Mathf.Max(g.angry, g.angry2), Mathf.Max(Mathf.Max(g.sad, g.cry), Mathf.Max(g.surprise, 0.5f * h))));
            showLine = mouthOpen < 0.25f && g.surprise < 0.4f;
            showO = g.surprise > 0.02f;
            showTear = Mathf.Max(g.sad, g.cry) * (1 - b) > 0.05f;
            showFlow = flowV * (1 - b) > 0.02f && g.cry > 0.05f;
            sparkle = g.surprise * (1 - b);
            irisScale = 1 - 0.08f * g.surprise;
            pitch = 0.0008f * g.angry + 0.0010f * g.angry2;

            foreach (var (r, names, grp) in skins)
            {
                var d = grp == GEye ? eye : grp == GLine ? line : grp == GTear ? tear : grp == GFace ? face : empty;
                for (int i = 0; i < names.Length; i++)
                {
                    float v = grp == GExSmile ? (names[i] == "ExHappy" ? mouthOpen : 0)
                        : grp == GExO ? (names[i] == "ExSurprise" ? oVal : 0)
                        : (d.TryGetValue(names[i], out var x) ? x : 0);
                    r.SetBlendShapeWeight(i, v * 100f);
                }
            }
            foreach (var r in exSmileR) r.enabled = mouthOpen > 0.02f;
            foreach (var r in lineR) r.enabled = showLine;
            foreach (var r in exOR) r.enabled = showO;
            foreach (var r in tearR) r.enabled = showTear;
            foreach (var r in streamR) r.enabled = showFlow;
            foreach (var r in hairR) r.enabled = hair;
            foreach (var r in cardR) r.enabled = hair && browCards && browAlpha > 0.01f;
            foreach (var m in streamMats) m.SetFloat("_Flow", flowV);
            foreach (var m in cardMats) { m.SetFloat("_Reveal", browAlpha); m.SetFloat("_Pull", BrowPullMeters); }
            foreach (var kv in eyeMat)
            {
                var p = proj[kv.Key];
                kv.Value.SetFloat("_GazeYaw", g.gaze);
                kv.Value.SetFloat("_Sparkle", sparkle);
                kv.Value.SetVector("_Proj", new Vector4(p.su / irisScale, (p.tu - p.uc) / irisScale + p.uc,
                                                        p.sv / irisScale, (p.tv - p.vc) / irisScale + p.vc - pitch * p.sv / irisScale));
            }
            Vector3 lw = Quaternion.AngleAxis(-ViewYaw, Vector3.up) * lightAtFront;
            foreach (var m in allMats) if (m.HasProperty("_LightDir")) m.SetVector("_LightDir", lw);
            watch.Stop();
            LastCostMicroseconds = (float)(watch.Elapsed.TotalMilliseconds * 1000.0);
        }

        void LateUpdate() => Compose();

        void OnDestroy()
        {
            foreach (var m in allMats) if (m != null) Destroy(m);
            allMats.Clear();
        }
    }
}
