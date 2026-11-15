using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace MMG.Data.Json
{
    public sealed class JsonFormatException : FormatException
    {
        public string JsonPath { get; }

        public JsonFormatException(string path, string message) : base(path + ": " + message)
        {
            JsonPath = path;
        }
    }

    /// <summary>
    /// Minimal JSON reader. Objects become Dictionary&lt;string, object&gt; (ordinal keys, duplicates rejected),
    /// arrays List&lt;object&gt;, integers long, other numbers double.
    /// </summary>
    public static class JsonParser
    {
        public static object Parse(string text)
        {
            if (text == null) throw new ArgumentNullException(nameof(text));
            var p = new Parser(text);
            p.SkipWhitespace();
            var value = p.ReadValue("$");
            p.SkipWhitespace();
            if (!p.AtEnd) throw p.Error("$", "unexpected characters after the root value");
            return value;
        }

        sealed class Parser
        {
            readonly string s;
            int i;

            public Parser(string text)
            {
                s = text;
                if (s.Length > 0 && s[0] == '\uFEFF') i = 1;
            }

            public bool AtEnd => i >= s.Length;

            public JsonFormatException Error(string path, string message) =>
                new JsonFormatException(path, message + " (offset " + i + ")");

            public void SkipWhitespace()
            {
                while (i < s.Length && (s[i] == ' ' || s[i] == '\t' || s[i] == '\n' || s[i] == '\r')) i++;
            }

            public object ReadValue(string path)
            {
                if (AtEnd) throw Error(path, "unexpected end of input");
                char c = s[i];
                switch (c)
                {
                    case '{': return ReadObject(path);
                    case '[': return ReadArray(path);
                    case '"': return ReadString(path);
                    case 't': Expect("true", path); return true;
                    case 'f': Expect("false", path); return false;
                    case 'n': Expect("null", path); return null;
                    default:
                        if (c == '-' || (c >= '0' && c <= '9')) return ReadNumber(path);
                        throw Error(path, "unexpected character '" + c + "'");
                }
            }

            void Expect(string word, string path)
            {
                if (string.CompareOrdinal(s, i, word, 0, word.Length) != 0) throw Error(path, "invalid literal");
                i += word.Length;
            }

            Dictionary<string, object> ReadObject(string path)
            {
                var map = new Dictionary<string, object>(StringComparer.Ordinal);
                i++;
                SkipWhitespace();
                if (!AtEnd && s[i] == '}') { i++; return map; }
                while (true)
                {
                    SkipWhitespace();
                    if (AtEnd || s[i] != '"') throw Error(path, "object key expected");
                    string key = ReadString(path);
                    SkipWhitespace();
                    if (AtEnd || s[i] != ':') throw Error(path, "':' expected");
                    i++;
                    SkipWhitespace();
                    string childPath = path + "." + key;
                    if (map.ContainsKey(key)) throw Error(childPath, "duplicate key");
                    map.Add(key, ReadValue(childPath));
                    SkipWhitespace();
                    if (AtEnd) throw Error(path, "unexpected end of object");
                    if (s[i] == ',') { i++; continue; }
                    if (s[i] == '}') { i++; return map; }
                    throw Error(path, "',' or '}' expected");
                }
            }

            List<object> ReadArray(string path)
            {
                var list = new List<object>();
                i++;
                SkipWhitespace();
                if (!AtEnd && s[i] == ']') { i++; return list; }
                while (true)
                {
                    SkipWhitespace();
                    list.Add(ReadValue(path + "[" + list.Count + "]"));
                    SkipWhitespace();
                    if (AtEnd) throw Error(path, "unexpected end of array");
                    if (s[i] == ',') { i++; continue; }
                    if (s[i] == ']') { i++; return list; }
                    throw Error(path, "',' or ']' expected");
                }
            }

            string ReadString(string path)
            {
                i++;
                var sb = new StringBuilder();
                while (true)
                {
                    if (AtEnd) throw Error(path, "unterminated string");
                    char c = s[i++];
                    if (c == '"') return sb.ToString();
                    if (c < ' ') throw Error(path, "control character in string");
                    if (c != '\\') { sb.Append(c); continue; }
                    if (AtEnd) throw Error(path, "unterminated escape");
                    char e = s[i++];
                    switch (e)
                    {
                        case '"': sb.Append('"'); break;
                        case '\\': sb.Append('\\'); break;
                        case '/': sb.Append('/'); break;
                        case 'b': sb.Append('\b'); break;
                        case 'f': sb.Append('\f'); break;
                        case 'n': sb.Append('\n'); break;
                        case 'r': sb.Append('\r'); break;
                        case 't': sb.Append('\t'); break;
                        case 'u':
                            if (i + 4 > s.Length) throw Error(path, "bad unicode escape");
                            if (!int.TryParse(s.Substring(i, 4), NumberStyles.AllowHexSpecifier, CultureInfo.InvariantCulture, out int code))
                                throw Error(path, "bad unicode escape");
                            sb.Append((char)code);
                            i += 4;
                            break;
                        default: throw Error(path, "unknown escape '\\" + e + "'");
                    }
                }
            }

            object ReadNumber(string path)
            {
                int start = i;
                if (s[i] == '-') i++;
                while (i < s.Length && char.IsDigit(s[i])) i++;
                bool integer = true;
                if (i < s.Length && s[i] == '.')
                {
                    integer = false;
                    i++;
                    while (i < s.Length && char.IsDigit(s[i])) i++;
                }
                if (i < s.Length && (s[i] == 'e' || s[i] == 'E'))
                {
                    integer = false;
                    i++;
                    if (i < s.Length && (s[i] == '+' || s[i] == '-')) i++;
                    while (i < s.Length && char.IsDigit(s[i])) i++;
                }
                string token = s.Substring(start, i - start);
                if (integer && long.TryParse(token, NumberStyles.AllowLeadingSign, CultureInfo.InvariantCulture, out long l)) return l;
                if (double.TryParse(token, NumberStyles.Float, CultureInfo.InvariantCulture, out double d)) return d;
                throw Error(path, "invalid number '" + token + "'");
            }
        }
    }
}
