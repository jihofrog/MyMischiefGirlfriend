using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Text;
using UnityEngine;
using UnityEngine.Rendering;

namespace MMG.Experiments.EyeView
{
    /// <summary>test only: writes junk into the view keys (and Blink) of the controller's renderers in LateUpdate</summary>
    public abstract class EyeViewJunkWriter : MonoBehaviour
    {
        public EyeViewController target;
        public bool writeBlink;

        void LateUpdate()
        {
            if (target == null) return;
            foreach (var r in target.renderers)
            {
                var m = r.sharedMesh;
                for (int i = 0; i < m.blendShapeCount; i++)
                {
                    string n = m.GetBlendShapeName(i);
                    if (n.StartsWith("View")) r.SetBlendShapeWeight(i, 100f);
                    else if (writeBlink && n == "Blink") r.SetBlendShapeWeight(i, 100f);
                }
            }
        }
    }

    /// <summary>runs before every other LateUpdate</summary>
    [DefaultExecutionOrder(-30000)]
    public sealed class EyeViewJunkWriterEarly : EyeViewJunkWriter { }

    /// <summary>runs after every other LateUpdate</summary>
    [DefaultExecutionOrder(30000)]
    public sealed class EyeViewJunkWriterLate : EyeViewJunkWriter { }

    /// <summary>
    /// test only: for each case (compose point x input source x junk writers), runs N frames and checks at the start of
    /// camera rendering, on every renderer: (1) the view keys are the values the controller wrote this frame,
    /// (2) per eye ViewFar + _GO + _GI + ViewSide &lt;= (1 - Blink)(1 - EyeSmile) (the lids never close past Blink 100 %),
    /// (3) Blink is the animated value (field or clip). Writes &lt;outFile&gt; (json lines) and &lt;outFile&gt;.done.
    /// </summary>
    public sealed class EyeViewRobustnessTest : MonoBehaviour
    {
        public sealed class Case
        {
            public string name;
            public EyeViewController.ComposeAt composeAt;
            public EyeViewController.InputSource input;
            public bool early, late, junkBlink;
            public System.Action<bool> setAnimation;   // true: this case's animation on
        }

        public EyeViewController controller;
        public List<Case> cases = new List<Case>();
        public System.Func<float> expectedBlink;     // what the animation set for Blink this frame
        public int framesPerCase = 150;
        public string outFile;

        EyeViewJunkWriterEarly early;
        EyeViewJunkWriterLate late;
        Case current;
        int frames, keyFail, sumFail, blinkFail, checkedFrames, composedLate;
        float worstSum, worstBlink;
        readonly StringBuilder log = new StringBuilder();

        void Start()
        {
            early = gameObject.AddComponent<EyeViewJunkWriterEarly>();
            late = gameObject.AddComponent<EyeViewJunkWriterLate>();
            early.target = late.target = controller;
            RenderPipelineManager.beginContextRendering += Check;
            StartCoroutine(Run());
        }

        void OnDestroy() => RenderPipelineManager.beginContextRendering -= Check;

        IEnumerator Run()
        {
            log.AppendLine($"{{\"loop\": \"after {EyeViewLoop.InsertedAfter}, before {EyeViewLoop.InsertedBefore}\"}}");
            foreach (var c in cases)
            {
                current = null;
                foreach (var o in cases) o.setAnimation?.Invoke(false);
                controller.composeAt = c.composeAt;
                controller.inputSource = c.input;
                early.enabled = c.early; late.enabled = c.late;
                early.writeBlink = late.writeBlink = c.junkBlink;
                c.setAnimation?.Invoke(true);
                frames = keyFail = sumFail = blinkFail = checkedFrames = composedLate = 0;
                worstSum = worstBlink = 0;
                int foreign0 = controller.ForeignWrites;
                yield return null;
                yield return null;                       // let the animation start
                current = c;
                while (frames < framesPerCase) yield return null;
                current = null;
                log.AppendLine($"{{\"case\": \"{c.name}\", \"frames\": {checkedFrames}, \"view_key_overwritten\": {keyFail}, " +
                               $"\"closing_over_blink100\": {sumFail}, \"worst_excess\": {worstSum:F3}, \"blink_not_animated_value\": {blinkFail}, " +
                               $"\"worst_blink_error\": {worstBlink:F3}, \"foreign_writes_seen\": {controller.ForeignWrites - foreign0}, \"not_composed_this_frame\": {composedLate}}}");
            }
            early.enabled = late.enabled = false;
            File.WriteAllText(outFile, log.ToString());
            File.WriteAllText(outFile + ".done", "ok");
        }

        void Check(ScriptableRenderContext ctx, List<Camera> cams)
        {
            if (current == null) return;
            frames++;
            checkedFrames++;
            if (controller.ComposedFrame != Time.frameCount) composedLate++;
            var w = controller.Written;
            float b = 0, es = 0;
            foreach (var r in controller.renderers)
            {
                var m = r.sharedMesh;
                float sumL = 0, sumR = 0;
                bool keyBad = false;
                for (int i = 0; i < m.blendShapeCount; i++)
                {
                    string n = m.GetBlendShapeName(i);
                    float v = r.GetBlendShapeWeight(i) / 100f;
                    if (n == "Blink") b = v;
                    else if (n == "EyeSmile") es = v;
                    else if (n.StartsWith("View"))
                    {
                        if (w.TryGetValue(n, out var exp) && Mathf.Abs(exp - v) > 0.001f) keyBad = true;
                        if (n.EndsWith("L") || n.Contains("L_")) sumL += v; else sumR += v;
                    }
                }
                if (keyBad) keyFail++;
                float lim = (1 - b) * (1 - es) + 0.001f;
                float ex = Mathf.Max(sumL, sumR) - lim;
                if (ex > 0) { sumFail++; worstSum = Mathf.Max(worstSum, ex); }
                if (expectedBlink != null && (r.name.StartsWith("Eye_Lids") || r.name.StartsWith("Eye_Lash")))
                {
                    float eb = Mathf.Abs(b - expectedBlink());
                    if (eb > 0.01f) { blinkFail++; worstBlink = Mathf.Max(worstBlink, eb); }
                }
            }
        }
    }
}
