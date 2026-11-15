using System.Collections.Generic;
using UnityEngine;
using UnityEngine.LowLevel;
using UnityEngine.PlayerLoop;

namespace MMG.Experiments.EyeView
{
    /// <summary>
    /// A player loop step inside PostLateUpdate, right after the Director late update and before renderers and skinned
    /// meshes are updated: every LateUpdate (any execution order), Animator and Timeline / Director have written their
    /// values, and nothing else runs before the frame is skinned and drawn. EyeViewController.Compose runs here.
    /// If another system replaces the player loop the step disappears; EyeViewController's watchdog notices it (the step
    /// did not run last frame), installs it again and composes from LateUpdate for that frame.
    /// </summary>
    public static class EyeViewLoop
    {
        static readonly List<EyeViewController> Active = new List<EyeViewController>();
        static readonly Dictionary<SkinnedMeshRenderer, EyeViewController> Owners = new Dictionary<SkinnedMeshRenderer, EyeViewController>();

        public static string InsertedAfter { get; private set; } = "";
        public static string InsertedBefore { get; private set; } = "";
        /// <summary>Time.frameCount of the last run of the step (-1: never)</summary>
        public static int LastRunFrame { get; private set; } = -1;
        public static int Installs { get; private set; }
        public static int Reinstalls { get; private set; }
        public static int ActiveCount => Active.Count;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        static void ResetStatics()
        {
            Active.Clear();
            Owners.Clear();
            LastRunFrame = -1;
            Installs = Reinstalls = 0;
        }

        /// <summary>false when another active controller already drives one of the renderers (the caller stays off)</summary>
        public static bool Register(EyeViewController c)
        {
            foreach (var r in c.renderers)
            {
                if (r != null && Owners.TryGetValue(r, out var other) && other != null && other != c && other.isActiveAndEnabled)
                {
                    Debug.LogError($"[EyeView] {c.name}: {r.name} is already driven by {other.name}; this controller stays off");
                    return false;
                }
            }
            foreach (var r in c.renderers)
                if (r != null) Owners[r] = c;
            EnsureInstalled();
            if (!Active.Contains(c)) Active.Add(c);
            return true;
        }

        /// <summary>
        /// every compose: the renderers of c must not be driven by another enabled controller (renderers can be
        /// assigned after OnEnable); free ones are taken. false: c must stay off.
        /// </summary>
        public static bool Claim(EyeViewController c)
        {
            foreach (var r in c.renderers)
                if (r != null && Owners.TryGetValue(r, out var other) && other != null && other != c && other.isActiveAndEnabled)
                    return false;
            foreach (var r in c.renderers)
                if (r != null) Owners[r] = c;
            return true;
        }

        public static void Unregister(EyeViewController c)
        {
            Active.Remove(c);
            var drop = new List<SkinnedMeshRenderer>();
            foreach (var kv in Owners)
                if (kv.Value == c) drop.Add(kv.Key);
            foreach (var r in drop) Owners.Remove(r);
        }

        public static bool IsInstalled()
        {
            var root = PlayerLoop.GetCurrentPlayerLoop();
            if (root.subSystemList == null) return false;
            foreach (var s in root.subSystemList)
            {
                if (s.type != typeof(PostLateUpdate) || s.subSystemList == null) continue;
                foreach (var t in s.subSystemList)
                    if (t.type == typeof(EyeViewLoop)) return true;
            }
            return false;
        }

        /// <summary>installs the step when it is missing; true if it was already there</summary>
        public static bool EnsureInstalled()
        {
            if (IsInstalled()) return true;
            var root = PlayerLoop.GetCurrentPlayerLoop();
            var subs = root.subSystemList;
            for (int i = 0; i < subs.Length; i++)
            {
                if (subs[i].type != typeof(PostLateUpdate)) continue;
                var list = new List<PlayerLoopSystem>(subs[i].subSystemList);
                list.RemoveAll(s => s.type == typeof(EyeViewLoop));
                int at = list.FindIndex(s => s.type == typeof(PostLateUpdate.DirectorLateUpdate));
                at = at >= 0 ? at + 1 : 0;
                list.Insert(at, new PlayerLoopSystem { type = typeof(EyeViewLoop), updateDelegate = Run });
                InsertedAfter = at > 0 ? list[at - 1].type.Name : "(start)";
                InsertedBefore = at + 1 < list.Count ? list[at + 1].type.Name : "(end)";
                subs[i].subSystemList = list.ToArray();
                break;
            }
            root.subSystemList = subs;
            PlayerLoop.SetPlayerLoop(root);
            if (Installs > 0) Reinstalls++;
            Installs++;
            return false;
        }

        /// <summary>the names of the PostLateUpdate steps in order (for logs)</summary>
        public static string Describe()
        {
            var names = new List<string>();
            foreach (var s in PlayerLoop.GetCurrentPlayerLoop().subSystemList)
            {
                if (s.type != typeof(PostLateUpdate)) continue;
                foreach (var t in s.subSystemList) names.Add(t.type.Name);
            }
            return string.Join(" > ", names);
        }

        static void Run()
        {
            if (!Application.isPlaying) return;
            LastRunFrame = Time.frameCount;
            for (int i = Active.Count - 1; i >= 0; i--)
            {
                var c = Active[i];
                if (c == null) { Active.RemoveAt(i); continue; }
            }
            for (int i = 0; i < Active.Count; i++)
            {
                var c = Active[i];
                if (c.composeAt == EyeViewController.ComposeAt.PlayerLoop) c.Compose();
            }
        }
    }
}
