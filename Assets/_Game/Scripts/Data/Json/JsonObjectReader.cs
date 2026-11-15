using System;
using System.Collections.Generic;

namespace MMG.Data.Json
{
    /// <summary>Strict reader over a parsed JSON object: wrong types, missing keys and unknown keys are errors.</summary>
    public sealed class JsonObjectReader
    {
        readonly Dictionary<string, object> map;
        readonly HashSet<string> used = new HashSet<string>(StringComparer.Ordinal);

        public string Path { get; }

        public JsonObjectReader(object value, string path)
        {
            Path = path;
            map = value as Dictionary<string, object> ?? throw new JsonFormatException(path, "object expected");
        }

        public bool Has(string key) => map.ContainsKey(key);

        object Raw(string key, bool required)
        {
            used.Add(key);
            if (map.TryGetValue(key, out var v)) return v;
            if (required) throw new JsonFormatException(Path + "." + key, "required field missing");
            return null;
        }

        public string String(string key)
        {
            var v = Raw(key, true);
            return v as string ?? throw new JsonFormatException(Path + "." + key, "string expected");
        }

        public string StringOrNull(string key)
        {
            var v = Raw(key, false);
            if (v == null) return null;
            return v as string ?? throw new JsonFormatException(Path + "." + key, "string or null expected");
        }

        public int Int(string key)
        {
            var v = Raw(key, true);
            return ToInt(v, Path + "." + key);
        }

        public int? IntOrNull(string key)
        {
            var v = Raw(key, false);
            if (v == null) return null;
            return ToInt(v, Path + "." + key);
        }

        static int ToInt(object v, string path)
        {
            if (v is long l && l >= int.MinValue && l <= int.MaxValue) return (int)l;
            throw new JsonFormatException(path, "integer expected");
        }

        public bool Bool(string key)
        {
            var v = Raw(key, true);
            if (v is bool b) return b;
            throw new JsonFormatException(Path + "." + key, "boolean expected");
        }

        public List<object> Array(string key)
        {
            var v = Raw(key, true);
            return v as List<object> ?? throw new JsonFormatException(Path + "." + key, "array expected");
        }

        public List<object> ArrayOrEmpty(string key)
        {
            var v = Raw(key, false);
            if (v == null) return new List<object>();
            return v as List<object> ?? throw new JsonFormatException(Path + "." + key, "array expected");
        }

        public JsonObjectReader Object(string key) => new JsonObjectReader(Raw(key, true), Path + "." + key);

        public JsonObjectReader ObjectOrNull(string key)
        {
            var v = Raw(key, false);
            return v == null ? null : new JsonObjectReader(v, Path + "." + key);
        }

        public List<string> StringList(string key, bool required = true)
        {
            var v = Raw(key, required);
            var result = new List<string>();
            if (v == null) return result;
            var list = v as List<object> ?? throw new JsonFormatException(Path + "." + key, "array expected");
            for (int i = 0; i < list.Count; i++)
                result.Add(list[i] as string ?? throw new JsonFormatException(Path + "." + key + "[" + i + "]", "string expected"));
            return result;
        }

        public List<JsonObjectReader> Objects(string key, bool required = true)
        {
            var list = required ? Array(key) : ArrayOrEmpty(key);
            var result = new List<JsonObjectReader>(list.Count);
            for (int i = 0; i < list.Count; i++) result.Add(new JsonObjectReader(list[i], Path + "." + key + "[" + i + "]"));
            return result;
        }

        public void EnsureNoUnknownKeys()
        {
            foreach (var key in map.Keys)
                if (!used.Contains(key)) throw new JsonFormatException(Path + "." + key, "unknown field");
        }
    }
}
