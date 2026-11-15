using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using UnityEngine;

namespace MMG.Characters.Avatar3D
{
    /// <summary>
    /// Race3D formal expression driver (v3b baseline). Owns Ex* BlendShapes, mouth/tear/brow visibility, and
    /// per-actor material instances (_Sparkle, _Proj, _Pull, _Flow). When an <see cref="EyeViewController"/> is linked,
    /// that controller alone writes Blink / EyeSmile / Smile / Surprise / View* on the eye meshes; this component only
    /// feeds its input fields and <c>viewSuppress = Happy</c>.
    /// Mix: Angry2 dominates Angry (weak = angry×(1−angry2)); Cry replaces Sad on the face; Happy stages A→C→B.
    /// </summary>
    [DefaultExecutionOrder(31000)]
    public sealed class ExpressionController : MonoBehaviour
    {
        [Serializable]
        public class Proj { public string side; public float su, tu, sv, tv, uc, vc; }

        public struct State
        {
            public float happy, angry, angry2, sad, cry, surprise, blink, gaze, eyesmile, smile, flow;
            public bool noview;
            public static State Neutral => new State { flow = -1 };
        }

        public EyeViewController eyeView;
        public Shader eyeSparkleShader, hairStencilShader, browCardShader, tearStreamShader, unlitShader;
        public Texture2D sparkleL, sparkleR;
        public Proj[] projData;
        public HairBrowPullTable browPullTable;
        [Tooltip("worn hair itemId for pull lookup; empty = table default")]
        public string hairItemId = "hair_bob_01_01";
        [Tooltip(">=0 overrides the table for this actor only")]
        public float browPullOverride = -1f;
        public Vector3 lightAtFront = new Vector3(0.296f, 0.5f, 0.814f);
        public bool hair = true, browCards = true;
        public State state = State.Neutral;

        public float BrowPullMeters { get; private set; }
        public float LastCostMicroseconds { get; private set; }
        public float Sparkle => sparkle;
        public float IrisScale => irisScale;
        public float Flow => flowV;
        public IReadOnlyList<Material> OwnedMaterials => allMats;

        const int GEye = 0, GLine = 1, GOldSmile = 2, GExSmile = 3, GExO = 4, GTear = 5, GFace = 6;
        static readonly HashSet<string> EyeViewOwned = new HashSet<string>
        {
            "Blink", "EyeSmile", "Smile", "Surprise",
            "ViewFarL", "ViewFarL_GO", "ViewFarL_GI", "ViewSideL",
            "ViewFarR", "ViewFarR_GO", "ViewFarR_GI", "ViewSideR"
        };

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

        public static State St(float happy = 0, float angry = 0, float angry2 = 0, float sad = 0, float cry = 0,
            float surprise = 0, float blink = 0, float gaze = 0, float flow = -1)
            => new State
            {
                happy = happy, angry = angry, angry2 = angry2, sad = sad, cry = cry, surprise = surprise,
                blink = blink, gaze = gaze, flow = flow
            };

        /// <summary>Angry2 dominates Angry so both keys never stack full deltas on the same mesh.</summary>
        public static void ResolveConflict(State g, out float angryWeak, out float angryStrong)
        {
            angryStrong = Mathf.Clamp01(g.angry2);
            angryWeak = Mathf.Clamp01(g.angry) * (1f - angryStrong);
        }

        static float Sm(float t) { t = Mathf.Clamp01(t); return t * t * (3f - 2f * t); }

        static void HappyStages(float h, out float a, out float c, out float b)
        {
            if (h <= 0.6f) { a = h / 0.6f; c = 0; b = 0; return; }
            if (h <= 0.85f) { float t = (h - 0.6f) / 0.25f; a = 1 - t; c = t; b = 0; return; }
            float u = (h - 0.85f) / 0.15f; a = 0; c = 1 - u; b = u;
        }

        public float ResolveBrowPull()
        {
            if (browPullOverride >= 0f) return browPullOverride;
            return browPullTable != null ? browPullTable.Resolve(hairItemId) : 0.03f;
        }

        public void Build()
        {
            if (built) return;
            if (projData != null) foreach (var p in projData) proj[p.side] = p;
            BrowPullMeters = ResolveBrowPull();
            var copies = new Dictionary<Material, Material>();
            Material Cached(Material src)
            {
                if (src == null) return null;
                if (!copies.TryGetValue(src, out var m))
                {
                    bool hairMat = src.shader != null && (src.shader.name == "MMG/Character/ToonHair"
                                                         || src.shader.name == "MMG/Character/ToonHairStencil"
                                                         || src.shader.name == "MMG/Experiments/ToonHairStencil");
                    m = hairMat && hairStencilShader != null ? Copy(src, hairStencilShader) : Copy(src);
                    copies[src] = m;
                }
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
            var rends = GetComponentsInChildren<Renderer>(true);
            foreach (var r in rends)
            {
                string n = r.name;
                var src = r.sharedMaterials;
                var dst = new Material[src.Length];
                for (int i = 0; i < src.Length; i++)
                {
                    string mn = src[i] != null ? src[i].name.Replace(" (Instance)", "") : "";
                    if (n.StartsWith("Eye_Ball.") && eyeSparkleShader != null)
                    {
                        string s = n.Length > 9 ? n.Substring(9, 1) : "L";
                        var m = Copy(src[i], eyeSparkleShader);
                        if (sparkleL && sparkleR) m.SetTexture("_SparkleTex", s == "L" ? sparkleL : sparkleR);
                        eyeMat[s] = m;
                        dst[i] = m;
                    }
                    else if (n.StartsWith("Face_BrowCard.") && browCardShader != null)
                    {
                        var m = new Material(browCardShader);
                        m.SetColor("_BaseColor", new Color(78 / 255f, 38 / 255f, 34 / 255f, 1));
                        allMats.Add(m); cardMats.Add(m);
                        dst[i] = m;
                    }
                    else if (n.StartsWith("Face_TearStream.") && tearStreamShader != null)
                    {
                        var m = new Material(tearStreamShader);
                        allMats.Add(m); streamMats.Add(m);
                        dst[i] = m;
                    }
                    else if (exMats.TryGetValue(mn, out var em)) dst[i] = em;
                    else dst[i] = Cached(src[i]);
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
            if (eyeView == null) eyeView = GetComponent<EyeViewController>();
            if (eyeView != null && eyeMat.Count > 0)
            {
                eyeView.eyeMaterials = eyeMat.Values.ToList();
            }
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
            var m = new Material(unlitShader != null ? unlitShader : Shader.Find("MMG/Character/Unlit"));
            m.SetColor("_BaseColor", new Color(c.r / 255f, c.g / 255f, c.b / 255f, alpha));
            m.renderQueue = queue;
            allMats.Add(m);
            return m;
        }

        public void Compose()
        {
            if (!built) Build();
            if (!built) return;
            watch.Restart();
            BrowPullMeters = ResolveBrowPull();
            var g = state;
            ResolveConflict(g, out float angryWeak, out float angryStrong);
            float h = Mathf.Clamp01(g.happy), b = Mathf.Clamp01(g.blink);
            HappyStages(h, out float hA, out float hC, out float hB);

            if (eyeView != null)
            {
                eyeView.blink = b;
                eyeView.eyeSmile = Mathf.Clamp01(g.eyesmile);
                eyeView.smile = Mathf.Clamp01(g.smile);
                eyeView.surprise = Mathf.Clamp01(g.surprise); // legacy Surprise key; ExSurprise is written below
                eyeView.gaze = Mathf.Clamp(g.gaze, -0.25f, 0.25f);
                eyeView.viewSuppress = g.noview ? 1f : h;
                if (!eyeView.viewCorrection) eyeView.viewCorrection = true;
            }

            eye.Clear();
            eye["ExHappyA"] = hA * (1 - b); eye["ExHappyC"] = hC * (1 - b); eye["ExHappyB"] = hB * (1 - b);
            eye["ExAngry"] = angryWeak * (1 - b); eye["ExAngry2"] = angryStrong * (1 - b);
            eye["ExSad"] = g.sad * (1 - b); eye["ExCry"] = g.cry * (1 - b); eye["ExSurprise"] = g.surprise * (1 - b);
            // when EyeView is absent, also drive the base + view keys (standalone / tests)
            if (eyeView == null)
            {
                eye["Blink"] = b; eye["EyeSmile"] = g.eyesmile; eye["Smile"] = g.smile; eye["Surprise"] = g.surprise;
            }

            face.Clear();
            face["ExHappy"] = h; face["ExAngry"] = angryWeak; face["ExAngry2"] = angryStrong;
            face["ExSad"] = g.sad * (1 - g.cry); face["ExCry"] = g.cry; face["ExSurprise"] = g.surprise;
            face["Blink"] = b; face["EyeSmile"] = g.eyesmile; face["Smile"] = g.smile;
            mouthOpen = Sm((h - 0.35f) / 0.55f);
            line.Clear();
            line["ExHappy"] = Mathf.Min(1, h / 0.35f);
            line["ExAngry"] = Mathf.Max(angryWeak, angryStrong); // single mouth-line channel; no stack past 1
            line["ExSad"] = g.sad * (1 - g.cry);
            line["ExCry"] = g.cry; line["ExSurprise"] = Mathf.Min(1, g.surprise * 2.5f); line["Smile"] = g.smile;
            tear.Clear();
            tear["ExSad"] = g.sad * (1 - b); tear["ExCry"] = g.cry * (1 - b);
            oVal = g.surprise;
            flowV = g.flow >= 0 ? g.flow : 0.5f * g.cry;
            browAlpha = 0.8f * Mathf.Min(1, Mathf.Max(Mathf.Max(angryWeak, angryStrong),
                Mathf.Max(Mathf.Max(g.sad, g.cry), Mathf.Max(g.surprise, 0.5f * h))));
            showLine = mouthOpen < 0.25f && g.surprise < 0.4f;
            showO = g.surprise > 0.02f;
            showTear = Mathf.Max(g.sad, g.cry) * (1 - b) > 0.05f;
            showFlow = flowV * (1 - b) > 0.02f && g.cry > 0.05f;
            sparkle = g.surprise * (1 - b);
            irisScale = 1 - 0.08f * g.surprise;
            pitch = 0.0008f * angryWeak + 0.0010f * angryStrong;

            bool deferEyeBase = eyeView != null;
            foreach (var (r, names, grp) in skins)
            {
                var d = grp == GEye ? eye : grp == GLine ? line : grp == GTear ? tear : grp == GFace ? face : empty;
                for (int i = 0; i < names.Length; i++)
                {
                    if (deferEyeBase && grp == GEye && EyeViewOwned.Contains(names[i])) continue;
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
                if (!proj.TryGetValue(kv.Key, out var p)) continue;
                kv.Value.SetFloat("_GazeYaw", g.gaze);
                kv.Value.SetFloat("_Sparkle", sparkle);
                kv.Value.SetVector("_Proj", new Vector4(p.su / irisScale, (p.tu - p.uc) / irisScale + p.uc,
                    p.sv / irisScale, (p.tv - p.vc) / irisScale + p.vc - pitch * p.sv / irisScale));
            }
            watch.Stop();
            LastCostMicroseconds = (float)(watch.Elapsed.TotalMilliseconds * 1000.0);
        }

        void Awake() => Build();
        void LateUpdate() => Compose();

        void OnDestroy()
        {
            foreach (var m in allMats) if (m != null) Destroy(m);
        }
    }
}
