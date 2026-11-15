using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace MMG.Data.Json
{
    /// <summary>
    /// Canonical JSON: object keys in ordinal order, no whitespace, integers only. The server (TypeScript) side
    /// compares against the same form, so the format must not depend on platform culture or dictionary order.
    /// </summary>
    public static class JsonWriter
    {
        public static string Write(object value)
        {
            var sb = new StringBuilder();
            WriteValue(sb, value);
            return sb.ToString();
        }

        static void WriteValue(StringBuilder sb, object value)
        {
            switch (value)
            {
                case null: sb.Append("null"); return;
                case bool b: sb.Append(b ? "true" : "false"); return;
                case string str: WriteString(sb, str); return;
                case int n: sb.Append(n.ToString(CultureInfo.InvariantCulture)); return;
                case long n: sb.Append(n.ToString(CultureInfo.InvariantCulture)); return;
                case IDictionary<string, object> map: WriteObject(sb, map); return;
                case IEnumerable list: WriteArray(sb, list); return;
                default: throw new ArgumentException("unsupported JSON value type " + value.GetType().Name);
            }
        }

        static void WriteObject(StringBuilder sb, IDictionary<string, object> map)
        {
            var keys = new List<string>(map.Keys);
            keys.Sort(StringComparer.Ordinal);
            sb.Append('{');
            for (int k = 0; k < keys.Count; k++)
            {
                if (k > 0) sb.Append(',');
                WriteString(sb, keys[k]);
                sb.Append(':');
                WriteValue(sb, map[keys[k]]);
            }
            sb.Append('}');
        }

        static void WriteArray(StringBuilder sb, IEnumerable list)
        {
            sb.Append('[');
            bool first = true;
            foreach (var item in list)
            {
                if (!first) sb.Append(',');
                first = false;
                WriteValue(sb, item);
            }
            sb.Append(']');
        }

        static void WriteString(StringBuilder sb, string s)
        {
            sb.Append('"');
            foreach (char c in s)
            {
                switch (c)
                {
                    case '"': sb.Append("\\\""); break;
                    case '\\': sb.Append("\\\\"); break;
                    case '\n': sb.Append("\\n"); break;
                    case '\r': sb.Append("\\r"); break;
                    case '\t': sb.Append("\\t"); break;
                    default:
                        if (c < ' ') sb.Append("\\u").Append(((int)c).ToString("x4", CultureInfo.InvariantCulture));
                        else sb.Append(c);
                        break;
                }
            }
            sb.Append('"');
        }
    }
}
