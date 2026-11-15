using System;
using System.Collections.Generic;
using MMG.Data;

namespace MMG.Appearance
{
    public sealed class StatSource
    {
        public StatGroup StatGroup { get; }
        public string SlotId { get; }
        public string ItemId { get; }
        public string VariantId { get; }
        public bool ViaOnePiece { get; }

        public StatSource(StatGroup statGroup, string slotId, string itemId, string variantId, bool viaOnePiece)
        {
            StatGroup = statGroup; SlotId = slotId; ItemId = itemId; VariantId = variantId; ViaOnePiece = viaOnePiece;
        }
    }

    /// <summary>
    /// Which equipped item feeds which stat group (05 document 4-10). Values come from the server; this only
    /// says where they come from: Footwear from shoes only (U1), a one-piece feeds Top and Bottom (U2).
    /// </summary>
    public static class StatSourceResolver
    {
        public static List<StatSource> Resolve(Catalog catalog, EquipmentState state)
        {
            var result = new List<StatSource>();
            var seen = new HashSet<string>(StringComparer.Ordinal);
            foreach (var slot in catalog.Slots)
            {
                if (!slot.StatGroup.HasValue) continue;
                foreach (var e in state.Entries)
                {
                    if (e.SlotId != slot.SlotId || !seen.Add(e.SlotId)) continue;
                    if (!catalog.TryGetItem(e.ItemId, out var item)) continue;
                    result.Add(new StatSource(slot.StatGroup.Value, slot.SlotId, item.ItemId, e.VariantId, item.Kind == ItemKind.OnePiece));
                }
            }
            result.Sort((a, b) =>
            {
                int c = a.StatGroup.CompareTo(b.StatGroup);
                return c != 0 ? c : catalog.SlotOrder(a.SlotId).CompareTo(catalog.SlotOrder(b.SlotId));
            });
            return result;
        }
    }

    /// <summary>
    /// Keeps a one-piece's Top and Bottom values from exceeding a top + bottom combination (policy U2): each value is
    /// capped by the best top or bottom for the same rarity and level. Those reference maxima come from balance data
    /// (undecided). Integer only.
    /// </summary>
    public static class OnePieceStatNormalizer
    {
        public static (int top, int bottom) Normalize(int top, int bottom, int referenceTopMax, int referenceBottomMax)
        {
            if (top < 0 || bottom < 0 || referenceTopMax < 0 || referenceBottomMax < 0)
                throw new ArgumentOutOfRangeException(nameof(top), "stat values are non-negative integers");
            return (Math.Min(top, referenceTopMax), Math.Min(bottom, referenceBottomMax));
        }
    }
}
