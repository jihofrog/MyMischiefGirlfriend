using Live2D.Cubism.Core;
using UnityEngine;

namespace MMG.Prototypes.CubismSplitA1
{
    /// <summary>
    /// A1 prototype: parameter differences by ID after physics and mirroring (end of LateUpdate, before the Cubism
    /// schedule phase), i.e. the values each model is actually updated with this frame.
    /// </summary>
    [DefaultExecutionOrder(32500)]
    public sealed class A1ParamProbe : MonoBehaviour
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
            SingleVsBody = A1Harness.MaxParamDiff(Single, Body, out var a);
            SingleVsBodyId = a;
            BodyVsBlouse = A1Harness.MaxParamDiff(Body, Blouse, out var b);
            BodyVsBlouseId = b;
        }
    }
}
