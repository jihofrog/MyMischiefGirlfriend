using System;
using System.Collections.Generic;
using System.Text.RegularExpressions;

namespace MMG.Data.Validation
{
    public sealed class ValidationIssue
    {
        public string Code { get; }
        public string Path { get; }
        public string Message { get; }
        public ValidationIssue(string code, string path, string message) { Code = code; Path = path; Message = message; }
        public override string ToString() => Code + " @ " + Path + ": " + Message;
    }

    /// <summary>
    /// Consistency and reference checks of a catalog. Gameplay-rule checks of default equipment (exclusive tags,
    /// hair forms) live in MMG.Appearance because they need the rule engine.
    /// </summary>
    public static class CatalogValidator
    {
        /// <summary>Words that must not appear as a token of a common item or face style id (policy U7).</summary>
        public static readonly IReadOnlyList<string> ColorWords = new[]
        {
            "black", "white", "brown", "cream", "navy", "pink", "red", "blue", "green", "yellow", "purple",
            "gray", "grey", "beige", "blonde", "silver", "gold", "orange", "ivory", "khaki"
        };

        static readonly string[] VariantChannels = { "accent", "primary", "secondary" };
        static readonly string[] StandardSlots = { "hair", "top", "bottom", "legwear", "shoes" };
        static readonly Regex Rgb = new Regex("^#[0-9A-F]{6}$");
        static readonly Regex SlotIdPattern = new Regex("^[a-z]+(\\.[a-z]+)?$");
        static readonly Regex TagPattern = new Regex("^[a-z0-9_]+$");
        static readonly Regex NameTail = new Regex("^[a-z0-9]+(_[a-z0-9]+)*_[0-9]{2}$");
        static readonly Regex VariantTail = new Regex("^[a-z0-9_]+$");

        public static List<ValidationIssue> Validate(Catalog c)
        {
            var issues = new List<ValidationIssue>();
            void Add(string code, string path, string msg) => issues.Add(new ValidationIssue(code, path, msg));

            foreach (var d in c.DuplicateIds) Add("DUPLICATE_ID", d, "id appears more than once");
            if (c.BodyTypes.Count == 0) Add("BODYTYPES_EMPTY", "bodyTypes", "at least one body type is needed");

            CheckRules(c, Add);
            CheckSlots(c, Add);
            foreach (var color in c.Colors) CheckColor(color, Add);
            foreach (var face in c.FaceStyles) CheckFaceStyle(face, Add);
            foreach (var body in c.BodyPresets) CheckBodyPreset(c, body, Add);
            foreach (var item in c.Items) CheckItem(c, item, Add);
            foreach (var variant in c.Variants) CheckVariant(c, variant, Add);
            foreach (var character in c.Characters) CheckCharacter(c, character, Add);

            issues.Sort((a, b) =>
            {
                int p = string.CompareOrdinal(a.Path, b.Path);
                return p != 0 ? p : string.CompareOrdinal(a.Code, b.Code);
            });
            return issues;
        }

        static void CheckRules(Catalog c, Action<string, string, string> add)
        {
            var r = c.Rules;
            if (r.AccessoryMaxCount.HasValue && r.AccessoryMaxCount.Value < 1)
                add("RULE_INVALID", "rules.accessoryMaxCount", "must be null or at least 1");
            var ids = new HashSet<string>(StringComparer.Ordinal);
            foreach (var e in r.Exclusive)
            {
                if (!ids.Add(e.RuleId)) add("DUPLICATE_ID", "rule:" + e.RuleId, "rule id appears more than once");
                if (!TagPattern.IsMatch(e.TagA) || !TagPattern.IsMatch(e.TagB) || e.TagA == e.TagB)
                    add("RULE_INVALID", "rules.exclusive[" + e.RuleId + "]", "two different tags are needed");
            }
            foreach (var h in r.HairFormRequirements)
            {
                if (!ids.Add(h.RuleId)) add("DUPLICATE_ID", "rule:" + h.RuleId, "rule id appears more than once");
                if (!TagPattern.IsMatch(h.Tag) || !TagPattern.IsMatch(h.HairForm) || h.HairForm == "default")
                    add("RULE_INVALID", "rules.hairFormRequirements[" + h.RuleId + "]", "tag and a non-default hair form are needed");
            }
        }

        static void CheckSlots(Catalog c, Action<string, string, string> add)
        {
            var orders = new HashSet<int>();
            foreach (var s in c.Slots)
            {
                string p = "slots[" + s.SlotId + "]";
                if (!SlotIdPattern.IsMatch(s.SlotId)) add("SLOT_ID_FORMAT", p, "slot id format");
                if (!orders.Add(s.Order)) add("SLOT_ORDER_DUPLICATE", p + ".order", "slot orders must be unique");
                if (s.AcceptsKinds.Count == 0) add("SLOT_KINDS_EMPTY", p + ".acceptsKinds", "no item kind accepted");
                if (s.IsAccessory)
                {
                    if (s.AcceptsKinds.Count != 1 || s.AcceptsKinds[0] != ItemKind.Accessory)
                        add("SLOT_KIND_MISMATCH", p + ".acceptsKinds", "accessory slots accept only accessories");
                    if (s.StatGroup != StatGroup.Accessory) add("POLICY_STAT_GROUP", p + ".statGroup", "accessory slots use the Accessory stat group");
                    if (s.Required) add("POLICY_U12", p + ".required", "accessory slots can be empty");
                }
                if (s.StatGroup == StatGroup.Footwear && s.SlotId != "shoes")
                    add("POLICY_U1", p + ".statGroup", "Footwear comes from shoes only");
            }
            foreach (var id in StandardSlots)
                if (!c.TryGetSlot(id, out _)) add("SLOT_MISSING", "slots[" + id + "]", "standard slot missing");
            if (c.TryGetSlot("legwear", out var legwear))
            {
                if (legwear.StatGroup.HasValue) add("POLICY_U1", "slots[legwear].statGroup", "legwear has no stat group");
                if (legwear.Required) add("POLICY_U12", "slots[legwear].required", "legwear can be empty");
            }
            if (c.TryGetSlot("shoes", out var shoes) && shoes.StatGroup != StatGroup.Footwear)
                add("POLICY_U1", "slots[shoes].statGroup", "shoes carry the Footwear stat group");
            foreach (var id in new[] { "hair", "top", "bottom", "shoes" })
                if (c.TryGetSlot(id, out var s) && !s.Required) add("POLICY_U12", "slots[" + id + "].required", "slot must be required");
        }

        static void CheckColor(ColorDefinition color, Action<string, string, string> add)
        {
            string p = "colors[" + color.ColorId + "]";
            string prefix = color.Category == ColorCategory.Skin ? "skin_" : color.Category == ColorCategory.Hair ? "haircolor_" : "eyecolor_";
            if (!color.ColorId.StartsWith(prefix, StringComparison.Ordinal) || !NameTail.IsMatch(color.ColorId.Substring(Math.Min(prefix.Length, color.ColorId.Length))))
                add("COLOR_ID_FORMAT", p, "expected " + prefix + "<name>_<nn>");
            foreach (var v in new[] { color.Base, color.Shade, color.Highlight })
                if (!Rgb.IsMatch(v ?? "")) add("RGB_FORMAT", p, "colors are #RRGGBB (upper case)");
        }

        static void CheckFaceStyle(FaceStyleDefinition f, Action<string, string, string> add)
        {
            string p = "faceStyles[" + f.StyleId + "]";
            string prefix = EnumNames.Of(f.Feature) + "_";
            if (!f.StyleId.StartsWith(prefix, StringComparison.Ordinal) || !NameTail.IsMatch(f.StyleId.Substring(Math.Min(prefix.Length, f.StyleId.Length))))
                add("FACE_ID_FORMAT", p, "expected " + prefix + "<name>_<nn>");
            CheckColorWords(f.StyleId, p, add);
        }

        static void CheckBodyPreset(Catalog c, BodyPreset b, Action<string, string, string> add)
        {
            string p = "bodyPresets[" + b.BodyPresetId + "]";
            if (!c.HasBodyType(b.BodyType)) add("REF_UNKNOWN", p + ".bodyType", "unknown body type " + b.BodyType);
            if (HasDuplicates(b.Regions)) add("LIST_DUPLICATE", p + ".regions", "regions must be unique");
        }

        static void CheckItem(Catalog c, ItemDefinition item, Action<string, string, string> add)
        {
            string p = "items[" + item.ItemId + "]";
            if (item.Occupies.Count == 0) add("OCCUPIES_COUNT", p + ".occupies", "an item occupies at least one slot");
            if (HasDuplicates(item.Occupies)) add("LIST_DUPLICATE", p + ".occupies", "slots must be unique");
            foreach (var slotId in item.Occupies)
            {
                if (!c.TryGetSlot(slotId, out var slot)) { add("REF_UNKNOWN", p + ".occupies", "unknown slot " + slotId); continue; }
                if (!Contains(slot.AcceptsKinds, item.Kind)) add("SLOT_KIND_MISMATCH", p + ".occupies", slotId + " does not accept " + EnumNames.Of(item.Kind));
            }
            if (item.Kind == ItemKind.OnePiece)
            {
                if (item.Occupies.Count != 2 || !ContainsString(item.Occupies, "top") || !ContainsString(item.Occupies, "bottom"))
                    add("ONEPIECE_OCCUPIES", p + ".occupies", "a one-piece occupies top and bottom");
            }
            else if (item.Occupies.Count != 1) add("OCCUPIES_COUNT", p + ".occupies", "only one-pieces occupy more than one slot");

            string prefix = ItemPrefix(item);
            if (prefix == null || !item.ItemId.StartsWith(prefix, StringComparison.Ordinal) || !NameTail.IsMatch(item.ItemId.Substring(Math.Min(prefix.Length, item.ItemId.Length))))
                add("ITEM_ID_FORMAT", p, "expected " + (prefix ?? "<prefix>") + "<shape>[_<detail>]_<nn>");
            CheckColorWords(item.ItemId, p, add);

            foreach (var t in item.Tags) if (!TagPattern.IsMatch(t)) add("TAG_FORMAT", p + ".tags", "tag format " + t);
            if (HasDuplicates(item.Tags)) add("LIST_DUPLICATE", p + ".tags", "tags must be unique");
            if (HasDuplicates(item.Covers)) add("LIST_DUPLICATE", p + ".covers", "regions must be unique");
            if (item.Kind == ItemKind.Hair)
            {
                if (!item.SupportsHairForm("default")) add("HAIRFORMS_INVALID", p + ".hairForms", "hair supports the default form");
                if (HasDuplicates(item.HairForms)) add("LIST_DUPLICATE", p + ".hairForms", "forms must be unique");
            }
            else if (item.HairForms.Count > 0) add("HAIRFORMS_INVALID", p + ".hairForms", "only hair has forms");

            if (item.FitsBodyTypes.Count == 0) add("FITS_EMPTY", p + ".fitsBodyTypes", "at least one body type");
            foreach (var bt in item.FitsBodyTypes) if (!c.HasBodyType(bt)) add("REF_UNKNOWN", p + ".fitsBodyTypes", "unknown body type " + bt);

            if (c.VariantsOf(item.ItemId).Count == 0) add("ITEM_NO_VARIANT", p, "an item has at least one variant");
            if (!c.TryGetVariant(item.DefaultVariantId, out var dv) || dv.ItemId != item.ItemId)
                add("VARIANT_DEFAULT_INVALID", p + ".defaultVariantId", "default variant must be a variant of this item");
        }

        static string ItemPrefix(ItemDefinition item)
        {
            switch (item.Kind)
            {
                case ItemKind.Hair: return "hair_";
                case ItemKind.Top: return "top_";
                case ItemKind.Bottom: return "bottom_";
                case ItemKind.OnePiece: return "onepiece_";
                case ItemKind.Legwear: return "legwear_";
                case ItemKind.Shoes: return "shoes_";
                default:
                    if (item.Occupies.Count != 1 || !item.Occupies[0].StartsWith("acc.", StringComparison.Ordinal)) return null;
                    return "acc_" + item.Occupies[0].Substring(4) + "_";
            }
        }

        static void CheckVariant(Catalog c, ItemVariant v, Action<string, string, string> add)
        {
            string p = "variants[" + v.VariantId + "]";
            if (!c.TryGetItem(v.ItemId, out _)) add("REF_UNKNOWN", p + ".itemId", "unknown item " + v.ItemId);
            string prefix = v.ItemId + ".";
            if (!v.VariantId.StartsWith(prefix, StringComparison.Ordinal) || !VariantTail.IsMatch(v.VariantId.Substring(Math.Min(prefix.Length, v.VariantId.Length))))
                add("VARIANT_ID_FORMAT", p, "expected <itemId>.<name>");
            var channels = new List<string>();
            foreach (var ch in v.Colors)
            {
                channels.Add(ch.Channel);
                if (Array.IndexOf(VariantChannels, ch.Channel) < 0) add("COLOR_CHANNEL_UNKNOWN", p + ".colors", "channel " + ch.Channel);
                if (!Rgb.IsMatch(ch.Rgb ?? "")) add("RGB_FORMAT", p + ".colors", "colors are #RRGGBB (upper case)");
            }
            if (HasDuplicates(channels)) add("LIST_DUPLICATE", p + ".colors", "channels must be unique");
        }

        static void CheckCharacter(Catalog c, CharacterDefinition ch, Action<string, string, string> add)
        {
            string p = "characters[" + ch.CharacterDefId + "]";
            foreach (var id in ch.AllowedBodyPresetIds)
                if (!c.TryGetBodyPreset(id, out _)) add("REF_UNKNOWN", p + ".allowedBodyPresetIds", "unknown body preset " + id);
            if (!ch.AllowsBodyPreset(ch.DefaultBodyPresetId)) add("DEFAULT_NOT_ALLOWED", p + ".defaultBodyPresetId", "default body preset is not in the allowed list");
            foreach (var id in ch.AllowedFaceStyleIds)
                if (!c.TryGetFaceStyle(id, out _)) add("REF_UNKNOWN", p + ".allowedFaceStyleIds", "unknown face style " + id);
            foreach (var id in ch.AllowedColorIds)
                if (!c.TryGetColor(id, out _)) add("REF_UNKNOWN", p + ".allowedColorIds", "unknown color " + id);

            var a = ch.DefaultAppearance;
            foreach (FaceFeature feature in Enum.GetValues(typeof(FaceFeature)))
            {
                string id = a.Face.Get(feature);
                string fp = p + ".defaultAppearance.face." + EnumNames.Of(feature);
                if (!c.TryGetFaceStyle(id, out var style)) { add("REF_UNKNOWN", fp, "unknown face style " + id); continue; }
                if (style.Feature != feature) add("FACE_FEATURE_MISMATCH", fp, id + " is not a " + EnumNames.Of(feature) + " style");
                if (!ch.AllowsFaceStyle(id)) add("DEFAULT_NOT_ALLOWED", fp, id + " is not in allowedFaceStyleIds");
            }
            CheckAppearanceColor(c, ch, a.SkinColorId, ColorCategory.Skin, p + ".defaultAppearance.skinColorId", add);
            CheckAppearanceColor(c, ch, a.HairColorId, ColorCategory.Hair, p + ".defaultAppearance.hairColorId", add);
            CheckAppearanceColor(c, ch, a.EyeColorId, ColorCategory.Eye, p + ".defaultAppearance.eyeColorId", add);
            if (a.BrowColorMode == BrowColorMode.FollowHair && a.BrowColorId != null)
                add("BROW_COLOR_INVALID", p + ".defaultAppearance.browColorId", "followHair uses no brow color id");
            if (a.BrowColorMode == BrowColorMode.Explicit)
                CheckAppearanceColor(c, ch, a.BrowColorId, ColorCategory.Hair, p + ".defaultAppearance.browColorId", add);

            CheckDefaultEquipment(c, ch, p + ".defaultEquipment", add);
        }

        static void CheckAppearanceColor(Catalog c, CharacterDefinition ch, string id, ColorCategory category, string path, Action<string, string, string> add)
        {
            if (!c.TryGetColor(id, out var color)) { add("REF_UNKNOWN", path, "unknown color " + id); return; }
            if (color.Category != category) add("COLOR_CATEGORY_MISMATCH", path, id + " is not a " + EnumNames.Of(category) + " color");
            if (!ch.AllowsColor(id)) add("DEFAULT_NOT_ALLOWED", path, id + " is not in allowedColorIds");
        }

        static void CheckDefaultEquipment(Catalog c, CharacterDefinition ch, string p, Action<string, string, string> add)
        {
            c.TryGetBodyPreset(ch.DefaultBodyPresetId, out var body);
            var bySlot = new Dictionary<string, EquipmentEntry>(StringComparer.Ordinal);
            foreach (var e in ch.DefaultEquipment)
            {
                string ep = p + "[" + e.SlotId + "]";
                if (bySlot.ContainsKey(e.SlotId)) { add("LIST_DUPLICATE", ep, "slot listed twice"); continue; }
                bySlot.Add(e.SlotId, e);
                if (!c.TryGetSlot(e.SlotId, out _)) add("REF_UNKNOWN", ep, "unknown slot " + e.SlotId);
                if (!c.TryGetItem(e.ItemId, out var item)) { add("REF_UNKNOWN", ep, "unknown item " + e.ItemId); continue; }
                if (!item.IsActive) add("DEFAULT_INACTIVE", ep, e.ItemId + " is inactive");
                if (!ContainsString(item.Occupies, e.SlotId)) add("SLOT_KIND_MISMATCH", ep, e.ItemId + " does not occupy " + e.SlotId);
                if (!c.TryGetVariant(e.VariantId, out var v) || v.ItemId != e.ItemId) add("VARIANT_MISMATCH", ep, e.VariantId + " is not a variant of " + e.ItemId);
                else if (!v.IsActive) add("DEFAULT_INACTIVE", ep, e.VariantId + " is inactive");
                if (body != null && !item.Fits(body.BodyType)) add("BODYTYPE_MISMATCH", ep, e.ItemId + " does not fit " + body.BodyType);
            }
            foreach (var e in ch.DefaultEquipment)
            {
                if (!c.TryGetItem(e.ItemId, out var item)) continue;
                foreach (var other in item.Occupies)
                    if (!bySlot.TryGetValue(other, out var oe) || oe.ItemId != e.ItemId || oe.VariantId != e.VariantId)
                        add("ONEPIECE_INCOMPLETE", p + "[" + other + "]", e.ItemId + " must be listed in every slot it occupies");
            }
            foreach (var slot in c.Slots)
                if (slot.Required && !bySlot.ContainsKey(slot.SlotId)) add("DEFAULT_REQUIRED_MISSING", p + "[" + slot.SlotId + "]", "required slot needs a default item");
        }

        static void CheckColorWords(string id, string path, Action<string, string, string> add)
        {
            foreach (var token in id.Split('_'))
                foreach (var word in ColorWords)
                    if (token == word) add("ID_HAS_COLOR_WORD", path, "common ids do not carry color names (" + word + "), use a variant");
        }

        static bool HasDuplicates<T>(IReadOnlyList<T> list)
        {
            var set = new HashSet<T>();
            foreach (var x in list) if (!set.Add(x)) return true;
            return false;
        }

        static bool Contains(IReadOnlyList<ItemKind> list, ItemKind k)
        {
            for (int i = 0; i < list.Count; i++) if (list[i] == k) return true;
            return false;
        }

        static bool ContainsString(IReadOnlyList<string> list, string s)
        {
            for (int i = 0; i < list.Count; i++) if (string.Equals(list[i], s, StringComparison.Ordinal)) return true;
            return false;
        }
    }
}
