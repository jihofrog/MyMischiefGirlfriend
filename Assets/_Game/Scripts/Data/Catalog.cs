using System;
using System.Collections.Generic;

namespace MMG.Data
{
    /// <summary>
    /// The common catalog. Lists are sorted (slots by Order then id, everything else by id) so iteration never depends
    /// on input order. Duplicate ids keep the first entry and are listed in <see cref="DuplicateIds"/> for the validator.
    /// </summary>
    public sealed class Catalog
    {
        public int SchemaVersion { get; }
        public int CatalogVersion { get; }
        public CatalogRules Rules { get; }
        public IReadOnlyList<string> BodyTypes { get; }
        public IReadOnlyList<SlotDefinition> Slots { get; }
        public IReadOnlyList<ColorDefinition> Colors { get; }
        public IReadOnlyList<FaceStyleDefinition> FaceStyles { get; }
        public IReadOnlyList<BodyPreset> BodyPresets { get; }
        public IReadOnlyList<ItemDefinition> Items { get; }
        public IReadOnlyList<ItemVariant> Variants { get; }
        public IReadOnlyList<CharacterDefinition> Characters { get; }
        /// <summary>"kind:id" for every id that appeared more than once.</summary>
        public IReadOnlyList<string> DuplicateIds { get; }

        readonly Dictionary<string, SlotDefinition> slots;
        readonly Dictionary<string, ColorDefinition> colors;
        readonly Dictionary<string, FaceStyleDefinition> faceStyles;
        readonly Dictionary<string, BodyPreset> bodyPresets;
        readonly Dictionary<string, ItemDefinition> items;
        readonly Dictionary<string, ItemVariant> variants;
        readonly Dictionary<string, CharacterDefinition> characters;
        readonly Dictionary<string, List<ItemVariant>> variantsByItem = new Dictionary<string, List<ItemVariant>>(StringComparer.Ordinal);

        public Catalog(int schemaVersion, int catalogVersion, CatalogRules rules, IEnumerable<string> bodyTypes,
            IEnumerable<SlotDefinition> slotList, IEnumerable<ColorDefinition> colorList, IEnumerable<FaceStyleDefinition> faceStyleList,
            IEnumerable<BodyPreset> bodyPresetList, IEnumerable<ItemDefinition> itemList, IEnumerable<ItemVariant> variantList,
            IEnumerable<CharacterDefinition> characterList)
        {
            SchemaVersion = schemaVersion;
            CatalogVersion = catalogVersion;
            Rules = rules;
            var duplicates = new List<string>();

            var types = new List<string>(bodyTypes);
            types.Sort(StringComparer.Ordinal);
            for (int i = 1; i < types.Count; i++)
                if (types[i] == types[i - 1]) duplicates.Add("bodyType:" + types[i]);
            BodyTypes = types;

            slots = Index(slotList, s => s.SlotId, "slot", duplicates, out var sortedSlots);
            sortedSlots.Sort((a, b) => a.Order != b.Order ? a.Order.CompareTo(b.Order) : string.CompareOrdinal(a.SlotId, b.SlotId));
            Slots = sortedSlots;
            colors = Index(colorList, c => c.ColorId, "color", duplicates, out var sortedColors);
            Colors = sortedColors;
            faceStyles = Index(faceStyleList, f => f.StyleId, "faceStyle", duplicates, out var sortedFaces);
            FaceStyles = sortedFaces;
            bodyPresets = Index(bodyPresetList, b => b.BodyPresetId, "bodyPreset", duplicates, out var sortedBodies);
            BodyPresets = sortedBodies;
            items = Index(itemList, it => it.ItemId, "item", duplicates, out var sortedItems);
            Items = sortedItems;
            variants = Index(variantList, v => v.VariantId, "variant", duplicates, out var sortedVariants);
            Variants = sortedVariants;
            characters = Index(characterList, c => c.CharacterDefId, "character", duplicates, out var sortedCharacters);
            Characters = sortedCharacters;

            foreach (var v in sortedVariants)
            {
                if (!variantsByItem.TryGetValue(v.ItemId, out var list)) variantsByItem[v.ItemId] = list = new List<ItemVariant>();
                list.Add(v);
            }
            DuplicateIds = duplicates;
        }

        static Dictionary<string, T> Index<T>(IEnumerable<T> source, Func<T, string> key, string kind, List<string> duplicates, out List<T> sorted)
        {
            var map = new Dictionary<string, T>(StringComparer.Ordinal);
            sorted = new List<T>();
            foreach (var x in source)
            {
                string id = key(x);
                if (map.ContainsKey(id)) { duplicates.Add(kind + ":" + id); continue; }
                map.Add(id, x);
                sorted.Add(x);
            }
            sorted.Sort((a, b) => string.CompareOrdinal(key(a), key(b)));
            return map;
        }

        public bool TryGetSlot(string id, out SlotDefinition v) => slots.TryGetValue(id ?? "", out v);
        public bool TryGetColor(string id, out ColorDefinition v) => colors.TryGetValue(id ?? "", out v);
        public bool TryGetFaceStyle(string id, out FaceStyleDefinition v) => faceStyles.TryGetValue(id ?? "", out v);
        public bool TryGetBodyPreset(string id, out BodyPreset v) => bodyPresets.TryGetValue(id ?? "", out v);
        public bool TryGetItem(string id, out ItemDefinition v) => items.TryGetValue(id ?? "", out v);
        public bool TryGetVariant(string id, out ItemVariant v) => variants.TryGetValue(id ?? "", out v);
        public bool TryGetCharacter(string id, out CharacterDefinition v) => characters.TryGetValue(id ?? "", out v);

        public bool HasBodyType(string bodyType)
        {
            for (int i = 0; i < BodyTypes.Count; i++) if (BodyTypes[i] == bodyType) return true;
            return false;
        }

        static readonly IReadOnlyList<ItemVariant> NoVariants = new ItemVariant[0];

        /// <summary>Variants of an item, sorted by id.</summary>
        public IReadOnlyList<ItemVariant> VariantsOf(string itemId) =>
            variantsByItem.TryGetValue(itemId ?? "", out var list) ? list : NoVariants;

        /// <summary>Slot order index (unknown slots sort last).</summary>
        public int SlotOrder(string slotId) => slots.TryGetValue(slotId ?? "", out var s) ? s.Order : int.MaxValue;
    }

    /// <summary>What the player owns, as the rules see it (no purchase or grant history).</summary>
    public sealed class OwnershipView
    {
        readonly Dictionary<string, HashSet<string>> owned = new Dictionary<string, HashSet<string>>(StringComparer.Ordinal);

        public OwnershipView(IEnumerable<KeyValuePair<string, IEnumerable<string>>> itemsWithVariants)
        {
            foreach (var pair in itemsWithVariants)
            {
                if (!owned.TryGetValue(pair.Key, out var set)) owned[pair.Key] = set = new HashSet<string>(StringComparer.Ordinal);
                foreach (var v in pair.Value) set.Add(v);
            }
        }

        public bool OwnsItem(string itemId) => owned.ContainsKey(itemId ?? "");

        public bool OwnsVariant(string itemId, string variantId) =>
            owned.TryGetValue(itemId ?? "", out var set) && set.Contains(variantId ?? "");
    }
}
