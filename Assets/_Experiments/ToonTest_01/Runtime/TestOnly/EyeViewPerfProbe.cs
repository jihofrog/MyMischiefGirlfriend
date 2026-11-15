using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using UnityEngine;

namespace MMG.Experiments.EyeView
{
    /// <summary>
    /// test only (desktop Editor play mode, not a device measurement): with the given controllers active, for N frames:
    /// summed EyeViewController compose cost per frame and the frame time (unscaled delta); then the same with the view
    /// correction off. The camera orbits slowly so the view keys keep changing. Writes &lt;outFile&gt;.
    /// </summary>
    public sealed class EyeViewPerfProbe : MonoBehaviour
    {
        public List<EyeViewController> controllers = new List<EyeViewController>();
        public Transform orbitPivot;
        public Camera cam;
        public int frames = 300;
        public string outFile;
        public string label;

        int f, phase;
        double sumCost, sumDt, maxCost;
        readonly List<string> lines = new List<string>();
        readonly Stopwatch sw = Stopwatch.StartNew();
        double last;

        void Update()
        {
            float yaw = Mathf.Sin(f * 0.02f) * 60f;
            cam.transform.position = orbitPivot.position + Quaternion.AngleAxis(yaw, Vector3.up) * (orbitPivot.forward * 2.4f);
            cam.transform.LookAt(orbitPivot.position);
        }

        void LateUpdate()
        {
            double now = sw.Elapsed.TotalMilliseconds;
            if (f > 0)
            {
                double cost = 0;
                foreach (var c in controllers) cost += c.LastCostMicroseconds;
                sumCost += cost; maxCost = System.Math.Max(maxCost, cost);
                sumDt += now - last;
            }
            last = now;
            f++;
            if (f <= frames) return;
            string costMean = (sumCost / frames).ToString("F1"), costMax = maxCost.ToString("F1"), dtMean = (sumDt / frames).ToString("F2");
            lines.Add("{\"label\": \"" + label + "\", \"view_correction\": " + (phase == 0 ? "true" : "false") + ", \"characters\": " + controllers.Count +
                      ", \"controller_us_per_frame_mean\": " + costMean + ", \"controller_us_per_frame_max\": " + costMax + ", \"frame_ms_mean\": " + dtMean + "}");
            f = 0; sumCost = sumDt = maxCost = 0;
            phase++;
            foreach (var c in controllers) c.viewCorrection = phase == 0;
            if (phase < 2) return;
            File.WriteAllLines(outFile, lines);
            enabled = false;
        }
    }
}
