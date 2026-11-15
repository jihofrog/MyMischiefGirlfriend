using System;
using System.Collections.Generic;
using MMG.Data;
using MMG.Data.Json;
using NUnit.Framework;

namespace MMG.Tests
{
    /// <summary>Shared JSON cases (gameplay cases are the contract with the server implementation).</summary>
    public class SharedCaseTests
    {
        static IEnumerable<TestCaseData> Cases()
        {
            foreach (var (file, caseId) in SharedCaseRunner.AllCases())
                yield return new TestCaseData(file, caseId).SetName(file.Replace(".json", "") + "." + caseId);
        }

        [TestCaseSource(nameof(Cases))]
        public void Case_matches_expected(string fileName, string caseId)
        {
            var file = SharedCaseRunner.LoadFile(fileName);
            var c = SharedCaseRunner.FindCase(file, caseId);
            var catalog = SharedFiles.LoadCatalog(System.IO.Path.Combine(SharedFiles.CasesDir, (string)file["catalog"]));
            object actual = SharedCaseRunner.Run(catalog, file, c);
            object expected = SharedCaseRunner.Expected(file, c);
            string diff = SharedFiles.FirstDifference(expected, actual);
            Assert.IsNull(diff, diff + "\nactual: " + JsonWriter.Write(actual));
        }

        /// <summary>Control: the comparison must fail when an expected value is wrong.</summary>
        [TestCase("cases_equipment.json", "onepiece_replaces_top_and_bottom")]
        [TestCase("cases_resolve.json", "resolve_hat_and_long_boots")]
        [TestCase("cases_equipment.json", "validate_broken_state")]
        public void Comparison_detects_a_wrong_expectation(string fileName, string caseId)
        {
            var file = SharedCaseRunner.LoadFile(fileName);
            var c = SharedCaseRunner.FindCase(file, caseId);
            var catalog = SharedFiles.LoadCatalog(System.IO.Path.Combine(SharedFiles.CasesDir, (string)file["catalog"]));
            object actual = SharedCaseRunner.Run(catalog, file, c);
            var expected = (Dictionary<string, object>)JsonParser.Parse(JsonWriter.Write(SharedCaseRunner.Expected(file, c)));
            Assert.IsNull(SharedFiles.FirstDifference(expected, actual));

            var wrongOrder = (Dictionary<string, object>)JsonParser.Parse(JsonWriter.Write(expected));
            var list = (List<object>)(wrongOrder.ContainsKey("changes") ? wrongOrder["changes"] : wrongOrder.ContainsKey("issues") ? wrongOrder["issues"] : wrongOrder["items"]);
            list.Reverse();
            Assert.IsNotNull(SharedFiles.FirstDifference(wrongOrder, actual), "reordered list must not match");

            var missing = (Dictionary<string, object>)JsonParser.Parse(JsonWriter.Write(expected));
            ((List<object>)(missing.ContainsKey("changes") ? missing["changes"] : missing.ContainsKey("issues") ? missing["issues"] : missing["items"])).RemoveAt(0);
            Assert.IsNotNull(SharedFiles.FirstDifference(missing, actual), "missing entry must not match");

            var extraKey = (Dictionary<string, object>)JsonParser.Parse(JsonWriter.Write(expected));
            extraKey["unexpected"] = 1L;
            Assert.IsNotNull(SharedFiles.FirstDifference(extraKey, actual), "extra key must not match");
        }

        [Test]
        public void Every_case_file_has_unique_case_ids()
        {
            var seen = new HashSet<string>(StringComparer.Ordinal);
            foreach (var (_, caseId) in SharedCaseRunner.AllCases()) Assert.IsTrue(seen.Add(caseId), "duplicate case id " + caseId);
            Assert.Greater(seen.Count, 20);
        }
    }

    /// <summary>Same input → same output, whatever the order of catalog lists, ownership and equipment entries.</summary>
    public class DeterminismTests
    {
        static readonly string[] CatalogLists = { "bodyTypes", "slots", "colors", "faceStyles", "bodyPresets", "items", "variants", "characters" };

        [Test]
        public void Shuffled_inputs_give_identical_results([Values(1, 7, 42, 1234, 98765)] int seed)
        {
            var rng = new Random(seed);
            List<object> Shuffle(List<object> list)
            {
                var copy = new List<object>(list);
                for (int i = copy.Count - 1; i > 0; i--)
                {
                    int j = rng.Next(i + 1);
                    (copy[i], copy[j]) = (copy[j], copy[i]);
                }
                return copy;
            }

            foreach (var fileName in SharedCaseRunner.CaseFiles)
            {
                var file = SharedCaseRunner.LoadFile(fileName);
                string catalogPath = System.IO.Path.Combine(SharedFiles.CasesDir, (string)file["catalog"]);
                var catalog = SharedFiles.LoadCatalog(catalogPath);
                var tree = SharedFiles.ReadTree(catalogPath);
                foreach (var key in CatalogLists) tree[key] = Shuffle((List<object>)tree[key]);
                var rules = (Dictionary<string, object>)tree["rules"];
                rules["exclusive"] = Shuffle((List<object>)rules["exclusive"]);
                rules["hairFormRequirements"] = Shuffle((List<object>)rules["hairFormRequirements"]);
                foreach (Dictionary<string, object> item in (List<object>)tree["items"])
                {
                    item["tags"] = Shuffle((List<object>)item["tags"]);
                    item["covers"] = Shuffle((List<object>)item["covers"]);
                    item["occupies"] = Shuffle((List<object>)item["occupies"]);
                }
                var shuffled = CatalogJson.ReadCatalog(JsonWriter.Write(tree));

                foreach (Dictionary<string, object> c in (List<object>)file["cases"])
                {
                    string a = JsonWriter.Write(SharedCaseRunner.Run(catalog, file, c));
                    string b = JsonWriter.Write(SharedCaseRunner.Run(shuffled, file, c, Shuffle));
                    string again = JsonWriter.Write(SharedCaseRunner.Run(catalog, file, c));
                    Assert.AreEqual(a, b, (string)c["caseId"] + " differs with shuffled input (seed " + seed + ")");
                    Assert.AreEqual(a, again, (string)c["caseId"] + " differs between two runs");
                }
            }
        }
    }
}
