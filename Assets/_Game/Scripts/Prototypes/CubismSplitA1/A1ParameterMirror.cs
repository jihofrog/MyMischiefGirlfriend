using System.Collections.Generic;
using Live2D.Cubism.Core;
using Live2D.Cubism.Framework.Physics;
using UnityEngine;

namespace MMG.Prototypes.CubismSplitA1
{
    /// <summary>
    /// A1 prototype: copies final parameter values (after physics) and part opacities from a source model with a
    /// different moc3, matched by ID. Same timing as the A0 mirror (after every CubismUpdateController LateUpdate,
    /// before the Cubism schedule phase). With <see cref="Mirror"/> off this model runs its own physics.
    /// </summary>
    [DefaultExecutionOrder(31000)]
    public sealed class A1ParameterMirror : MonoBehaviour
    {
        public CubismModel Source;
        public bool Mirror = true;

        CubismModel target;
        CubismPhysicsController physics;
        int[] paramMap, partMap;

        public int MatchedParameters { get; private set; }
        public int MatchedParts { get; private set; }
        public List<string> UnmatchedParameters { get; } = new List<string>();
        public List<string> UnmatchedParts { get; } = new List<string>();

        void Awake()
        {
            target = GetComponent<CubismModel>();
            physics = GetComponent<CubismPhysicsController>();
        }

        void Start()
        {
            paramMap = Map(target.Parameters, Source.Parameters, p => p.Id, UnmatchedParameters, out int mp);
            partMap = Map(target.Parts, Source.Parts, p => p.Id, UnmatchedParts, out int mq);
            MatchedParameters = mp;
            MatchedParts = mq;
            ApplyMode();
        }

        static int[] Map<T>(T[] dst, T[] src, System.Func<T, string> id, List<string> unmatched, out int matched)
        {
            var index = new Dictionary<string, int>();
            for (int i = 0; i < src.Length; i++) index[id(src[i])] = i;
            var map = new int[dst.Length];
            matched = 0;
            for (int i = 0; i < dst.Length; i++)
            {
                if (index.TryGetValue(id(dst[i]), out int s)) { map[i] = s; matched++; }
                else { map[i] = -1; unmatched.Add(id(dst[i])); }
            }
            return map;
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
            if (!Mirror || paramMap == null || Source == null || !Source.isActiveAndEnabled) return;
            var src = Source.Parameters;
            var dst = target.Parameters;
            for (int i = 0; i < dst.Length; i++) if (paramMap[i] >= 0) dst[i].Value = src[paramMap[i]].Value;
            var srcParts = Source.Parts;
            var dstParts = target.Parts;
            for (int i = 0; i < dstParts.Length; i++) if (partMap[i] >= 0) dstParts[i].Opacity = srcParts[partMap[i]].Opacity;
        }
    }
}
