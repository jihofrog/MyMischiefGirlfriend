using Live2D.Cubism.Core;
using Live2D.Cubism.Framework.Physics;
using UnityEngine;

namespace MMG.Prototypes.CubismSplit
{
    /// <summary>
    /// A0 prototype: copies the final parameter values (after physics) and part opacities from a source model to this
    /// model every frame. Runs after every CubismUpdateController LateUpdate and before the Cubism schedule phase
    /// (appended to PreLateUpdate), so both models are updated from the same values in the same frame.
    /// With <see cref="Mirror"/> off, this model runs its own physics instead (independent mode).
    /// </summary>
    [DefaultExecutionOrder(31000)]
    public sealed class A0ParameterMirror : MonoBehaviour
    {
        public CubismModel Source;
        public bool Mirror = true;

        CubismModel target;
        CubismPhysicsController physics;

        public bool IdsMatch { get; private set; }

        void Awake()
        {
            target = GetComponent<CubismModel>();
            physics = GetComponent<CubismPhysicsController>();
        }

        void Start()
        {
            IdsMatch = Source != null && Source.Parameters.Length == target.Parameters.Length && Source.Parts.Length == target.Parts.Length;
            if (IdsMatch)
            {
                for (int i = 0; i < target.Parameters.Length; i++) IdsMatch &= Source.Parameters[i].Id == target.Parameters[i].Id;
                for (int i = 0; i < target.Parts.Length; i++) IdsMatch &= Source.Parts[i].Id == target.Parts[i].Id;
            }
            ApplyMode();
        }

        public void SetMirror(bool mirror)
        {
            Mirror = mirror;
            ApplyMode();
        }

        void ApplyMode()
        {
            if (physics != null) physics.enabled = !Mirror;
        }

        void LateUpdate()
        {
            if (!Mirror || !IdsMatch) return;
            var src = Source.Parameters;
            var dst = target.Parameters;
            for (int i = 0; i < dst.Length; i++) dst[i].Value = src[i].Value;
            var srcParts = Source.Parts;
            var dstParts = target.Parts;
            for (int i = 0; i < dstParts.Length; i++) dstParts[i].Opacity = srcParts[i].Opacity;
        }
    }
}
