using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using UnityEngine;

namespace MMG.Experiments.Race3DExpr
{
    /// <summary>
    /// Test only (Race3D v3b expressions, not for the game): plays the v3b expression FBX in play mode with the mixing rules
    /// of expr_mix_v3b.py and the v6j view keys (eye_v6_common.view_key_values; the formal EyeViewController has no Happy
    /// input yet, so this driver writes every key itself). Materials are run-time copies of the formal prefab materials
    /// (assets untouched) plus the experiment shaders: eyeball sparkle / iris scale / pitch, hair stencil + brow card,
    /// tear stream flow. Shots use the Blender render framing (orthographic, Blender (x, y, z) = Unity (-x, z, -y)) and
    /// the Blender file names, so the two can be paired. A real-time sweep (emotions, Blink, gaze, camera yaw up to +-60)
    /// checks the per-frame weights. Results: outDir/{shots}, outDir/sweep, outDir/weights.jsonl, outDir/log.txt.
    /// </summary>
    public sealed class Race3DExprCheck : MonoBehaviour
    {
        [Serializable] public class Shot { public string name; public float yaw, w, h, ortho; public float[] loc; }
        [Serializable] public class Proj { public string side; public float su, tu, sv, tv, uc, vc; }
        [Serializable] public class Spec { public Shot[] shots; public Proj[] proj; public float[] eyeBallL; }

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
            public override string ToString() => string.Format(CultureInfo.InvariantCulture,
                "{{\"happy\":{0},\"angry\":{1},\"angry2\":{2},\"sad\":{3},\"cry\":{4},\"surprise\":{5},\"blink\":{6},\"gaze\":{7},\"flow\":{8},\"noview\":{9}}}",
                happy, angry, angry2, sad, cry, surprise, blink, gaze, flow, noview ? "true" : "false");
        }

        public GameObject model;
        public GameObject formalPrefab;
        public Shader eyeSparkleShader, hairStencilShader, browCardShader, tearStreamShader, unlitShader;
        public Texture2D sparkleL, sparkleR;
        public TextAsset specJson;
        public string outDir;
        public float browPull = 0.03f;
        public Vector3 lightAtFront = new Vector3(0.296f, 0.5f, 0.814f);
        public bool runShots = true, runSweep = true;
        public float sweepSeconds = 16f;

        public State state = State.Neutral;
        public bool viewCorrection = true, hair = true, browCards = true;
        public float ViewYaw { get; private set; }

        const int GEye = 0, GLine = 1, GOldSmile = 2, GExSmile = 3, GExO = 4, GTear = 5, GFace = 6;
        Spec spec;
        Camera cam;
        GameObject inst;
        Vector3 fwdLocal, leftLocal, offset;
        readonly List<(SkinnedMeshRenderer r, string[] names, int group)> skins = new List<(SkinnedMeshRenderer, string[], int)>();
        readonly List<Renderer> lineR = new List<Renderer>(), exSmileR = new List<Renderer>(), exOR = new List<Renderer>(),
            tearR = new List<Renderer>(), streamR = new List<Renderer>(), cardR = new List<Renderer>(), hairR = new List<Renderer>();
        readonly Dictionary<string, Material> eyeMat = new Dictionary<string, Material>();
        readonly List<Material> streamMats = new List<Material>(), cardMats = new List<Material>(), allMats = new List<Material>();
        readonly Dictionary<string, Proj> proj = new Dictionary<string, Proj>();
        readonly Dictionary<string, float> eye = new Dictionary<string, float>(), face = new Dictionary<string, float>(),
            line = new Dictionary<string, float>(), tear = new Dictionary<string, float>(), empty = new Dictionary<string, float>();
        float mouthOpen, oVal, flowV, sparkle, irisScale, pitch, browAlpha;
        bool showLine, showO, showTear, showFlow;
        readonly List<string> log = new List<string>();
        StreamWriter weights;

        void Log(string s)
        {
            Debug.Log("[Race3DExprCheck] " + s);
            log.Add(s);
            File.WriteAllLines(Path.Combine(outDir, "log.txt"), log);
        }

        static float Sm(float t)
        {
            t = Mathf.Clamp01(t);
            return t * t * (3 - 2 * t);
        }

        static void HappyStages(float h, out float a, out float c, out float b)
        {
            if (h <= 0.6f) { a = h / 0.6f; c = 0; b = 0; return; }
            if (h <= 0.85f) { float t = (h - 0.6f) / 0.25f; a = 1 - t; c = t; b = 0; return; }
            float u = (h - 0.85f) / 0.15f;
            a = 0; c = 1 - u; b = u;
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

        float CameraYaw()
        {
            Vector3 dir = cam.orthographic ? -cam.transform.forward : (cam.transform.position - inst.transform.position).normalized;
            Vector3 d = inst.transform.InverseTransformDirection(dir);
            return Mathf.Atan2(Vector3.Dot(d, leftLocal), Vector3.Dot(d, fwdLocal)) * Mathf.Rad2Deg;
        }

        /// <summary>expr_mix_v3b.compose + render apply(): every weight, renderer switch and material value</summary>
        public void Compose()
        {
            if (inst == null) return;
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
                    float v;
                    if (grp == GExSmile) v = names[i] == "ExHappy" ? mouthOpen : 0;
                    else if (grp == GExO) v = names[i] == "ExSurprise" ? oVal : 0;
                    else v = d.TryGetValue(names[i], out var x) ? x : 0;
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
            foreach (var m in cardMats) { m.SetFloat("_Reveal", browAlpha); m.SetFloat("_Pull", browPull); }
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
        }

        void LateUpdate() => Compose();

        void OnDestroy()
        {
            weights?.Dispose();
            foreach (var m in allMats) if (m != null) Destroy(m);
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

        void Build()
        {
            inst = Instantiate(model);
            inst.name = "Race3D_v3b_Expressions (test)";
            var formal = formalPrefab.GetComponentsInChildren<Renderer>(true).GroupBy(r => r.name).ToDictionary(x => x.Key, x => x.First().sharedMaterials);
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
                ["M_Ex_MouthInside"] = Unlit(new Color32(150, 60, 60, 255), 1, 3000), ["M_Ex_Tongue"] = Unlit(new Color32(230, 120, 120, 255), 1, 3001),
                ["M_Ex_Teeth"] = Unlit(new Color32(250, 248, 248, 255), 1, 3001), ["M_Ex_MouthRim"] = Unlit(new Color32(150, 70, 62, 255), 1, 3002),
                ["M_Tear"] = Unlit(new Color32(190, 224, 255, 255), 0.6f, 3006), ["M_TearHighlight"] = Unlit(new Color32(255, 255, 255, 255), 0.9f, 3007),
            };
            var unmapped = new List<string>();
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
                    else { dst[i] = src[i]; unmapped.Add($"{n}:{mn}"); }
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
            var eyeL = R("Eye_Ball.L");
            float sx = Mathf.Sign(eyeL.bounds.center.x - inst.transform.position.x);
            float front = Mathf.Sign(R("TT_Mouth_Closed").bounds.center.z - head.center.z);
            fwdLocal = new Vector3(0, 0, front);
            leftLocal = new Vector3(sx, 0, 0);
            // bounds centre of the left eyeball against the Blender value: the offset of the import (if any) moves the camera
            var eyeMesh = eyeL is SkinnedMeshRenderer es ? es.sharedMesh : eyeL.GetComponent<MeshFilter>()?.sharedMesh;
            Vector3 mean = eyeMesh != null ? eyeL.transform.TransformPoint(eyeMesh.bounds.center) : eyeL.bounds.center;
            var bl = spec.eyeBallL;
            var expect = new Vector3(-bl[0], bl[2], -bl[1]);
            offset = mean - expect;
            Log($"renderers {rends.Length}, skinned with keys {skins.Count}, eye mats {eyeMat.Count}, cards {cardR.Count}, streams {streamR.Count}, " +
                $"tears {tearR.Count}, hair {hairR.Count}, unmapped [{string.Join(", ", unmapped)}], sx {sx}, front {front}, " +
                $"eyeL mean {mean.ToString("F4")} expected {expect.ToString("F4")} offset {offset.ToString("F4")}");
        }

        Shot S(string n) => spec.shots.First(s => s.name == n);

        void Frame(Shot s, float scale, out int w, out int h)
        {
            w = (int)(s.w * scale);
            h = (int)(s.h * scale);
            cam.orthographic = true;
            cam.orthographicSize = s.ortho * 0.5f * (s.w >= s.h ? (float)h / w : 1f);
            float t = s.yaw * Mathf.Deg2Rad;
            var p = new Vector3(-s.loc[0], s.loc[2], -s.loc[1]) + offset;
            cam.transform.SetPositionAndRotation(p, Quaternion.LookRotation(new Vector3(Mathf.Sin(t), 0, -Mathf.Cos(t)), Vector3.up));
        }

        IEnumerator Capture(string rel, string shot, float scale, State st, bool hairOn = true, bool cards = true)
        {
            state = st; hair = hairOn; browCards = cards;
            Frame(S(shot), scale, out int w, out int h);
            yield return null;
            yield return new WaitForEndOfFrame();
            Compose();
            var rt = new RenderTexture(w, h, 24, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB) { antiAliasing = 4 };
            cam.targetTexture = rt;
            cam.Render();
            cam.targetTexture = null;
            var prev = RenderTexture.active;
            RenderTexture.active = rt;
            var tex = new Texture2D(w, h, TextureFormat.RGB24, false);
            tex.ReadPixels(new Rect(0, 0, w, h), 0, 0);
            tex.Apply();
            RenderTexture.active = prev;
            string path = Path.Combine(outDir, rel);
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            File.WriteAllBytes(path, tex.EncodeToPNG());
            Destroy(tex);
            rt.Release();
            Destroy(rt);
            WriteWeights(rel);
        }

        void WriteWeights(string tag)
        {
            var sb = new StringBuilder();
            sb.Append("{\"tag\":\"").Append(tag).Append("\",\"yaw\":").Append(ViewYaw.ToString("R", CultureInfo.InvariantCulture));
            sb.Append(",\"state\":").Append(state.ToString());
            foreach (var (r, names, grp) in skins)
            {
                if (grp != GEye || !r.name.StartsWith("Eye_Lids")) continue;
                sb.Append(",\"").Append(r.name).Append("\":{");
                for (int i = 0; i < names.Length; i++)
                    sb.Append(i > 0 ? "," : "").Append('"').Append(names[i]).Append("\":").Append((r.GetBlendShapeWeight(i) / 100f).ToString("R", CultureInfo.InvariantCulture));
                sb.Append('}');
            }
            var pl = eyeMat["L"].GetVector("_Proj");
            sb.Append(string.Format(CultureInfo.InvariantCulture,
                ",\"mat\":{{\"sparkle\":{0},\"iris_scale\":{1},\"pitch\":{2},\"flow\":{3},\"reveal\":{4},\"projL\":[{5},{6},{7},{8}]}}",
                sparkle, irisScale, pitch, flowV, browAlpha, pl.x, pl.y, pl.z, pl.w));
            sb.Append(string.Format(CultureInfo.InvariantCulture, ",\"on\":{{\"line\":{0},\"o\":{1},\"smile\":{2},\"tear\":{3},\"flow\":{4},\"cards\":{5}}}}}",
                showLine ? 1 : 0, showO ? 1 : 0, mouthOpen > 0.02f ? 1 : 0, showTear ? 1 : 0, showFlow ? 1 : 0, cardR.Count > 0 && cardR[0].enabled ? 1 : 0));
            weights.WriteLine(sb.ToString());
            weights.Flush();
        }

        static State St(float happy = 0, float angry = 0, float angry2 = 0, float sad = 0, float cry = 0, float surprise = 0,
                        float blink = 0, float gaze = 0, float flow = -1)
            => new State { happy = happy, angry = angry, angry2 = angry2, sad = sad, cry = cry, surprise = surprise, blink = blink, gaze = gaze, flow = flow };

        IEnumerator Shots()
        {
            var ang5 = new[] { 0, 35, -35, 45, -45 };
            foreach (int a in ang5)
                foreach (float h in new[] { 0.6f, 0.7f, 0.8f, 0.9f, 1.0f })
                    yield return Capture($"happy/Happy{Mathf.RoundToInt(h * 100):000}_eyes_{a}.png", $"eyes_{a}", 1.5f, St(happy: h));
            foreach (int a in ang5)
                foreach (var (n, st) in new[] { ("Angry100", St(angry: 1)), ("Angry2_100", St(angry2: 1)) })
                {
                    yield return Capture($"angrybrow/{n}_pull_eyes_{a}.png", $"eyes_{a}", 1.5f, st);
                    yield return Capture($"angrybrow/{n}_hide_eyes_{a}.png", $"eyes_{a}", 1.5f, st, true, false);
                    yield return Capture($"angrybrow/{n}_pull_face_{a}.png", $"face_{a}", 1.0f, st);
                }
            foreach (int a in new[] { 0, 35, -35 })
            {
                foreach (float f in new[] { 0f, 0.25f, 0.5f, 0.75f, 1f })
                    yield return Capture($"cry/Flow{Mathf.RoundToInt(f * 100):000}_face_{a}.png", $"face_{a}", 1.0f, St(sad: 1, cry: 1, flow: f));
                yield return Capture($"cry/Flow100_eyes_{a}.png", $"eyes_{a}", 1.5f, St(sad: 1, cry: 1, flow: 1));
            }
            foreach (int a in new[] { 0, 35, -35 })
                foreach (float sv in new[] { 0.5f, 1f })
                    foreach (float gz in new[] { -0.25f, 0f, 0.25f })
                        yield return Capture(string.Format(CultureInfo.InvariantCulture, "surprise/S{0:000}_g{1}{2:0.00}_eyes_{3}.png",
                                                           Mathf.RoundToInt(sv * 100), gz < 0 ? "-" : "+", Mathf.Abs(gz), a),
                                             $"eyes_{a}", 1.5f, St(surprise: sv, gaze: gz));
            foreach (int a in new[] { 0, 35, -35, 45, -45, 60, -60 })
                foreach (var (n, st) in new[]
                         {
                             ("Neutral", St()), ("Happy060", St(happy: 0.6f)), ("Angry100", St(angry: 1)), ("Sad100", St(sad: 1)),
                             ("Cry100", St(sad: 1, cry: 1)), ("Surprise100", St(surprise: 1)), ("Surprise100_gR", St(surprise: 1, gaze: -0.25f)),
                             ("Angry100_b05", St(angry: 1, blink: 0.5f)),
                         })
                    yield return Capture($"view/{n}_view_{a}.png", $"eyes_{a}", 1.5f, st, false);
            var seq = new[] { St(), St(happy: 1), St(angry: 1), St(sad: 1, cry: 0.6f), St(surprise: 1) };
            var frames = new List<State>();
            for (int i = 0; i < seq.Length - 1; i++)
                for (int k = 0; k < 8; k++) frames.Add(seq[i].Lerp(seq[i + 1], k / 8f));
            frames.Add(seq[seq.Length - 1]);
            foreach (int a in new[] { 0, 35 })
                for (int f = 0; f < frames.Count; f++)
                    yield return Capture($"transition/t{a}_{f:00}.png", $"face_{a}", 0.8f, frames[f]);
            Log("shots done");
        }

        /// <summary>real-time play: emotions crossfade, Blink pulses, gaze sweeps, camera orbits up to +-60 deg; per-frame checks</summary>
        IEnumerator Sweep()
        {
            var seq = new[] { St(), St(happy: 1), St(angry: 1), St(angry2: 1), St(sad: 1, cry: 0.6f), St(surprise: 1), St(happy: 0.7f), St() };
            var face0 = S("face_0");
            Frame(face0, 0.8f, out int w, out int h);
            Vector3 pivot = cam.transform.position + cam.transform.forward * 3f;
            int frames = 0, bad = 0, captures = 0;
            float maxJump = 0;
            string maxJumpAt = "";
            var last = new Dictionary<(int, int), float>();
            int prevFps = Application.targetFrameRate;
            Application.targetFrameRate = 60;
            float t0 = Time.time, nextCap = 0, tPrev = -1, bPrev = 1;
            hair = true; browCards = true;
            while (Time.time - t0 < sweepSeconds)
            {
                float t = Time.time - t0;
                float seg = t / sweepSeconds * (seq.Length - 1);
                int i = Mathf.Min((int)seg, seq.Length - 2);
                var st = seq[i].Lerp(seq[i + 1], Sm(seg - i));
                float bp = (t % 2.7f) / 0.24f;
                st.blink = bp < 1 ? 1 - Mathf.Abs(2 * bp - 1) : 0;
                st.gaze = 0.25f * Mathf.Sin(2 * Mathf.PI * t / 5f);
                state = st;
                float yaw = 60f * Mathf.Sin(2 * Mathf.PI * t / 8f);
                float r = yaw * Mathf.Deg2Rad;
                var dir = new Vector3(Mathf.Sin(r), 0, -Mathf.Cos(r));
                cam.transform.SetPositionAndRotation(pivot - dir * 3f, Quaternion.LookRotation(dir, Vector3.up));
                yield return new WaitForEndOfFrame();                 // LateUpdate composed this frame
                frames++;
                // step per 1/60 s of the state clock, outside Blink pulses (a Blink pulse is fast by design)
                bool rated = tPrev >= 0 && st.blink == 0 && bPrev == 0 && t > tPrev;
                for (int si = 0; si < skins.Count; si++)
                {
                    var (sr, names, grp) = skins[si];
                    for (int k = 0; k < names.Length; k++)
                    {
                        float v = sr.GetBlendShapeWeight(k);
                        if (float.IsNaN(v) || float.IsInfinity(v) || v < -1e-3f || v > 200.001f) bad++;
                        if (grp == GEye && rated && last.TryGetValue((si, k), out var pv))
                        {
                            float j = Mathf.Abs(v - pv) / ((t - tPrev) * 60f);
                            if (j > maxJump) { maxJump = j; maxJumpAt = $"{sr.name}/{names[k]} t {t:F2} yaw {ViewYaw:F1}"; }
                        }
                        last[(si, k)] = v;
                    }
                }
                tPrev = t;
                bPrev = st.blink;
                if (t >= nextCap)
                {
                    nextCap += 0.5f;
                    var rt = new RenderTexture(w, h, 24, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB) { antiAliasing = 4 };
                    cam.targetTexture = rt;
                    cam.Render();
                    cam.targetTexture = null;
                    var prev = RenderTexture.active;
                    RenderTexture.active = rt;
                    var tex = new Texture2D(w, h, TextureFormat.RGB24, false);
                    tex.ReadPixels(new Rect(0, 0, w, h), 0, 0);
                    tex.Apply();
                    RenderTexture.active = prev;
                    Directory.CreateDirectory(Path.Combine(outDir, "sweep"));
                    File.WriteAllBytes(Path.Combine(outDir, "sweep", $"f{captures:00}.png"), tex.EncodeToPNG());
                    Destroy(tex);
                    rt.Release();
                    Destroy(rt);
                    WriteWeights($"sweep/f{captures:00}.png t {t:F2}");
                    captures++;
                }
            }
            Application.targetFrameRate = prevFps;
            Log($"sweep {sweepSeconds}s at 60 fps: frames {frames}, captures {captures}, weights NaN / out of range {bad}, " +
                $"largest eye-key step per 1/60 s outside Blink pulses (%) {maxJump:F2} at {maxJumpAt}");
        }

        IEnumerator Start()
        {
            Directory.CreateDirectory(outDir);
            weights = new StreamWriter(Path.Combine(outDir, "weights.jsonl"), false);
            spec = JsonUtility.FromJson<Spec>(specJson.text);
            foreach (var p in spec.proj) proj[p.side] = p;
            var go = new GameObject("Race3DExprCheckCam");
            cam = go.AddComponent<Camera>();
            cam.clearFlags = CameraClearFlags.SolidColor;
            cam.backgroundColor = Color.white;
            cam.nearClipPlane = 0.01f;
            cam.farClipPlane = 10f;
            cam.allowMSAA = true;
            Build();
            yield return null;
            if (runShots) yield return Shots();
            if (runSweep) yield return Sweep();
            Log("ALL_DONE");
        }
    }
}
