using System.Collections.Generic;
using Live2D.Cubism.Core;
using Live2D.Cubism.Rendering;
using UnityEngine;

namespace MMG.Prototypes.CubismSplitA1
{
    /// <summary>
    /// A1 prototype: places the drawables of a partial moc3 at the render order they have in the master model, so
    /// several moc3 files in one sorting group interleave like the master. Each moc3 numbers its render order from 0,
    /// so the offset goes into <see cref="CubismRenderer.LocalSortingOrder"/>:
    /// BackToFrontOrder sorts by (own order + local), so local = master - own;
    /// BackToFrontZ sorts by local first and own order only breaks ties through depth, so local = master.
    /// Re-applied every frame in case a draw order key changes the model's own order.
    /// </summary>
    [DefaultExecutionOrder(32100)]
    public sealed class A1SortingMap : MonoBehaviour
    {
        public enum MapMode { None, OrderDelta, ZReference }

        public MapMode Mode = MapMode.None;

        CubismModel model;
        CubismRenderer[] renderers;
        int[] master;

        public int Unmapped { get; private set; }

        /// <summary>Master render order by drawable ID (from the full model, or a baked table).</summary>
        public void SetMaster(IReadOnlyDictionary<string, int> masterOrder)
        {
            Init();
            master = new int[renderers.Length];
            Unmapped = 0;
            for (int i = 0; i < renderers.Length; i++)
            {
                if (masterOrder.TryGetValue(model.Drawables[i].Id, out int o)) master[i] = o;
                else { master[i] = -1; Unmapped++; }
            }
            Apply();
        }

        public void SetMode(MapMode mode)
        {
            Mode = mode;
            Apply();
        }

        void Init()
        {
            if (renderers != null) return;
            model = GetComponent<CubismModel>();
            renderers = new CubismRenderer[model.Drawables.Length];
            for (int i = 0; i < renderers.Length; i++) renderers[i] = model.Drawables[i].GetComponent<CubismRenderer>();
        }

        void LateUpdate() => Apply();

        void Apply()
        {
            if (master == null) return;
            var own = model.AllDrawObjectsRenderOrder;
            for (int i = 0; i < renderers.Length; i++)
            {
                int local = 0;
                if (master[i] >= 0)
                {
                    if (Mode == MapMode.OrderDelta) local = master[i] - own[i];
                    else if (Mode == MapMode.ZReference) local = master[i];
                }
                renderers[i].LocalSortingOrder = local;
            }
        }
    }
}
