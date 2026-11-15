using System;
using System.Collections.Generic;
using MMG.Data;

namespace MMG.Appearance
{
    public sealed class ResolvedColor
    {
        public string ColorId { get; }
        public string Rgb { get; }
        public ResolvedColor(string colorId, string rgb) { ColorId = colorId; Rgb = rgb; }
    }

    public sealed class ResolvedColors
    {
        public ResolvedColor Skin { get; }
        public ResolvedColor Hair { get; }
        public ResolvedColor Eye { get; }
        public ResolvedColor Brow { get; }
        public bool BrowFollowsHair { get; }

        public ResolvedColors(ResolvedColor skin, ResolvedColor hair, ResolvedColor eye, ResolvedColor brow, bool browFollowsHair)
        {
            Skin = skin; Hair = hair; Eye = eye; Brow = brow; BrowFollowsHair = browFollowsHair;
        }
    }

    public sealed class ResolvedItem
    {
        public IReadOnlyList<string> SlotIds { get; }
        public string ItemId { get; }
        public string VariantId { get; }
        public ItemKind Kind { get; }
        /// <summary>Highest layer of the item's slots (meaning only, renderers choose the draw order).</summary>
        public int Layer { get; }
        public IReadOnlyList<string> Tags { get; }
        public IReadOnlyList<BodyRegion> Covers { get; }
        public IReadOnlyList<ColorChannel> Colors { get; }
        /// <summary>Regions of this item covered by items on a higher layer (e.g. stocking calves under long boots).</summary>
        public IReadOnlyList<BodyRegion> OccludedRegions { get; }

        public ResolvedItem(IReadOnlyList<string> slotIds, string itemId, string variantId, ItemKind kind, int layer,
            IReadOnlyList<string> tags, IReadOnlyList<BodyRegion> covers, IReadOnlyList<ColorChannel> colors, IReadOnlyList<BodyRegion> occludedRegions)
        {
            SlotIds = slotIds; ItemId = itemId; VariantId = variantId; Kind = kind; Layer = layer; Tags = tags; Covers = covers;
            Colors = colors; OccludedRegions = occludedRegions;
        }
    }

    /// <summary>A display intent the renderers must honour, e.g. kind "hairForm", value "under_hat".</summary>
    public sealed class DisplayIntent
    {
        public string Kind { get; }
        public string Value { get; }
        public string CauseItemId { get; }
        public DisplayIntent(string kind, string value, string causeItemId) { Kind = kind; Value = value; CauseItemId = causeItemId; }
    }

    /// <summary>
    /// Renderer-neutral result: which items, variants and colors are shown, which body regions are covered, and display
    /// intents. It holds no ArtMesh ids, sprite names or mesh names; renderer visual adapters turn it into graphics.
    /// </summary>
    public sealed class ResolvedAppearance
    {
        public string CharacterDefId { get; }
        public string BodyPresetId { get; }
        public string BodyType { get; }
        public string HeadBaseId { get; }
        public FaceStyle Face { get; }
        public ResolvedColors Colors { get; }
        public IReadOnlyList<ResolvedItem> Items { get; }
        public IReadOnlyList<BodyRegion> CoveredRegions { get; }
        public IReadOnlyList<DisplayIntent> Intents { get; }
        public IReadOnlyList<string> Warnings { get; }

        public ResolvedAppearance(string characterDefId, string bodyPresetId, string bodyType, string headBaseId, FaceStyle face,
            ResolvedColors colors, IReadOnlyList<ResolvedItem> items, IReadOnlyList<BodyRegion> coveredRegions,
            IReadOnlyList<DisplayIntent> intents, IReadOnlyList<string> warnings)
        {
            CharacterDefId = characterDefId; BodyPresetId = bodyPresetId; BodyType = bodyType; HeadBaseId = headBaseId; Face = face;
            Colors = colors; Items = items; CoveredRegions = coveredRegions; Intents = intents; Warnings = warnings;
        }
    }

    public static class IntentKinds
    {
        public const string HairForm = "hairForm";
    }

    /// <summary>
    /// Resolves what to show (05 document 7-3). It never fails on bad input: unknown or invalid values fall back to the
    /// character defaults and are reported in <see cref="ResolvedAppearance.Warnings"/>. Same input → same output.
    /// </summary>
    public static class AppearanceResolver
    {
        public static ResolvedAppearance Resolve(Catalog catalog, string characterDefId, string bodyPresetId, AppearancePreset appearance, EquipmentState state)
        {
            if (!catalog.TryGetCharacter(characterDefId, out var character))
                throw new ArgumentException("unknown character " + characterDefId, nameof(characterDefId));
            var warnings = new List<string>();

            if (!character.AllowsBodyPreset(bodyPresetId) || !catalog.TryGetBodyPreset(bodyPresetId, out var body))
            {
                warnings.Add("bodyPresetFallback");
                catalog.TryGetBodyPreset(character.DefaultBodyPresetId, out body);
            }

            var face = ResolveFace(catalog, character, appearance, warnings);
            var colors = ResolveColors(catalog, character, appearance, warnings);
            var items = ResolveItems(catalog, character, body, state, warnings);

            var covered = new SortedSet<BodyRegion>();
            foreach (var it in items) covered.UnionWith(it.Covers);

            var intents = new List<DisplayIntent>();
            ResolvedItem hair = null;
            foreach (var it in items) if (it.Kind == ItemKind.Hair) hair = it;
            catalog.TryGetItem(hair?.ItemId, out var hairDef);
            foreach (var req in catalog.Rules.HairFormRequirements)
                foreach (var it in items)
                {
                    if (!Contains(it.Tags, req.Tag)) continue;
                    if (hairDef != null && hairDef.SupportsHairForm(req.HairForm))
                    {
                        if (!intents.Exists(x => x.Kind == IntentKinds.HairForm && x.Value == req.HairForm))
                            intents.Add(new DisplayIntent(IntentKinds.HairForm, req.HairForm, it.ItemId));
                    }
                    else warnings.Add("hairFormUnsupported:" + req.HairForm);
                }
            intents.Sort((a, b) =>
            {
                int c = string.CompareOrdinal(a.Kind, b.Kind);
                return c != 0 ? c : string.CompareOrdinal(a.Value, b.Value);
            });
            warnings.Sort(StringComparer.Ordinal);

            return new ResolvedAppearance(character.CharacterDefId, body.BodyPresetId, body.BodyType, body.HeadBaseId, face, colors, items,
                new List<BodyRegion>(covered), intents, warnings);
        }

        static FaceStyle ResolveFace(Catalog catalog, CharacterDefinition character, AppearancePreset appearance, List<string> warnings)
        {
            var ids = new string[5];
            foreach (FaceFeature f in Enum.GetValues(typeof(FaceFeature)))
            {
                string id = appearance?.Face?.Get(f);
                bool ok = id != null && catalog.TryGetFaceStyle(id, out var style) && style.Feature == f && character.AllowsFaceStyle(id);
                if (!ok)
                {
                    warnings.Add("faceStyleFallback:" + EnumNames.Of(f));
                    id = character.DefaultAppearance.Face.Get(f);
                }
                ids[(int)f] = id;
            }
            return new FaceStyle(ids[(int)FaceFeature.Eye], ids[(int)FaceFeature.Nose], ids[(int)FaceFeature.Mouth], ids[(int)FaceFeature.Ear], ids[(int)FaceFeature.Brow]);
        }

        static ResolvedColors ResolveColors(Catalog catalog, CharacterDefinition character, AppearancePreset appearance, List<string> warnings)
        {
            var d = character.DefaultAppearance;
            var skin = PickColor(catalog, character, appearance?.SkinColorId, d.SkinColorId, ColorCategory.Skin, "skin", warnings);
            var hair = PickColor(catalog, character, appearance?.HairColorId, d.HairColorId, ColorCategory.Hair, "hair", warnings);
            var eye = PickColor(catalog, character, appearance?.EyeColorId, d.EyeColorId, ColorCategory.Eye, "eye", warnings);
            if (appearance != null && appearance.BrowColorMode == BrowColorMode.Explicit)
            {
                var brow = PickColor(catalog, character, appearance.BrowColorId, hair.ColorId, ColorCategory.Hair, "brow", warnings);
                return new ResolvedColors(skin, hair, eye, brow, false);
            }
            return new ResolvedColors(skin, hair, eye, hair, true);
        }

        static ResolvedColor PickColor(Catalog catalog, CharacterDefinition character, string id, string fallbackId, ColorCategory category, string name, List<string> warnings)
        {
            if (id != null && catalog.TryGetColor(id, out var c) && c.Category == category && character.AllowsColor(id))
                return new ResolvedColor(c.ColorId, c.Base);
            warnings.Add("colorFallback:" + name);
            catalog.TryGetColor(fallbackId, out var f);
            return new ResolvedColor(fallbackId, f?.Base);
        }

        static List<ResolvedItem> ResolveItems(Catalog catalog, CharacterDefinition character, BodyPreset body, EquipmentState state, List<string> warnings)
        {
            // slot -> entry, keeping only entries the catalog can show
            var bySlot = new Dictionary<string, EquipmentEntry>(StringComparer.Ordinal);
            var entries = new List<EquipmentEntry>(state?.Entries ?? new EquipmentEntry[0]);
            entries.Sort((a, b) =>
            {
                int c = catalog.SlotOrder(a.SlotId).CompareTo(catalog.SlotOrder(b.SlotId));
                if (c != 0) return c;
                c = string.CompareOrdinal(a.SlotId, b.SlotId);
                return c != 0 ? c : string.CompareOrdinal(a.ItemId, b.ItemId);
            });
            foreach (var e in entries)
            {
                if (bySlot.ContainsKey(e.SlotId) || !catalog.TryGetSlot(e.SlotId, out _) || !catalog.TryGetItem(e.ItemId, out var item) ||
                    !Contains(item.Occupies, e.SlotId) || !catalog.TryGetVariant(e.VariantId, out var v) || v.ItemId != e.ItemId)
                {
                    warnings.Add("entryIgnored:" + e.SlotId);
                    continue;
                }
                bySlot.Add(e.SlotId, e);
            }

            foreach (var slot in catalog.Slots)
            {
                if (!slot.Required || bySlot.ContainsKey(slot.SlotId)) continue;
                var d = character.DefaultFor(slot.SlotId);
                if (d == null || !catalog.TryGetItem(d.ItemId, out var item)) { warnings.Add("requiredSlotEmpty:" + slot.SlotId); continue; }
                bool free = true;
                foreach (var s in item.Occupies) if (bySlot.ContainsKey(s)) free = false;
                if (!free) { warnings.Add("requiredSlotEmpty:" + slot.SlotId); continue; }
                foreach (var s in item.Occupies) bySlot[s] = new EquipmentEntry(s, d.ItemId, d.VariantId);
                warnings.Add("requiredSlotDefaulted:" + slot.SlotId);
            }

            var result = new List<ResolvedItem>();
            var done = new HashSet<string>(StringComparer.Ordinal);
            var raw = new List<(ItemDefinition item, EquipmentEntry entry, List<string> slots, int layer)>();
            foreach (var slot in catalog.Slots)
            {
                if (!bySlot.TryGetValue(slot.SlotId, out var e) || !done.Add(e.ItemId)) continue;
                catalog.TryGetItem(e.ItemId, out var item);
                var slots = new List<string>();
                int layer = int.MinValue;
                foreach (var s in catalog.Slots)
                    if (bySlot.TryGetValue(s.SlotId, out var other) && other.ItemId == e.ItemId)
                    {
                        slots.Add(s.SlotId);
                        layer = Math.Max(layer, s.Layer);
                    }
                if (slots.Count != item.Occupies.Count) warnings.Add("onePieceIncomplete:" + e.ItemId);
                if (body != null && !item.Fits(body.BodyType)) warnings.Add("bodyTypeMismatch:" + e.ItemId);
                raw.Add((item, e, slots, layer));
            }

            foreach (var r in raw)
            {
                var occluded = new SortedSet<BodyRegion>();
                foreach (var other in raw)
                {
                    if (other.layer <= r.layer) continue;
                    foreach (var region in other.item.Covers)
                        if (Contains(r.item.Covers, region)) occluded.Add(region);
                }
                catalog.TryGetVariant(r.entry.VariantId, out var variant);
                var tags = new List<string>(r.item.Tags);
                tags.Sort(StringComparer.Ordinal);
                var covers = new List<BodyRegion>(r.item.Covers);
                covers.Sort();
                result.Add(new ResolvedItem(r.slots, r.item.ItemId, r.entry.VariantId, r.item.Kind, r.layer, tags, covers,
                    variant?.Colors ?? new ColorChannel[0], new List<BodyRegion>(occluded)));
            }
            return result;
        }

        static bool Contains<T>(IReadOnlyList<T> list, T value)
        {
            for (int i = 0; i < list.Count; i++) if (EqualityComparer<T>.Default.Equals(list[i], value)) return true;
            return false;
        }
    }
}
