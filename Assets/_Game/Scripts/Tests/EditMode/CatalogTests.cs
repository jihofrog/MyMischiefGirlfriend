using System;
using System.Collections.Generic;
using System.Linq;
using MMG.Appearance;
using MMG.Data;
using MMG.Data.Json;
using MMG.Data.Validation;
using NUnit.Framework;

namespace MMG.Tests
{
    public class JsonTests
    {
        [Test]
        public void Parses_and_writes_canonical_json()
        {
            var tree = JsonParser.Parse("{ \"b\": [1, true, null, \"x\\n\\u00e9\"], \"a\": { \"z\": -3 } }");
            Assert.AreEqual("{\"a\":{\"z\":-3},\"b\":[1,true,null,\"x\\né\"]}", JsonWriter.Write(tree));
        }

        [TestCase("{\"a\":1,\"a\":2}")]
        [TestCase("{\"a\":1,}")]
        [TestCase("[1 2]")]
        [TestCase("{\"a\":1} x")]
        [TestCase("\"unterminated")]
        public void Rejects_bad_json(string text)
        {
            Assert.Throws<JsonFormatException>(() => JsonParser.Parse(text));
        }

        [Test]
        public void Strict_reader_rejects_unknown_fields_and_wrong_types()
        {
            var text = SharedFiles.Read(SharedFiles.SampleCatalogPath);
            Assert.Throws<JsonFormatException>(() => CatalogJson.ReadCatalog(text.Replace("\"catalogVersion\": 1,", "\"catalogVersion\": 1, \"extra\": 0,")));
            Assert.Throws<JsonFormatException>(() => CatalogJson.ReadCatalog(text.Replace("\"catalogVersion\": 1,", "\"catalogVersion\": \"1\",")));
            Assert.Throws<JsonFormatException>(() => CatalogJson.ReadCatalog(text.Replace("\"kind\": \"hair\"", "\"kind\": \"hat\"")));
        }
    }

    public class CatalogTests
    {
        static List<ValidationIssue> Issues(string path) => CatalogValidator.Validate(SharedFiles.LoadCatalog(path));

        [Test]
        public void Sample_catalog_is_valid()
        {
            var issues = Issues(SharedFiles.SampleCatalogPath);
            Assert.IsEmpty(issues, string.Join("\n", issues));
        }

        [Test]
        public void Rule_test_catalog_is_valid()
        {
            var issues = Issues(SharedFiles.TestCatalogPath);
            Assert.IsEmpty(issues, string.Join("\n", issues));
        }

        [Test]
        public void Sample_catalog_has_the_current_content()
        {
            var c = SharedFiles.LoadCatalog(SharedFiles.SampleCatalogPath);
            CollectionAssert.AreEqual(
                new[] { "acc_head_hairclip_x_01", "bottom_pleatskirt_01", "hair_bob_01", "legwear_thighhigh_01", "shoes_ankleboot_01", "top_blouse_01" },
                c.Items.Select(i => i.ItemId).ToArray());
            CollectionAssert.AreEqual(new[] { "standard" }, c.BodyTypes.ToArray());
            Assert.IsTrue(c.TryGetFaceStyle("brow_basic_01", out var brow) && brow.Feature == FaceFeature.Brow);
        }

        /// <summary>Default outfits must also pass the gameplay rules (exclusive tags, hair forms, accessory count).</summary>
        [TestCase("sample")]
        [TestCase("test")]
        public void Default_equipment_passes_gameplay_rules(string which)
        {
            var c = SharedFiles.LoadCatalog(which == "sample" ? SharedFiles.SampleCatalogPath : SharedFiles.TestCatalogPath);
            foreach (var ch in c.Characters)
            {
                var owned = new OwnershipView(ch.DefaultEquipment.Select(e => new KeyValuePair<string, IEnumerable<string>>(e.ItemId, new[] { e.VariantId })));
                var state = new EquipmentState("pc", ch.DefaultEquipment, 0, c.Rules.RulesVersion);
                var issues = EquipmentRules.Validate(c, new CharacterContext(ch.CharacterDefId, ch.DefaultBodyPresetId), state, owned);
                Assert.IsEmpty(issues, ch.CharacterDefId + ": " + string.Join(", ", issues));
            }
        }

        static List<string> CodesAfter(Action<Dictionary<string, object>> mutate, string path = null)
        {
            var tree = SharedFiles.ReadTree(path ?? SharedFiles.TestCatalogPath);
            mutate(tree);
            return CatalogValidator.Validate(CatalogJson.ReadCatalog(JsonWriter.Write(tree))).Select(i => i.Code).Distinct().ToList();
        }

        static Dictionary<string, object> Find(Dictionary<string, object> tree, string list, string idKey, string id) =>
            ((List<object>)tree[list]).Cast<Dictionary<string, object>>().First(o => (string)o[idKey] == id);

        [Test]
        public void Detects_policy_U1_legwear_with_stat()
        {
            var codes = CodesAfter(t => Find(t, "slots", "slotId", "legwear")["statGroup"] = "Footwear");
            CollectionAssert.Contains(codes, "POLICY_U1");
        }

        [Test]
        public void Detects_policy_U12_optional_shoes()
        {
            var codes = CodesAfter(t => Find(t, "slots", "slotId", "shoes")["required"] = false);
            CollectionAssert.Contains(codes, "POLICY_U12");
        }

        [Test]
        public void Detects_policy_U7_color_word_in_item_id()
        {
            var codes = CodesAfter(t =>
            {
                Find(t, "items", "itemId", "top_hoodie_01")["itemId"] = "top_hoodie_gray_01";
            });
            CollectionAssert.Contains(codes, "ID_HAS_COLOR_WORD");
        }

        [Test]
        public void Detects_broken_references()
        {
            var codes = CodesAfter(t => Find(t, "variants", "variantId", "top_hoodie_01.gray")["itemId"] = "top_missing_01");
            CollectionAssert.Contains(codes, "REF_UNKNOWN");
            CollectionAssert.Contains(codes, "ITEM_NO_VARIANT");
            CollectionAssert.Contains(codes, "VARIANT_DEFAULT_INVALID");
        }

        [Test]
        public void Detects_onepiece_not_occupying_both_slots()
        {
            var codes = CodesAfter(t => Find(t, "items", "itemId", "onepiece_sundress_01")["occupies"] = new List<object> { "top" });
            CollectionAssert.Contains(codes, "ONEPIECE_OCCUPIES");
        }

        [Test]
        public void Detects_missing_default_for_required_slot()
        {
            var codes = CodesAfter(t =>
            {
                var ch = Find(t, "characters", "characterDefId", "chr_mainGirlfriend_01");
                ((List<object>)ch["defaultEquipment"]).RemoveAll(e => (string)((Dictionary<string, object>)e)["slotId"] == "shoes");
            });
            CollectionAssert.Contains(codes, "DEFAULT_REQUIRED_MISSING");
        }

        [Test]
        public void Detects_duplicate_ids_and_hair_without_default_form()
        {
            var codes = CodesAfter(t =>
            {
                var items = (List<object>)t["items"];
                items.Add(new Dictionary<string, object>(Find(t, "items", "itemId", "hair_bob_01")));
                Find(t, "items", "itemId", "hair_long_01")["hairForms"] = new List<object> { "under_hat" };
            });
            CollectionAssert.Contains(codes, "DUPLICATE_ID");
            CollectionAssert.Contains(codes, "HAIRFORMS_INVALID");
        }

        [Test]
        public void Detects_wrong_color_category_in_default_appearance()
        {
            var codes = CodesAfter(t =>
            {
                var a = (Dictionary<string, object>)Find(t, "characters", "characterDefId", "chr_mainGirlfriend_01")["defaultAppearance"];
                a["skinColorId"] = "haircolor_brown_01";
            });
            CollectionAssert.Contains(codes, "COLOR_CATEGORY_MISMATCH");
        }
    }

    public class ArchitectureTests
    {
        /// <summary>Common data and resolver must not depend on Unity or graphics engines (05 document, 0장 보완).</summary>
        [TestCase(typeof(Catalog))]
        [TestCase(typeof(AppearanceResolver))]
        public void Common_assemblies_reference_no_engine(Type marker)
        {
            var refs = marker.Assembly.GetReferencedAssemblies().Select(a => a.Name).ToList();
            foreach (var name in refs)
            {
                StringAssert.DoesNotStartWith("UnityEngine", name);
                StringAssert.DoesNotStartWith("UnityEditor", name);
                StringAssert.DoesNotStartWith("Live2D", name);
            }
        }
    }

    public class RendererSupportTests
    {
        [Test]
        public void Reports_supported_missing_and_revision_mismatch()
        {
            var catalog = SharedFiles.LoadCatalog(SharedFiles.TestCatalogPath);
            var ch = catalog.Characters[0];
            var state = new EquipmentState("pc", new List<EquipmentEntry>
            {
                new EquipmentEntry("hair", "hair_bob_01", "hair_bob_01.default"),
                new EquipmentEntry("top", "top_blouse_01", "top_blouse_01.pink"),
                new EquipmentEntry("bottom", "bottom_pleatskirt_01", "bottom_pleatskirt_01.navy"),
                new EquipmentEntry("shoes", "shoes_longboot_01", "shoes_longboot_01.brown"),
            }, 0, 1);
            var resolved = AppearanceResolver.Resolve(catalog, ch.CharacterDefId, ch.DefaultBodyPresetId, ch.DefaultAppearance, state);

            var entries = new List<RendererSupportEntry>
            {
                new RendererSupportEntry(SupportKind.BodyPreset, "body_base_01", null, 26, null),
                new RendererSupportEntry(SupportKind.FaceStyle, "eye_round_01", null, 26, null),
                new RendererSupportEntry(SupportKind.FaceStyle, "nose_dot_01", null, 26, null),
                new RendererSupportEntry(SupportKind.FaceStyle, "mouth_basic_01", null, 26, null),
                new RendererSupportEntry(SupportKind.FaceStyle, "ear_basic_01", null, 26, null),
                new RendererSupportEntry(SupportKind.FaceStyle, "brow_basic_01", null, 26, null),
                new RendererSupportEntry(SupportKind.Item, "hair_bob_01", null, 26, null),
                new RendererSupportEntry(SupportKind.Item, "top_blouse_01", "top_blouse_01.cream", 26, null),
                new RendererSupportEntry(SupportKind.Item, "bottom_pleatskirt_01", null, 30, null),
            };
            var report = RendererSupportChecker.Check(resolved, new RendererSupportManifest("cubism", "l2d/base/mainGirlfriend", 28, entries));

            Assert.IsFalse(report.AllSupported);
            var status = report.Results.ToDictionary(r => r.Kind + ":" + r.Id, r => r.Status);
            Assert.AreEqual(SupportStatus.Supported, status["BodyPreset:body_base_01"]);
            Assert.AreEqual(SupportStatus.Supported, status["FaceStyle:brow_basic_01"]);
            Assert.AreEqual(SupportStatus.Supported, status["Item:hair_bob_01"]);
            Assert.AreEqual(SupportStatus.Missing, status["Item:top_blouse_01"], "only the cream variant is drawn, pink is missing");
            Assert.AreEqual(SupportStatus.RevisionMismatch, status["Item:bottom_pleatskirt_01"], "needs base r30, base is r28");
            Assert.AreEqual(SupportStatus.Missing, status["Item:shoes_longboot_01"]);
        }
    }

    public class StatTests
    {
        [Test]
        public void Normalizer_rejects_negative_values()
        {
            Assert.Throws<ArgumentOutOfRangeException>(() => OnePieceStatNormalizer.Normalize(-1, 0, 10, 10));
        }

        [Test]
        public void Legwear_never_feeds_a_stat()
        {
            var catalog = SharedFiles.LoadCatalog(SharedFiles.SampleCatalogPath);
            var ch = catalog.Characters[0];
            var sources = StatSourceResolver.Resolve(catalog, new EquipmentState("pc", ch.DefaultEquipment, 0, 1));
            Assert.IsFalse(sources.Any(s => s.ItemId == "legwear_thighhigh_01"));
            Assert.AreEqual("shoes_ankleboot_01", sources.Single(s => s.StatGroup == StatGroup.Footwear).ItemId);
        }
    }
}
