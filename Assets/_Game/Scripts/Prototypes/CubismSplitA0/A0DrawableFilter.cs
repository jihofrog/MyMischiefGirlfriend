using System;
using System.Collections.Generic;
using Live2D.Cubism.Core;
using Live2D.Cubism.Rendering;
using UnityEngine;

namespace MMG.Prototypes.CubismSplit
{
    /// <summary>
    /// A0 prototype: hides drawables of one model instance by turning their MeshRenderer off every frame, after the
    /// Cubism update (the SDK only touches MeshRenderer.enabled when a drawable's visibility flag changes, and the URP
    /// pass skips disabled renderers). Never turns a renderer on, so the SDK's own visibility is kept.
    /// </summary>
    [DefaultExecutionOrder(32000)]
    public sealed class A0DrawableFilter : MonoBehaviour
    {
        public enum FilterMode { HideListed, ShowOnlyListed, HideAll, None }

        public FilterMode Mode = FilterMode.None;
        public List<string> DrawableIds = new List<string>();

        CubismRenderer[] renderers;
        readonly HashSet<string> ids = new HashSet<string>(StringComparer.Ordinal);

        public void Set(FilterMode mode, IEnumerable<string> drawableIds)
        {
            Mode = mode;
            DrawableIds = new List<string>(drawableIds);
            Apply();
        }

        void Start() => Apply();

        void LateUpdate() => Apply();

        void Apply()
        {
            if (renderers == null)
            {
                var model = GetComponent<CubismModel>();
                if (model == null) return;
                renderers = new CubismRenderer[model.Drawables.Length];
                for (int i = 0; i < model.Drawables.Length; i++) renderers[i] = model.Drawables[i].GetComponent<CubismRenderer>();
            }
            ids.Clear();
            foreach (var id in DrawableIds) ids.Add(id);
            foreach (var r in renderers)
            {
                if (r == null || r.MeshRenderer == null) continue;
                bool listed = ids.Contains(r.name);
                bool hide = Mode == FilterMode.HideAll
                            || (Mode == FilterMode.HideListed && listed)
                            || (Mode == FilterMode.ShowOnlyListed && !listed);
                if (hide && r.MeshRenderer.enabled) r.MeshRenderer.enabled = false;
            }
        }

        /// <summary>
        /// Turns the given renderers back on. Only for drawables known to be visible in the current pose: the SDK
        /// exposes no visibility flag to read back.
        /// </summary>
        public void Reveal(IEnumerable<string> drawableIds)
        {
            var reveal = new HashSet<string>(drawableIds, StringComparer.Ordinal);
            if (renderers == null) Apply();
            foreach (var r in renderers)
                if (r != null && r.MeshRenderer != null && reveal.Contains(r.name)) r.MeshRenderer.enabled = true;
        }
    }
}
