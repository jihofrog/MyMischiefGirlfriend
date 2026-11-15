using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Text;
using UnityEngine;

namespace MMG.Experiments.EyeView
{
    /// <summary>
    /// ToonTest_01 test only: plays fixed sequences (head turn, blink, gaze, smile, camera above / below, dolly) on each
    /// model in turn, one sequence step per frame, and saves what the camera rendered in the normal render loop of that
    /// frame (read at the end of the frame, so animation, EyeViewController and skinning are all of the same frame):
    /// outDir/&lt;tag&gt;/&lt;sequence&gt;_&lt;frame&gt;.png and &lt;sequence&gt;.csv with the controller values. Writes outDir/done.txt at the end.
    /// </summary>
    [DefaultExecutionOrder(2000)]
    public sealed class EyeViewTestRig : MonoBehaviour
    {
        [System.Serializable]
        public sealed class Entry
        {
            public string tag;
            public GameObject root;
            public EyeViewController controller;
            public List<Material> materials = new List<Material>();
        }

        public List<Entry> entries = new List<Entry>();
        public Camera cam;
        public string outDir;
        public Vector3 lightLocal;              // light direction in model space for a camera in front (t03 sun)
        public Vector3 faceForwardLocal = Vector3.forward;
        public int width = 640, height = 400;
        public float fov = 22f, distance = 0.85f;
        [Tooltip("default: the v6j test sequences; final: head turn 0 -> +-60 for the whole face and for the eyes close up")]
        public string sequenceSet = "default";

        struct Step
        {
            public float yaw, pitch, dist, blink, eyeSmile, smile, gaze, lift;
        }

        readonly List<(string name, List<Step> steps)> sequences = new List<(string, List<Step>)>();
        int entry, frame;
        RenderTexture rt;
        Texture2D tex;
        StringBuilder csv;
        double costSum, costMax;
        int costN;

        static List<Step> Ramp(params (float at, Step s)[] keys)
        {
            // piecewise linear between keys, one step per frame; "at" = frame number
            var list = new List<Step>();
            for (int k = 0; k < keys.Length - 1; k++)
            {
                var (f0, a) = keys[k];
                var (f1, b) = keys[k + 1];
                for (int f = (int)f0; f < (int)f1 || (k == keys.Length - 2 && f == (int)f1); f++)
                {
                    float t = f1 > f0 ? (f - f0) / (f1 - f0) : 0;
                    list.Add(new Step
                    {
                        yaw = Mathf.Lerp(a.yaw, b.yaw, t), pitch = Mathf.Lerp(a.pitch, b.pitch, t), dist = Mathf.Lerp(a.dist, b.dist, t),
                        blink = Mathf.Lerp(a.blink, b.blink, t), eyeSmile = Mathf.Lerp(a.eyeSmile, b.eyeSmile, t),
                        smile = Mathf.Lerp(a.smile, b.smile, t), gaze = Mathf.Lerp(a.gaze, b.gaze, t), lift = Mathf.Lerp(a.lift, b.lift, t)
                    });
                }
            }
            return list;
        }

        Step S(float yaw, float pitch = 0, float dist = -1, float blink = 0, float eyeSmile = 0, float smile = 0, float gaze = 0, float lift = 0)
            => new Step { yaw = yaw, pitch = pitch, dist = dist < 0 ? distance : dist, blink = blink, eyeSmile = eyeSmile, smile = smile, gaze = gaze, lift = lift };

        void Start()
        {
            if (sequenceSet == "final")
            {
                // 0.5 deg per frame: 0 -> 60 -> 0 -> -60 -> 0 in 481 frames (16 s at 30 fps)
                sequences.Add(("face_turn", Ramp((0, S(0, dist: 1.25f, lift: -0.07f)), (120, S(60, dist: 1.25f, lift: -0.07f)), (240, S(0, dist: 1.25f, lift: -0.07f)),
                                                 (360, S(-60, dist: 1.25f, lift: -0.07f)), (480, S(0, dist: 1.25f, lift: -0.07f)))));
                sequences.Add(("eye_turn", Ramp((0, S(0, dist: 0.42f)), (120, S(60, dist: 0.42f)), (240, S(0, dist: 0.42f)),
                                                (360, S(-60, dist: 0.42f)), (480, S(0, dist: 0.42f)))));
            }
            else
            {
            // 1 deg per frame for the turns, so 15-45 deg is 30 frames each way
            sequences.Add(("turn", Ramp((0, S(0)), (60, S(60)), (120, S(0)), (180, S(-60)), (240, S(0)))));
            sequences.Add(("blink35", Ramp((0, S(35)), (6, S(35)), (11, S(35, blink: 1)), (16, S(35)), (24, S(35)), (29, S(35, blink: 1)),
                                           (34, S(35, blink: 0.5f)), (39, S(35)), (45, S(35)))));
            sequences.Add(("gaze35", Ramp((0, S(35)), (20, S(35, gaze: 0.25f)), (60, S(35, gaze: -0.25f)), (80, S(35)))));
            sequences.Add(("smile35", Ramp((0, S(35)), (12, S(35, eyeSmile: 1)), (24, S(35)), (36, S(35, eyeSmile: 1, smile: 1)), (48, S(35)))));
            sequences.Add(("above", Ramp((0, S(0, 25)), (60, S(60, 25)), (120, S(0, 25)), (180, S(-60, 25)), (240, S(0, 25)))));
            sequences.Add(("below", Ramp((0, S(0, -20)), (60, S(60, -20)), (120, S(0, -20)), (180, S(-60, -20)), (240, S(0, -20)))));
            sequences.Add(("dolly35", Ramp((0, S(35, dist: 2.2f)), (60, S(35, dist: 0.32f)), (90, S(35, dist: 0.32f)), (150, S(35, dist: 2.2f)))));
            sequences.Add(("dolly25", Ramp((0, S(25, dist: 2.2f)), (60, S(25, dist: 0.32f)), (120, S(25, dist: 2.2f)))));
            }
            rt = new RenderTexture(width, height, 24, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB) { antiAliasing = 4 };
            tex = new Texture2D(width, height, TextureFormat.RGB24, false);
            cam.targetTexture = rt;
            cam.fieldOfView = fov;
            cam.enabled = true;
            StartCoroutine(Run());
        }

        void Activate()
        {
            for (int i = 0; i < entries.Count; i++) entries[i].root.SetActive(i == entry);
            Directory.CreateDirectory(Path.Combine(outDir, entries[entry].tag));
            csv = new StringBuilder("frame,yaw_set,pitch_set,dist,blink,eyesmile,smile,gaze,yawL,yawR,pitchL,farL,farR,sideL,sideR,cost_us\n");
        }

        void Apply(Entry e, Step st)
        {
            float sx = Mathf.Sign(Vector3.Dot(e.controller.characterLeftLocal, Vector3.right));
            // camera stays in front (world), the head turns: camera yaw relative to the face = st.yaw
            e.root.transform.rotation = Quaternion.AngleAxis(-sx * st.yaw, Vector3.up);
            Vector3 pivot = (e.controller.eyeL.position + e.controller.eyeR.position) * 0.5f + Vector3.up * st.lift;
            Vector3 front = faceForwardLocal.normalized;
            Vector3 camDir = Quaternion.AngleAxis(-st.pitch, Vector3.Cross(Vector3.up, front).normalized) * front;
            cam.transform.position = pivot + camDir * st.dist;
            cam.transform.rotation = Quaternion.LookRotation(-camDir, Vector3.up);
            // the light keeps its angle to the camera (t03 sun): turned with the camera around the head
            Vector3 lightWorld = e.root.transform.rotation * (Quaternion.AngleAxis(sx * st.yaw, Vector3.up) * lightLocal);
            foreach (var m in e.materials)
                if (m != null && m.HasProperty("_LightDir")) m.SetVector("_LightDir", lightWorld);
            var c = e.controller;
            c.blink = st.blink; c.eyeSmile = st.eyeSmile; c.smile = st.smile; c.gaze = st.gaze; c.surprise = 0;
        }

        IEnumerator Run()
        {
            var endOfFrame = new WaitForEndOfFrame();
            for (entry = 0; entry < entries.Count; entry++)
            {
                Activate();
                var e = entries[entry];
                foreach (var (name, steps) in sequences)
                {
                    for (frame = 0; frame < steps.Count; frame++)
                    {
                        yield return null;                        // after Update: set this frame's state
                        var st = steps[frame];
                        Apply(e, st);
                        yield return endOfFrame;                  // EyeViewController (LateUpdate) and rendering done
                        var prev = RenderTexture.active;
                        RenderTexture.active = rt;
                        tex.ReadPixels(new Rect(0, 0, width, height), 0, 0);
                        tex.Apply();
                        RenderTexture.active = prev;
                        File.WriteAllBytes(Path.Combine(outDir, e.tag, $"{name}_{frame:000}.png"), tex.EncodeToPNG());
                        var c = e.controller;
                        costSum += c.LastCostMicroseconds; costMax = System.Math.Max(costMax, c.LastCostMicroseconds); costN++;
                        csv.AppendLine(string.Join(",", frame, st.yaw, st.pitch, st.dist, st.blink, st.eyeSmile, st.smile, st.gaze,
                            c.YawL.ToString("F2"), c.YawR.ToString("F2"), c.PitchL.ToString("F2"), c.FarL.ToString("F3"), c.FarR.ToString("F3"),
                            c.SideL.ToString("F3"), c.SideR.ToString("F3"), c.LastCostMicroseconds.ToString("F1")));
                    }
                    File.WriteAllText(Path.Combine(outDir, e.tag, $"{name}.csv"), csv.ToString());
                    csv.Clear().Append("frame,yaw_set,pitch_set,dist,blink,eyesmile,smile,gaze,yawL,yawR,pitchL,farL,farR,sideL,sideR,cost_us\n");
                }
            }
            cam.enabled = false;
            File.WriteAllText(Path.Combine(outDir, "done.txt"),
                $"frames {costN}, controller cost mean {costSum / System.Math.Max(costN, 1):F1} us, max {costMax:F1} us\n");
        }

        void OnDestroy()
        {
            if (rt != null) rt.Release();
        }
    }
}
