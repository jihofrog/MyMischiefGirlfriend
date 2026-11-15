using System;
using System.Collections.Generic;

namespace MMG.Data
{
    public enum ItemKind { Hair, Top, Bottom, OnePiece, Legwear, Shoes, Accessory }

    /// <summary>Racing stat groups (01 document). Legwear has none (policy U1).</summary>
    public enum StatGroup { Hair, Top, Bottom, Footwear, Accessory }

    /// <summary>Body regions shared by 2D and 3D. Declaration order is the output sort order.</summary>
    public enum BodyRegion
    {
        HeadTop, Ear_L, Ear_R, Neck, Chest, Torso,
        UpperArm_L, UpperArm_R, Forearm_L, Forearm_R, Hand_L, Hand_R,
        Hips, Thigh_L, Thigh_R, Knee_L, Knee_R, Calf_L, Calf_R, Foot_L, Foot_R
    }

    public enum ColorCategory { Skin, Hair, Eye }

    public enum FaceFeature { Eye, Nose, Mouth, Ear, Brow }

    public enum ColorUnlock { Free, Item, Achievement }

    public enum BrowColorMode { FollowHair, Explicit }

    /// <summary>JSON names of the enums. Unknown names are format errors.</summary>
    public static class EnumNames
    {
        static readonly Dictionary<string, ItemKind> Kinds = new Dictionary<string, ItemKind>(StringComparer.Ordinal)
        {
            ["hair"] = ItemKind.Hair, ["top"] = ItemKind.Top, ["bottom"] = ItemKind.Bottom, ["onepiece"] = ItemKind.OnePiece,
            ["legwear"] = ItemKind.Legwear, ["shoes"] = ItemKind.Shoes, ["accessory"] = ItemKind.Accessory
        };

        static readonly Dictionary<string, ColorCategory> Categories = new Dictionary<string, ColorCategory>(StringComparer.Ordinal)
        {
            ["skin"] = ColorCategory.Skin, ["hair"] = ColorCategory.Hair, ["eye"] = ColorCategory.Eye
        };

        static readonly Dictionary<string, FaceFeature> Features = new Dictionary<string, FaceFeature>(StringComparer.Ordinal)
        {
            ["eye"] = FaceFeature.Eye, ["nose"] = FaceFeature.Nose, ["mouth"] = FaceFeature.Mouth, ["ear"] = FaceFeature.Ear, ["brow"] = FaceFeature.Brow
        };

        static readonly Dictionary<string, ColorUnlock> Unlocks = new Dictionary<string, ColorUnlock>(StringComparer.Ordinal)
        {
            ["free"] = ColorUnlock.Free, ["item"] = ColorUnlock.Item, ["achievement"] = ColorUnlock.Achievement
        };

        public static string Of(ItemKind v) => Name(Kinds, v);
        public static string Of(ColorCategory v) => Name(Categories, v);
        public static string Of(FaceFeature v) => Name(Features, v);
        public static string Of(ColorUnlock v) => Name(Unlocks, v);
        public static string Of(StatGroup v) => v.ToString();
        public static string Of(BodyRegion v) => v.ToString();
        public static string Of(BrowColorMode v) => v == BrowColorMode.FollowHair ? "followHair" : "explicit";

        public static bool TryParse(string s, out ItemKind v) => Kinds.TryGetValue(s ?? "", out v);
        public static bool TryParse(string s, out ColorCategory v) => Categories.TryGetValue(s ?? "", out v);
        public static bool TryParse(string s, out FaceFeature v) => Features.TryGetValue(s ?? "", out v);
        public static bool TryParse(string s, out ColorUnlock v) => Unlocks.TryGetValue(s ?? "", out v);
        public static bool TryParse(string s, out StatGroup v) => TryParseExact(s, out v);
        public static bool TryParse(string s, out BodyRegion v) => TryParseExact(s, out v);

        public static bool TryParse(string s, out BrowColorMode v)
        {
            v = BrowColorMode.FollowHair;
            if (s == "followHair") return true;
            if (s == "explicit") { v = BrowColorMode.Explicit; return true; }
            return false;
        }

        static bool TryParseExact<T>(string s, out T v) where T : struct, Enum
        {
            foreach (T value in Enum.GetValues(typeof(T)))
                if (string.Equals(value.ToString(), s, StringComparison.Ordinal)) { v = value; return true; }
            v = default;
            return false;
        }

        static string Name<T>(Dictionary<string, T> map, T v)
        {
            foreach (var pair in map)
                if (EqualityComparer<T>.Default.Equals(pair.Value, v)) return pair.Key;
            throw new ArgumentOutOfRangeException(nameof(v));
        }
    }
}
