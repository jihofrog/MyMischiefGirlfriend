using System.Collections.Generic;

namespace MMG.Data.Json
{
    /// <summary>
    /// Reads the shared JSON formats (Shared/schemas/*.schema.json). Readers are strict: missing fields, wrong types,
    /// unknown fields and unknown enum names throw <see cref="JsonFormatException"/>. Reference checks are done by
    /// <see cref="Validation.CatalogValidator"/>, not here.
    /// </summary>
    public static class CatalogJson
    {
        public const int SupportedSchemaVersion = 1;

        public static Catalog ReadCatalog(string json)
        {
            var r = new JsonObjectReader(JsonParser.Parse(json), "$");
            int schemaVersion = r.Int("schemaVersion");
            if (schemaVersion != SupportedSchemaVersion)
                throw new JsonFormatException("$.schemaVersion", "unsupported schema version " + schemaVersion);
            int catalogVersion = r.Int("catalogVersion");
            var rules = ReadRules(r.Object("rules"));
            var bodyTypes = r.StringList("bodyTypes");
            var slots = new List<SlotDefinition>();
            foreach (var o in r.Objects("slots")) slots.Add(ReadSlot(o));
            var colors = new List<ColorDefinition>();
            foreach (var o in r.Objects("colors")) colors.Add(ReadColor(o));
            var faces = new List<FaceStyleDefinition>();
            foreach (var o in r.Objects("faceStyles")) faces.Add(ReadFaceStyle(o));
            var bodies = new List<BodyPreset>();
            foreach (var o in r.Objects("bodyPresets")) bodies.Add(ReadBodyPreset(o));
            var items = new List<ItemDefinition>();
            foreach (var o in r.Objects("items")) items.Add(ReadItem(o));
            var variants = new List<ItemVariant>();
            foreach (var o in r.Objects("variants")) variants.Add(ReadVariant(o));
            var characters = new List<CharacterDefinition>();
            foreach (var o in r.Objects("characters")) characters.Add(ReadCharacter(o));
            r.StringOrNull("$comment");
            r.EnsureNoUnknownKeys();
            return new Catalog(schemaVersion, catalogVersion, rules, bodyTypes, slots, colors, faces, bodies, items, variants, characters);
        }

        static CatalogRules ReadRules(JsonObjectReader r)
        {
            int rulesVersion = r.Int("rulesVersion");
            int? max = r.IntOrNull("accessoryMaxCount");
            var exclusive = new List<ExclusiveRule>();
            foreach (var o in r.Objects("exclusive"))
            {
                exclusive.Add(new ExclusiveRule(o.String("ruleId"), o.String("tagA"), o.String("tagB")));
                o.EnsureNoUnknownKeys();
            }
            var hairForms = new List<HairFormRequirement>();
            foreach (var o in r.Objects("hairFormRequirements"))
            {
                hairForms.Add(new HairFormRequirement(o.String("ruleId"), o.String("tag"), o.String("hairForm")));
                o.EnsureNoUnknownKeys();
            }
            exclusive.Sort((a, b) => string.CompareOrdinal(a.RuleId, b.RuleId));
            hairForms.Sort((a, b) => string.CompareOrdinal(a.RuleId, b.RuleId));
            r.EnsureNoUnknownKeys();
            return new CatalogRules(rulesVersion, max, exclusive, hairForms);
        }

        static SlotDefinition ReadSlot(JsonObjectReader r)
        {
            var kinds = new List<ItemKind>();
            foreach (var k in r.StringList("acceptsKinds")) kinds.Add(ParseKind(k, r.Path + ".acceptsKinds"));
            string stat = r.StringOrNull("statGroup");
            StatGroup? statGroup = null;
            if (stat != null)
            {
                if (!EnumNames.TryParse(stat, out StatGroup sg)) throw new JsonFormatException(r.Path + ".statGroup", "unknown stat group " + stat);
                statGroup = sg;
            }
            var slot = new SlotDefinition(r.String("slotId"), kinds, statGroup, r.Bool("required"), r.Int("layer"), r.Int("order"));
            r.EnsureNoUnknownKeys();
            return slot;
        }

        static ColorDefinition ReadColor(JsonObjectReader r)
        {
            if (!EnumNames.TryParse(r.String("category"), out ColorCategory category)) throw new JsonFormatException(r.Path + ".category", "unknown color category");
            if (!EnumNames.TryParse(r.String("unlock"), out ColorUnlock unlock)) throw new JsonFormatException(r.Path + ".unlock", "unknown unlock kind");
            var c = new ColorDefinition(r.String("colorId"), category, r.String("base"), r.String("shade"), r.String("highlight"), unlock);
            r.EnsureNoUnknownKeys();
            return c;
        }

        static FaceStyleDefinition ReadFaceStyle(JsonObjectReader r)
        {
            if (!EnumNames.TryParse(r.String("feature"), out FaceFeature feature)) throw new JsonFormatException(r.Path + ".feature", "unknown face feature");
            var f = new FaceStyleDefinition(r.String("styleId"), feature);
            r.EnsureNoUnknownKeys();
            return f;
        }

        static BodyPreset ReadBodyPreset(JsonObjectReader r)
        {
            var b = new BodyPreset(r.String("bodyPresetId"), r.String("bodyType"), r.String("headBaseId"), ReadRegions(r, "regions"));
            r.EnsureNoUnknownKeys();
            return b;
        }

        static ItemDefinition ReadItem(JsonObjectReader r)
        {
            var it = new ItemDefinition(
                r.String("itemId"),
                ParseKind(r.String("kind"), r.Path + ".kind"),
                r.StringList("occupies"),
                r.StringList("tags"),
                ReadRegions(r, "covers"),
                r.StringList("hairForms"),
                r.StringList("fitsBodyTypes"),
                r.String("rarity"),
                r.String("nameKey"),
                r.StringOrNull("setId"),
                r.String("defaultVariantId"),
                r.Bool("isActive"));
            r.EnsureNoUnknownKeys();
            return it;
        }

        static ItemVariant ReadVariant(JsonObjectReader r)
        {
            var colors = new List<ColorChannel>();
            foreach (var o in r.Objects("colors"))
            {
                colors.Add(new ColorChannel(o.String("channel"), o.String("rgb")));
                o.EnsureNoUnknownKeys();
            }
            colors.Sort((a, b) => string.CompareOrdinal(a.Channel, b.Channel));
            var v = new ItemVariant(r.String("variantId"), r.String("itemId"), colors, r.Bool("isActive"));
            r.EnsureNoUnknownKeys();
            return v;
        }

        static CharacterDefinition ReadCharacter(JsonObjectReader r)
        {
            var c = new CharacterDefinition(
                r.String("characterDefId"),
                r.String("nameKey"),
                r.StringList("allowedBodyPresetIds"),
                r.String("defaultBodyPresetId"),
                ReadAppearance(r.Object("defaultAppearance")),
                ReadEntries(r, "defaultEquipment"),
                r.StringList("allowedFaceStyleIds"),
                r.StringList("allowedColorIds"));
            r.EnsureNoUnknownKeys();
            return c;
        }

        public static AppearancePreset ReadAppearance(JsonObjectReader r)
        {
            var f = r.Object("face");
            var face = new FaceStyle(f.String("eye"), f.String("nose"), f.String("mouth"), f.String("ear"), f.String("brow"));
            f.EnsureNoUnknownKeys();
            if (!EnumNames.TryParse(r.String("browColorMode"), out BrowColorMode mode)) throw new JsonFormatException(r.Path + ".browColorMode", "unknown brow color mode");
            var a = new AppearancePreset(face, r.String("skinColorId"), r.String("hairColorId"), r.String("eyeColorId"), mode,
                r.StringOrNull("browColorId"), r.Int("version"));
            r.EnsureNoUnknownKeys();
            return a;
        }

        public static EquipmentState ReadEquipmentState(JsonObjectReader r)
        {
            var s = new EquipmentState(r.String("characterId"), ReadEntries(r, "entries"), r.Int("version"), r.Int("rulesVersion"));
            r.EnsureNoUnknownKeys();
            return s;
        }

        public static OwnershipView ReadOwnership(JsonObjectReader r)
        {
            var pairs = new List<KeyValuePair<string, IEnumerable<string>>>();
            foreach (var o in r.Objects("items"))
            {
                pairs.Add(new KeyValuePair<string, IEnumerable<string>>(o.String("itemId"), o.StringList("variants")));
                o.EnsureNoUnknownKeys();
            }
            r.EnsureNoUnknownKeys();
            return new OwnershipView(pairs);
        }

        static List<EquipmentEntry> ReadEntries(JsonObjectReader r, string key)
        {
            var entries = new List<EquipmentEntry>();
            foreach (var o in r.Objects(key))
            {
                entries.Add(new EquipmentEntry(o.String("slotId"), o.String("itemId"), o.String("variantId")));
                o.EnsureNoUnknownKeys();
            }
            return entries;
        }

        static List<BodyRegion> ReadRegions(JsonObjectReader r, string key)
        {
            var list = new List<BodyRegion>();
            foreach (var s in r.StringList(key))
            {
                if (!EnumNames.TryParse(s, out BodyRegion region)) throw new JsonFormatException(r.Path + "." + key, "unknown body region " + s);
                list.Add(region);
            }
            return list;
        }

        static ItemKind ParseKind(string s, string path)
        {
            if (!EnumNames.TryParse(s, out ItemKind kind)) throw new JsonFormatException(path, "unknown item kind " + s);
            return kind;
        }

        /// <summary>Canonical tree of an equipment state: entries sorted by slot order, then slot id.</summary>
        public static Dictionary<string, object> ToTree(EquipmentState state, Catalog catalog)
        {
            var entries = new List<EquipmentEntry>(state.Entries);
            entries.Sort((a, b) =>
            {
                int c = catalog.SlotOrder(a.SlotId).CompareTo(catalog.SlotOrder(b.SlotId));
                return c != 0 ? c : string.CompareOrdinal(a.SlotId, b.SlotId);
            });
            var list = new List<object>();
            foreach (var e in entries)
                list.Add(new Dictionary<string, object> { ["slotId"] = e.SlotId, ["itemId"] = e.ItemId, ["variantId"] = e.VariantId });
            return new Dictionary<string, object>
            {
                ["characterId"] = state.CharacterId, ["entries"] = list, ["version"] = (long)state.Version, ["rulesVersion"] = (long)state.RulesVersion
            };
        }
    }
}
