using System.Collections.Generic;
using System.Diagnostics;
using UnityEngine;

namespace MMG.Experiments.EyeView
{
    /// <summary>
    /// ToonTest_01 v6j eye: the one place that writes the eye blend shape weights each frame.
    /// Inputs (Blink, EyeSmile, Smile, Surprise, gaze) come from the component fields (animate them with the Animator) or,
    /// with <see cref="InputSource.BlendShapes"/>, from the blend shape weights that clips wrote this frame. The view keys
    /// (ViewFar{L,R}, ViewFar{L,R}_GO, ViewFar{L,R}_GI, ViewSide{L,R}) come from the camera direction seen from each eye in
    /// head space. Same formula as eye_v6_common.view_key_values (Blender).
    /// The final weights are written by <see cref="EyeViewLoop"/> at a fixed point of the player loop: after every
    /// LateUpdate and the Director late update, before skinning and rendering. Script execution order does not matter.
    /// Safety: a renderer can be driven by one controller only (a second one stays off); if the loop step did not run in
    /// the last frame (player loop replaced) the watchdog in LateUpdate installs it again and composes once from there;
    /// a missing or disabled camera falls back to Camera.main; NaN never reaches a weight.
    /// LOD: view keys fade out below lodMinEyePixels (eye distance on screen) and can be recomputed every N frames.
    /// </summary>
    [DefaultExecutionOrder(32000)]
    public sealed class EyeViewController : MonoBehaviour
    {
        public enum InputSource
        {
            /// <summary>blink / eyeSmile / smile / surprise / gaze fields (animated or set by code); the controller writes all eye keys</summary>
            Fields,
            /// <summary>Blink / EyeSmile / Smile / Surprise as clips wrote them on the renderers this frame; gaze from the field</summary>
            BlendShapes
        }

        public enum ComposeAt
        {
            /// <summary>EyeViewLoop: after all LateUpdate calls (default)</summary>
            PlayerLoop,
            /// <summary>this component's own LateUpdate (order-dependent; kept only to compare in tests)</summary>
            LateUpdate
        }

        [Header("Rig")]
        public Transform head;
        public Vector3 faceForwardLocal = Vector3.forward;
        public Vector3 characterLeftLocal = Vector3.right;
        public Transform eyeL, eyeR;
        public Camera viewCamera;
        public List<SkinnedMeshRenderer> renderers = new List<SkinnedMeshRenderer>();
        public List<Material> eyeMaterials = new List<Material>();

        [Header("Inputs")]
        public InputSource inputSource = InputSource.Fields;
        public ComposeAt composeAt = ComposeAt.PlayerLoop;
        [Range(0, 1)] public float blink;
        [Range(0, 1)] public float eyeSmile;
        [Range(0, 1)] public float smile;
        [Range(0, 1)] public float surprise;
        [Tooltip("rad, + = toward the character's left")]
        [Range(-0.25f, 0.25f)] public float gaze;

        [Header("View correction")]
        public bool viewCorrection = true;
        public float farFrom = 20f, farTo = 40f;
        public float sideFrom = 50f, sideTo = 65f, sideMax = 0.8f;
        public float gazeOut = 0.25f, gazeIn = 0.12f;
        [Tooltip("|pitch| (deg) where the view keys fade out (camera far above / below)")]
        public float pitchFadeFrom = 50f, pitchFadeTo = 75f;
        [Tooltip("seconds; 0 = follow the camera at once")]
        public float smoothTime;
        [Tooltip("a change of more than this (deg) in one frame is a camera cut: no smoothing")]
        public float cutDegrees = 20f;

        [Header("LOD")]
        [Tooltip("distance between the eye centres on screen (px) below which the view keys fade out; 0 = always on")]
        public float lodMinEyePixels;
        [Tooltip("recompute the view angles every N frames (1 = every frame); Blink etc. are written every frame")]
        public int viewUpdateInterval = 1;

        public float YawL { get; private set; }
        public float YawR { get; private set; }
        public float PitchL { get; private set; }
        public float PitchR { get; private set; }
        public float FarL { get; private set; }
        public float FarR { get; private set; }
        public float SideL { get; private set; }
        public float SideR { get; private set; }
        public double LastCostMicroseconds { get; private set; }
        /// <summary>times a view key had another value than the one written last frame (someone else wrote it)</summary>
        public int ForeignWrites { get; private set; }
        public int ComposedFrame { get; private set; } = -1;
        /// <summary>composes done from LateUpdate because the loop step had not run (watchdog)</summary>
        public int FallbackComposes { get; private set; }
        public bool Registered { get; private set; }
        public float LodFactor { get; private set; } = 1f;
        public Camera UsedCamera { get; private set; }
        /// <summary>the weights (0..1) written in the last compose, by blend shape name</summary>
        public IReadOnlyDictionary<string, float> Written => values;

        struct Slot
        {
            public SkinnedMeshRenderer renderer;
            public int index;
        }

        static readonly string[] BaseKeys = { "Blink", "EyeSmile", "Smile", "Surprise" };

        readonly Dictionary<string, List<Slot>> slots = new Dictionary<string, List<Slot>>();
        readonly Dictionary<string, float> values = new Dictionary<string, float>();
        readonly Stopwatch watch = new Stopwatch();
        Vector3 fwd, left, up;
        float prevYawL, prevYawR, velFarL, velFarR, velSideL, velSideR;
        bool started, initialised;
        int stagger, enabledFrame;

        public bool HasViewKeys => slots.ContainsKey("ViewFarL") || slots.ContainsKey("ViewFarR");

        void OnEnable()
        {
            if (!initialised) Init();
            Registered = EyeViewLoop.Register(this);
            if (!Registered)
            {
                enabled = false;                                         // a second driver for the same renderers: stay off
                return;
            }
            enabledFrame = Time.frameCount;
            stagger = (System.Runtime.CompilerServices.RuntimeHelpers.GetHashCode(this) & 0x7fffffff) % 997;
        }

        void OnDisable()
        {
            if (Registered) EyeViewLoop.Unregister(this);
            Registered = false;
        }

        public void Init()
        {
            slots.Clear();
            foreach (var r in renderers)
            {
                if (r == null) continue;
                var mesh = r.sharedMesh;
                for (int i = 0; i < mesh.blendShapeCount; i++)
                {
                    string n = mesh.GetBlendShapeName(i);
                    if (!slots.TryGetValue(n, out var list)) slots[n] = list = new List<Slot>();
                    list.Add(new Slot { renderer = r, index = i });
                }
            }
            fwd = faceForwardLocal.normalized;
            left = characterLeftLocal.normalized;
            up = Vector3.Cross(fwd, left).normalized;
            if (Vector3.Dot(up, Vector3.up) < 0) up = -up;
            values.Clear();
            started = false;
            initialised = true;
        }

        static float Smooth(float t)
        {
            t = Mathf.Clamp01(t);
            return t * t * (3 - 2 * t);
        }

        void Angles(Camera cam, Transform eye, out float yaw, out float pitch)
        {
            Vector3 dir = cam.orthographic
                ? -cam.transform.forward
                : (cam.transform.position - eye.position).normalized;
            Vector3 d = head.InverseTransformDirection(dir);
            float f = Vector3.Dot(d, fwd), l = Vector3.Dot(d, left), u = Vector3.Dot(d, up);
            yaw = Mathf.Atan2(l, f) * Mathf.Rad2Deg;                    // + = camera toward the character's left
            pitch = Mathf.Atan2(u, Mathf.Sqrt(f * f + l * l)) * Mathf.Rad2Deg;
        }

        void Target(float yaw, float pitch, bool isLeft, out float far, out float side)
        {
            float away = isLeft ? -yaw : yaw;                            // L is the far eye when the camera is on the right
            float pf = 1 - Smooth((Mathf.Abs(pitch) - pitchFadeFrom) / (pitchFadeTo - pitchFadeFrom));
            far = away > 0 ? Smooth((away - farFrom) / (farTo - farFrom)) * pf : 0f;
            side = away > 0 ? Smooth((away - sideFrom) / (sideTo - sideFrom)) * sideMax * pf : 0f;
        }

        float Read(string key)
        {
            if (!slots.TryGetValue(key, out var list) || list.Count == 0) return 0f;
            var s = list[0];
            return s.renderer.GetBlendShapeWeight(s.index) / 100f;
        }

        void LateUpdate()
        {
            if (composeAt == ComposeAt.LateUpdate)
            {
                Compose();
                return;
            }
            // watchdog: the loop step must have run in the previous frame
            if (Time.frameCount > enabledFrame + 1 && EyeViewLoop.LastRunFrame < Time.frameCount - 1)
            {
                EyeViewLoop.EnsureInstalled();
                FallbackComposes++;
                Compose();
            }
        }

        float EyePixels(Camera cam)
        {
            Vector3 a = cam.WorldToScreenPoint(eyeL.position), b = cam.WorldToScreenPoint(eyeR.position);
            if (a.z <= 0 || b.z <= 0) return 0f;
            return Vector2.Distance(a, b);
        }

        /// <summary>called once per frame by EyeViewLoop (or LateUpdate in the comparison mode)</summary>
        public void Compose()
        {
            var cam = viewCamera != null && viewCamera.isActiveAndEnabled ? viewCamera : Camera.main;
            UsedCamera = cam;
            if (cam == null || head == null || !isActiveAndEnabled) return;
            if (!EyeViewLoop.Claim(this))
            {
                UnityEngine.Debug.LogError($"[EyeView] {name}: renderers already driven by another EyeViewController; this one is switched off");
                enabled = false;
                return;
            }
            watch.Restart();
            // someone else wrote a view key since our last write?
            foreach (var kv in values)
            {
                if (System.Array.IndexOf(BaseKeys, kv.Key) >= 0) continue;
                if (slots.TryGetValue(kv.Key, out var list) && list.Count > 0
                    && Mathf.Abs(list[0].renderer.GetBlendShapeWeight(list[0].index) / 100f - kv.Value) > 0.001f)
                {
                    ForeignWrites++;
                    break;
                }
            }
            float b, es, sm, su;
            if (inputSource == InputSource.BlendShapes)
            {
                b = Read("Blink"); es = Read("EyeSmile"); sm = Read("Smile"); su = Read("Surprise");
            }
            else
            {
                b = blink; es = eyeSmile; sm = smile; su = surprise;
            }
            b = Mathf.Clamp01(b); es = Mathf.Clamp01(es);

            float farL = 0, farR = 0, sideL = 0, sideR = 0;
            LodFactor = 1f;
            if (viewCorrection && HasViewKeys && lodMinEyePixels > 0)
            {
                float t = (EyePixels(cam) - lodMinEyePixels) / (lodMinEyePixels * 0.5f);
                LodFactor = Smooth(t);
            }
            bool recompute = viewUpdateInterval <= 1 || !started || (Time.frameCount + stagger) % viewUpdateInterval == 0;
            if (viewCorrection && HasViewKeys && LodFactor > 0f && !recompute)
            {
                farL = FarL; farR = FarR; sideL = SideL; sideR = SideR;
            }
            else if (viewCorrection && HasViewKeys && LodFactor > 0f)
            {
                Angles(cam, eyeL, out float yl, out float pl);
                Angles(cam, eyeR, out float yr, out float pr);
                YawL = yl; YawR = yr; PitchL = pl; PitchR = pr;
                Target(yl, pl, true, out farL, out sideL);
                Target(yr, pr, false, out farR, out sideR);
                bool cut = !started || Mathf.Abs(Mathf.DeltaAngle(yl, prevYawL)) > cutDegrees
                                    || Mathf.Abs(Mathf.DeltaAngle(yr, prevYawR)) > cutDegrees;
                if (smoothTime > 0 && !cut)
                {
                    farL = Mathf.SmoothDamp(FarL, farL, ref velFarL, smoothTime);
                    farR = Mathf.SmoothDamp(FarR, farR, ref velFarR, smoothTime);
                    sideL = Mathf.SmoothDamp(SideL, sideL, ref velSideL, smoothTime);
                    sideR = Mathf.SmoothDamp(SideR, sideR, ref velSideR, smoothTime);
                }
                prevYawL = yl; prevYawR = yr; started = true;
                farL *= LodFactor; farR *= LodFactor; sideL *= LodFactor; sideR *= LodFactor;
            }
            if (float.IsNaN(farL) || float.IsNaN(farR) || float.IsNaN(sideL) || float.IsNaN(sideR)) farL = farR = sideL = sideR = 0f;
            if (float.IsNaN(b)) b = 0f;
            if (float.IsNaN(es)) es = 0f;
            FarL = farL; FarR = farR; SideL = sideL; SideR = sideR;

            values.Clear();
            values["Blink"] = b;
            values["EyeSmile"] = es;
            values["Smile"] = sm;
            values["Surprise"] = su;
            float k = (1 - b) * (1 - es);                                // never closes past Blink 100 %
            Eye("L", 1f, farL, sideL, k);
            Eye("R", -1f, farR, sideR, k);
            foreach (var kv in values)
            {
                // with BlendShapes input the clips own the base keys: leave them as they are
                if (inputSource == InputSource.BlendShapes && System.Array.IndexOf(BaseKeys, kv.Key) >= 0) continue;
                if (!slots.TryGetValue(kv.Key, out var list)) continue;
                foreach (var s in list) s.renderer.SetBlendShapeWeight(s.index, kv.Value * 100f);
            }
            foreach (var m in eyeMaterials)
                if (m != null && m.HasProperty("_GazeYaw")) m.SetFloat("_GazeYaw", gaze);
            ComposedFrame = Time.frameCount;
            watch.Stop();
            LastCostMicroseconds = watch.Elapsed.TotalMilliseconds * 1000.0;
        }

        void Eye(string s, float sg, float far, float side, float k)
        {
            float ws = far * k * (1 - side);
            float gOut = sg * gaze;
            float to = Mathf.Clamp01(gOut / gazeOut), ti = Mathf.Clamp01(-gOut / gazeIn);
            values["ViewFar" + s] = ws * (1 - to - ti);
            values["ViewFar" + s + "_GO"] = ws * to;
            values["ViewFar" + s + "_GI"] = ws * ti;
            values["ViewSide" + s] = side * k;
        }
    }
}
