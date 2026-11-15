using System;
using System.Collections.Generic;
using System.IO;
using MMG.Appearance;
using MMG.Data;
using MMG.Data.Json;

namespace MMG.Tests
{
    /// <summary>
    /// Runs one case of Shared/testcases/appearance/cases_*.json. The server TypeScript runner must follow the same
    /// steps: resolve fixtures, run the operation, compare the canonical result tree with "expected".
    /// </summary>
    public static class SharedCaseRunner
    {
        public static readonly string[] CaseFiles = { "cases_equipment.json", "cases_resolve.json" };

        public static Dictionary<string, object> LoadFile(string fileName) => SharedFiles.ReadTree(Path.Combine(SharedFiles.CasesDir, fileName));

        public static Dictionary<string, object> FindCase(Dictionary<string, object> file, string caseId)
        {
            foreach (var c in (List<object>)file["cases"])
                if ((string)((Dictionary<string, object>)c)["caseId"] == caseId) return (Dictionary<string, object>)c;
            throw new ArgumentException("no case " + caseId);
        }

        public static IEnumerable<(string file, string caseId)> AllCases()
        {
            foreach (var f in CaseFiles)
                foreach (var c in (List<object>)LoadFile(f)["cases"])
                    yield return (f, (string)((Dictionary<string, object>)c)["caseId"]);
        }

        /// <summary>Runs the case. <paramref name="permute"/> may reorder input lists (determinism test).</summary>
        public static object Run(Catalog catalog, Dictionary<string, object> file, Dictionary<string, object> c, Func<List<object>, List<object>> permute = null)
        {
            permute = permute ?? (l => l);
            var op = (Dictionary<string, object>)c["operation"];
            string kind = (string)op["op"];
            if (kind == "normalizeOnePiece")
            {
                var list = new List<object>();
                foreach (Dictionary<string, object> n in (List<object>)op["cases"])
                {
                    var (t, b) = OnePieceStatNormalizer.Normalize(Int(n["top"]), Int(n["bottom"]), Int(n["referenceTopMax"]), Int(n["referenceBottomMax"]));
                    list.Add(new Dictionary<string, object> { ["top"] = (long)t, ["bottom"] = (long)b });
                }
                return list;
            }

            var context = ReadContext(file, c);
            var state = ReadState(file, c, permute);
            switch (kind)
            {
                case "equip":
                    return ResultJson.ToTree(EquipmentRules.Equip(catalog, context, state, (string)op["itemId"], (string)op["variantId"], ReadOwnership(file, c, permute)), catalog);
                case "unequip":
                    return ResultJson.ToTree(EquipmentRules.Unequip(catalog, context, state, (string)op["slotId"], ReadOwnership(file, c, permute)), catalog);
                case "validate":
                    return ResultJson.ToTree(EquipmentRules.Validate(catalog, context, state, ReadOwnership(file, c, permute)));
                case "statSources":
                    return ResultJson.ToTree(StatSourceResolver.Resolve(catalog, state));
                case "resolve":
                    var appearance = CatalogJson.ReadAppearance(new JsonObjectReader(c["appearance"], "$.appearance"));
                    return ResultJson.ToTree(AppearanceResolver.Resolve(catalog, context.CharacterDefId, context.BodyPresetId, appearance, state));
                default:
                    throw new NotSupportedException("op " + kind);
            }
        }

        public static object Expected(Dictionary<string, object> file, Dictionary<string, object> c)
        {
            var op = (Dictionary<string, object>)c["operation"];
            if ((string)op["op"] == "normalizeOnePiece")
            {
                var list = new List<object>();
                foreach (Dictionary<string, object> n in (List<object>)op["cases"])
                    list.Add(new Dictionary<string, object> { ["top"] = n["expectedTop"], ["bottom"] = n["expectedBottom"] });
                return list;
            }
            var expected = (Dictionary<string, object>)c["expected"];
            if (expected.TryGetValue("state", out var s) && s is string name)
            {
                var copy = new Dictionary<string, object>(expected) { ["state"] = Fixture(file, "states", name) };
                return copy;
            }
            return expected;
        }

        static CharacterContext ReadContext(Dictionary<string, object> file, Dictionary<string, object> c)
        {
            object raw = c.TryGetValue("context", out var own) ? own : Fixture(file, "context", null);
            var r = new JsonObjectReader(raw, "$.context");
            return new CharacterContext(r.String("characterDefId"), r.String("bodyPresetId"));
        }

        static EquipmentState ReadState(Dictionary<string, object> file, Dictionary<string, object> c, Func<List<object>, List<object>> permute)
        {
            object raw = c["state"] is string name ? Fixture(file, "states", name) : c["state"];
            var copy = new Dictionary<string, object>((Dictionary<string, object>)raw);
            copy["entries"] = permute(new List<object>((List<object>)copy["entries"]));
            return CatalogJson.ReadEquipmentState(new JsonObjectReader(copy, "$.state"));
        }

        static OwnershipView ReadOwnership(Dictionary<string, object> file, Dictionary<string, object> c, Func<List<object>, List<object>> permute)
        {
            var raw = (Dictionary<string, object>)Fixture(file, "ownership", (string)c["ownership"]);
            var copy = new Dictionary<string, object>(raw) { ["items"] = permute(new List<object>((List<object>)raw["items"])) };
            return CatalogJson.ReadOwnership(new JsonObjectReader(copy, "$.ownership"));
        }

        static object Fixture(Dictionary<string, object> file, string group, string name)
        {
            var fixtures = (Dictionary<string, object>)file["fixtures"];
            var g = fixtures[group];
            return name == null ? g : ((Dictionary<string, object>)g)[name];
        }

        static int Int(object v) => (int)(long)v;
    }
}
