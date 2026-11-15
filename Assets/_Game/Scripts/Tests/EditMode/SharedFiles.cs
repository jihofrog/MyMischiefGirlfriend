using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using MMG.Data;
using MMG.Data.Json;

namespace MMG.Tests
{
    /// <summary>Access to the shared JSON files at &lt;project&gt;/Shared (outside Assets, also read by the server).</summary>
    public static class SharedFiles
    {
        public static string Root => Path.GetFullPath(Path.Combine(UnityEngine.Application.dataPath, "..", "Shared"));
        public static string CasesDir => Path.Combine(Root, "testcases", "appearance");
        public static string SampleCatalogPath => Path.Combine(Root, "samples", "catalog_mainGirlfriend_v1.json");
        public static string TestCatalogPath => Path.Combine(CasesDir, "catalog_rules_test.json");

        public static string Read(string path) => File.ReadAllText(path, Encoding.UTF8);

        public static Catalog LoadCatalog(string path) => CatalogJson.ReadCatalog(Read(path));

        public static Dictionary<string, object> ReadTree(string path) => (Dictionary<string, object>)JsonParser.Parse(Read(path));

        /// <summary>First differing path between two canonical trees, or null when equal.</summary>
        public static string FirstDifference(object expected, object actual, string path = "$")
        {
            if (expected is Dictionary<string, object> em)
            {
                if (!(actual is IDictionary<string, object> am)) return path + ": expected object";
                var keys = new SortedSet<string>(em.Keys, StringComparer.Ordinal);
                keys.UnionWith(am.Keys);
                foreach (var k in keys)
                {
                    if (!em.ContainsKey(k)) return path + "." + k + ": unexpected key";
                    if (!am.ContainsKey(k)) return path + "." + k + ": missing key";
                    var d = FirstDifference(em[k], am[k], path + "." + k);
                    if (d != null) return d;
                }
                return null;
            }
            if (expected is List<object> el)
            {
                var al = ToList(actual);
                if (al == null) return path + ": expected array";
                for (int i = 0; i < Math.Min(el.Count, al.Count); i++)
                {
                    var d = FirstDifference(el[i], al[i], path + "[" + i + "]");
                    if (d != null) return d;
                }
                return el.Count == al.Count ? null : path + ": expected " + el.Count + " items, got " + al.Count;
            }
            string e = JsonWriter.Write(expected), a = JsonWriter.Write(Normalize(actual));
            return e == a ? null : path + ": expected " + e + ", got " + a;
        }

        static List<object> ToList(object v)
        {
            if (v is List<object> l) return l;
            if (v is System.Collections.IEnumerable en && !(v is string) && !(v is IDictionary<string, object>))
            {
                var list = new List<object>();
                foreach (var x in en) list.Add(x);
                return list;
            }
            return null;
        }

        static object Normalize(object v) => v is int i ? (long)i : v;
    }
}
