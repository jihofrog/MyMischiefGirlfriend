using Live2D.Cubism.Core;
using UnityEngine;

namespace MMG.Prototypes.CubismSplit
{
    /// <summary>
    /// A0 prototype: measures parameter differences after physics and mirroring (end of LateUpdate, before the
    /// Cubism schedule phase), i.e. the values each model is actually updated with this frame.
    /// </summary>
    [DefaultExecutionOrder(32500)]
    public sealed class A0ParamProbe : MonoBehaviour
    {
        public CubismModel Single;
        public CubismModel Body;
        public CubismModel Blouse;

        public float SingleVsBody { get; private set; }
        public string SingleVsBodyId { get; private set; } = "";
        public float BodyVsBlouse { get; private set; }
        public string BodyVsBlouseId { get; private set; } = "";

        void LateUpdate()
        {
            if (Single == null || Body == null || Blouse == null || !Single.isActiveAndEnabled || !Body.isActiveAndEnabled || !Blouse.isActiveAndEnabled) return;
            SingleVsBody = Max(Single, Body, out var a);
            SingleVsBodyId = a;
            BodyVsBlouse = Max(Body, Blouse, out var b);
            BodyVsBlouseId = b;
        }

        static float Max(CubismModel x, CubismModel y, out string id)
        {
            float max = 0;
            id = "";
            for (int i = 0; i < x.Parameters.Length; i++)
            {
                float d = Mathf.Abs(x.Parameters[i].Value - y.Parameters[i].Value);
                if (d > max) { max = d; id = x.Parameters[i].Id; }
            }
            return max;
        }
    }
}
