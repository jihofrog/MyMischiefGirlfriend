using System.Collections.Generic;
using MMG.Data;
using MMG.Data.Json;

namespace MMG.Appearance
{
    /// <summary>
    /// Canonical JSON trees of rule and resolver results. Shared/testcases/appearance stores expected results in this
    /// form; the server implementation must produce the same trees.
    /// </summary>
    public static class ResultJson
    {
        public static Dictionary<string, object> ToTree(EquipResult r, Catalog catalog)
        {
            var changes = new List<object>();
            foreach (var c in r.Changes)
                changes.Add(new Dictionary<string, object>
                {
                    ["change"] = c.Change, ["slotIds"] = new List<object>(c.SlotIds), ["itemId"] = c.ItemId,
                    ["variantId"] = c.VariantId, ["reason"] = c.Reason
                });
            return new Dictionary<string, object>
            {
                ["success"] = r.Success, ["error"] = r.Error, ["state"] = CatalogJson.ToTree(r.State, catalog), ["changes"] = changes
            };
        }

        public static Dictionary<string, object> ToTree(IEnumerable<RuleIssue> issues)
        {
            var list = new List<object>();
            foreach (var i in issues)
                list.Add(new Dictionary<string, object> { ["code"] = i.Code, ["slotId"] = i.SlotId, ["itemId"] = i.ItemId });
            return new Dictionary<string, object> { ["issues"] = list };
        }

        public static Dictionary<string, object> ToTree(IEnumerable<StatSource> sources)
        {
            var list = new List<object>();
            foreach (var s in sources)
                list.Add(new Dictionary<string, object>
                {
                    ["statGroup"] = EnumNames.Of(s.StatGroup), ["slotId"] = s.SlotId, ["itemId"] = s.ItemId,
                    ["variantId"] = s.VariantId, ["viaOnePiece"] = s.ViaOnePiece
                });
            return new Dictionary<string, object> { ["sources"] = list };
        }

        public static Dictionary<string, object> ToTree(ResolvedAppearance a)
        {
            var items = new List<object>();
            foreach (var it in a.Items)
            {
                var colors = new List<object>();
                foreach (var c in it.Colors) colors.Add(new Dictionary<string, object> { ["channel"] = c.Channel, ["rgb"] = c.Rgb });
                items.Add(new Dictionary<string, object>
                {
                    ["slotIds"] = new List<object>(it.SlotIds), ["itemId"] = it.ItemId, ["variantId"] = it.VariantId,
                    ["kind"] = EnumNames.Of(it.Kind), ["layer"] = (long)it.Layer, ["tags"] = new List<object>(it.Tags),
                    ["covers"] = Regions(it.Covers), ["colors"] = colors, ["occludedRegions"] = Regions(it.OccludedRegions)
                });
            }
            var intents = new List<object>();
            foreach (var i in a.Intents)
                intents.Add(new Dictionary<string, object> { ["kind"] = i.Kind, ["value"] = i.Value, ["causeItemId"] = i.CauseItemId });
            return new Dictionary<string, object>
            {
                ["characterDefId"] = a.CharacterDefId,
                ["bodyPresetId"] = a.BodyPresetId,
                ["bodyType"] = a.BodyType,
                ["headBaseId"] = a.HeadBaseId,
                ["face"] = new Dictionary<string, object>
                {
                    ["eye"] = a.Face.Eye, ["nose"] = a.Face.Nose, ["mouth"] = a.Face.Mouth, ["ear"] = a.Face.Ear, ["brow"] = a.Face.Brow
                },
                ["colors"] = new Dictionary<string, object>
                {
                    ["skin"] = Color(a.Colors.Skin), ["hair"] = Color(a.Colors.Hair), ["eye"] = Color(a.Colors.Eye),
                    ["brow"] = Color(a.Colors.Brow), ["browFollowsHair"] = a.Colors.BrowFollowsHair
                },
                ["items"] = items,
                ["coveredRegions"] = Regions(a.CoveredRegions),
                ["intents"] = intents,
                ["warnings"] = new List<object>(a.Warnings)
            };
        }

        static Dictionary<string, object> Color(ResolvedColor c) => new Dictionary<string, object> { ["colorId"] = c.ColorId, ["rgb"] = c.Rgb };

        static List<object> Regions(IEnumerable<BodyRegion> regions)
        {
            var list = new List<object>();
            foreach (var r in regions) list.Add(EnumNames.Of(r));
            return list;
        }
    }
}
