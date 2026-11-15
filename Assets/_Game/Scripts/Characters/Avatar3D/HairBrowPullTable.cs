using System;
using System.Collections.Generic;
using UnityEngine;

namespace MMG.Characters.Avatar3D
{
    /// <summary>
    /// Unity-side appearance data: brow-card pull distance (metres toward the camera) by worn hair <c>itemId</c>.
    /// Not sourced from Admin DB. Missing hair entries use <see cref="defaultPullMeters"/> (bob bangs: 0.03).
    /// </summary>
    [CreateAssetMenu(menuName = "MMG/Appearance/Hair Brow Pull Table", fileName = "HairBrowPullTable")]
    public sealed class HairBrowPullTable : ScriptableObject
    {
        [Serializable]
        public struct Entry
        {
            [Tooltip("hair itemId, e.g. hair_bob_01_01")]
            public string hairItemId;
            [Tooltip("metres the brow card moves toward the camera before the depth test")]
            public float pullMeters;
        }

        [Tooltip("safe default when the worn hair has no entry (bob: 0.03)")]
        public float defaultPullMeters = 0.03f;
        public List<Entry> entries = new List<Entry>();

        public float Resolve(string hairItemId)
        {
            if (!string.IsNullOrEmpty(hairItemId))
            {
                for (int i = 0; i < entries.Count; i++)
                    if (entries[i].hairItemId == hairItemId)
                        return Mathf.Max(0f, entries[i].pullMeters);
            }
            return Mathf.Max(0f, defaultPullMeters);
        }
    }
}
