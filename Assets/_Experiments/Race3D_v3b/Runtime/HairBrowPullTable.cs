using System;
using System.Collections.Generic;
using UnityEngine;

namespace MMG.Experiments.Race3DExpr
{
    /// <summary>
    /// Experiment only: brow-card pull distance (metres toward the camera) looked up by hair itemId.
    /// Formal storage (Unity hair appearance vs Admin) is undecided — this table is the temporary contract.
    /// Do not hard-code the bob's 0.03 m as the only global constant in shaders or drivers.
    /// </summary>
    [CreateAssetMenu(menuName = "MMG/Experiments/Hair Brow Pull Table", fileName = "HairBrowPullTable")]
    public sealed class HairBrowPullTable : ScriptableObject
    {
        [Serializable]
        public struct Entry
        {
            [Tooltip("itemId of the hair, e.g. hair_bob_01_01")]
            public string hairItemId;
            [Tooltip("metres the brow card is moved toward the camera before the depth test")]
            public float pullMeters;
        }

        [Tooltip("used when the worn hair has no entry (bob bangs: 0.03)")]
        public float defaultPullMeters = 0.03f;
        public List<Entry> entries = new List<Entry>();

        public float Resolve(string hairItemId)
        {
            if (!string.IsNullOrEmpty(hairItemId))
            {
                for (int i = 0; i < entries.Count; i++)
                    if (entries[i].hairItemId == hairItemId) return Mathf.Max(0f, entries[i].pullMeters);
            }
            return Mathf.Max(0f, defaultPullMeters);
        }
    }
}
