using System;
using System.Collections.Generic;

namespace MMG.Data
{
    public sealed class SlotDefinition
    {
        public string SlotId { get; }
        public IReadOnlyList<ItemKind> AcceptsKinds { get; }
        public StatGroup? StatGroup { get; }
        public bool Required { get; }
        /// <summary>Stacking order by meaning: higher layers cover lower ones (not a draw order).</summary>
        public int Layer { get; }
        public int Order { get; }

        public SlotDefinition(string slotId, IReadOnlyList<ItemKind> acceptsKinds, StatGroup? statGroup, bool required, int layer, int order)
        {
            SlotId = slotId; AcceptsKinds = acceptsKinds; StatGroup = statGroup; Required = required; Layer = layer; Order = order;
        }

        public bool IsAccessory => SlotId.StartsWith("acc.", StringComparison.Ordinal);
    }

    public sealed class ItemDefinition
    {
        public string ItemId { get; }
        public ItemKind Kind { get; }
        public IReadOnlyList<string> Occupies { get; }
        public IReadOnlyList<string> Tags { get; }
        public IReadOnlyList<BodyRegion> Covers { get; }
        /// <summary>Hair only: supported forms, e.g. "default", "under_hat".</summary>
        public IReadOnlyList<string> HairForms { get; }
        public IReadOnlyList<string> FitsBodyTypes { get; }
        public string Rarity { get; }
        public string NameKey { get; }
        public string SetId { get; }
        public string DefaultVariantId { get; }
        public bool IsActive { get; }

        public ItemDefinition(string itemId, ItemKind kind, IReadOnlyList<string> occupies, IReadOnlyList<string> tags,
            IReadOnlyList<BodyRegion> covers, IReadOnlyList<string> hairForms, IReadOnlyList<string> fitsBodyTypes,
            string rarity, string nameKey, string setId, string defaultVariantId, bool isActive)
        {
            ItemId = itemId; Kind = kind; Occupies = occupies; Tags = tags; Covers = covers; HairForms = hairForms;
            FitsBodyTypes = fitsBodyTypes; Rarity = rarity; NameKey = nameKey; SetId = setId; DefaultVariantId = defaultVariantId; IsActive = isActive;
        }

        public bool HasTag(string tag)
        {
            for (int i = 0; i < Tags.Count; i++) if (string.Equals(Tags[i], tag, StringComparison.Ordinal)) return true;
            return false;
        }

        public bool SupportsHairForm(string form)
        {
            for (int i = 0; i < HairForms.Count; i++) if (string.Equals(HairForms[i], form, StringComparison.Ordinal)) return true;
            return false;
        }

        public bool Fits(string bodyType)
        {
            for (int i = 0; i < FitsBodyTypes.Count; i++) if (string.Equals(FitsBodyTypes[i], bodyType, StringComparison.Ordinal)) return true;
            return false;
        }
    }

    public sealed class ColorChannel
    {
        public string Channel { get; }
        public string Rgb { get; }
        public ColorChannel(string channel, string rgb) { Channel = channel; Rgb = rgb; }
    }

    public sealed class ItemVariant
    {
        public string VariantId { get; }
        public string ItemId { get; }
        public IReadOnlyList<ColorChannel> Colors { get; }
        public bool IsActive { get; }

        public ItemVariant(string variantId, string itemId, IReadOnlyList<ColorChannel> colors, bool isActive)
        {
            VariantId = variantId; ItemId = itemId; Colors = colors; IsActive = isActive;
        }
    }

    public sealed class ColorDefinition
    {
        public string ColorId { get; }
        public ColorCategory Category { get; }
        public string Base { get; }
        public string Shade { get; }
        public string Highlight { get; }
        public ColorUnlock Unlock { get; }

        public ColorDefinition(string colorId, ColorCategory category, string baseRgb, string shade, string highlight, ColorUnlock unlock)
        {
            ColorId = colorId; Category = category; Base = baseRgb; Shade = shade; Highlight = highlight; Unlock = unlock;
        }
    }

    public sealed class FaceStyleDefinition
    {
        public string StyleId { get; }
        public FaceFeature Feature { get; }
        public FaceStyleDefinition(string styleId, FaceFeature feature) { StyleId = styleId; Feature = feature; }
    }

    public sealed class BodyPreset
    {
        public string BodyPresetId { get; }
        public string BodyType { get; }
        public string HeadBaseId { get; }
        public IReadOnlyList<BodyRegion> Regions { get; }

        public BodyPreset(string bodyPresetId, string bodyType, string headBaseId, IReadOnlyList<BodyRegion> regions)
        {
            BodyPresetId = bodyPresetId; BodyType = bodyType; HeadBaseId = headBaseId; Regions = regions;
        }
    }

    public sealed class FaceStyle
    {
        public string Eye { get; }
        public string Nose { get; }
        public string Mouth { get; }
        public string Ear { get; }
        public string Brow { get; }

        public FaceStyle(string eye, string nose, string mouth, string ear, string brow)
        {
            Eye = eye; Nose = nose; Mouth = mouth; Ear = ear; Brow = brow;
        }

        public string Get(FaceFeature feature)
        {
            switch (feature)
            {
                case FaceFeature.Eye: return Eye;
                case FaceFeature.Nose: return Nose;
                case FaceFeature.Mouth: return Mouth;
                case FaceFeature.Ear: return Ear;
                default: return Brow;
            }
        }
    }

    /// <summary>Non-item appearance of one character: face styles and colors (policies U4, U6).</summary>
    public sealed class AppearancePreset
    {
        public FaceStyle Face { get; }
        public string SkinColorId { get; }
        public string HairColorId { get; }
        public string EyeColorId { get; }
        public BrowColorMode BrowColorMode { get; }
        /// <summary>Only for <see cref="BrowColorMode.Explicit"/>.</summary>
        public string BrowColorId { get; }
        public int Version { get; }

        public AppearancePreset(FaceStyle face, string skinColorId, string hairColorId, string eyeColorId,
            BrowColorMode browColorMode, string browColorId, int version)
        {
            Face = face; SkinColorId = skinColorId; HairColorId = hairColorId; EyeColorId = eyeColorId;
            BrowColorMode = browColorMode; BrowColorId = browColorId; Version = version;
        }
    }

    public sealed class EquipmentEntry
    {
        public string SlotId { get; }
        public string ItemId { get; }
        public string VariantId { get; }
        public EquipmentEntry(string slotId, string itemId, string variantId) { SlotId = slotId; ItemId = itemId; VariantId = variantId; }
    }

    public sealed class EquipmentState
    {
        public string CharacterId { get; }
        /// <summary>One entry per slot; a one-piece appears in both top and bottom.</summary>
        public IReadOnlyList<EquipmentEntry> Entries { get; }
        /// <summary>Optimistic lock value. The server increments it on save; the rules never change it.</summary>
        public int Version { get; }
        public int RulesVersion { get; }

        public EquipmentState(string characterId, IReadOnlyList<EquipmentEntry> entries, int version, int rulesVersion)
        {
            CharacterId = characterId; Entries = entries; Version = version; RulesVersion = rulesVersion;
        }
    }

    public sealed class CharacterDefinition
    {
        public string CharacterDefId { get; }
        public string NameKey { get; }
        public IReadOnlyList<string> AllowedBodyPresetIds { get; }
        public string DefaultBodyPresetId { get; }
        public AppearancePreset DefaultAppearance { get; }
        public IReadOnlyList<EquipmentEntry> DefaultEquipment { get; }
        public IReadOnlyList<string> AllowedFaceStyleIds { get; }
        public IReadOnlyList<string> AllowedColorIds { get; }

        public CharacterDefinition(string characterDefId, string nameKey, IReadOnlyList<string> allowedBodyPresetIds,
            string defaultBodyPresetId, AppearancePreset defaultAppearance, IReadOnlyList<EquipmentEntry> defaultEquipment,
            IReadOnlyList<string> allowedFaceStyleIds, IReadOnlyList<string> allowedColorIds)
        {
            CharacterDefId = characterDefId; NameKey = nameKey; AllowedBodyPresetIds = allowedBodyPresetIds;
            DefaultBodyPresetId = defaultBodyPresetId; DefaultAppearance = defaultAppearance; DefaultEquipment = defaultEquipment;
            AllowedFaceStyleIds = allowedFaceStyleIds; AllowedColorIds = allowedColorIds;
        }

        public EquipmentEntry DefaultFor(string slotId)
        {
            for (int i = 0; i < DefaultEquipment.Count; i++)
                if (string.Equals(DefaultEquipment[i].SlotId, slotId, StringComparison.Ordinal)) return DefaultEquipment[i];
            return null;
        }

        public bool AllowsBodyPreset(string id) => Contains(AllowedBodyPresetIds, id);
        public bool AllowsFaceStyle(string id) => Contains(AllowedFaceStyleIds, id);
        public bool AllowsColor(string id) => Contains(AllowedColorIds, id);

        static bool Contains(IReadOnlyList<string> list, string id)
        {
            for (int i = 0; i < list.Count; i++) if (string.Equals(list[i], id, StringComparison.Ordinal)) return true;
            return false;
        }
    }

    public sealed class ExclusiveRule
    {
        public string RuleId { get; }
        public string TagA { get; }
        public string TagB { get; }
        public ExclusiveRule(string ruleId, string tagA, string tagB) { RuleId = ruleId; TagA = tagA; TagB = tagB; }
    }

    public sealed class HairFormRequirement
    {
        public string RuleId { get; }
        public string Tag { get; }
        public string HairForm { get; }
        public HairFormRequirement(string ruleId, string tag, string hairForm) { RuleId = ruleId; Tag = tag; HairForm = hairForm; }
    }

    /// <summary>Gameplay rules (source: DB, published with a rules version; policy U10).</summary>
    public sealed class CatalogRules
    {
        public int RulesVersion { get; }
        public int? AccessoryMaxCount { get; }
        public IReadOnlyList<ExclusiveRule> Exclusive { get; }
        public IReadOnlyList<HairFormRequirement> HairFormRequirements { get; }

        public CatalogRules(int rulesVersion, int? accessoryMaxCount, IReadOnlyList<ExclusiveRule> exclusive, IReadOnlyList<HairFormRequirement> hairFormRequirements)
        {
            RulesVersion = rulesVersion; AccessoryMaxCount = accessoryMaxCount; Exclusive = exclusive; HairFormRequirements = hairFormRequirements;
        }
    }
}
