using System;
using System.Collections.Generic;
using MMG.Data;

namespace MMG.Appearance
{
    public enum SupportKind { BodyPreset, FaceStyle, Item }

    public enum SupportStatus { Supported, Missing, RevisionMismatch }

    /// <summary>One thing a renderer can draw. A null variant id means every variant of the item.</summary>
    public sealed class RendererSupportEntry
    {
        public SupportKind Kind { get; }
        public string Id { get; }
        public string VariantId { get; }
        public int MinBaseRevision { get; }
        public int? MaxBaseRevision { get; }

        public RendererSupportEntry(SupportKind kind, string id, string variantId, int minBaseRevision, int? maxBaseRevision)
        {
            Kind = kind; Id = id; VariantId = variantId; MinBaseRevision = minBaseRevision; MaxBaseRevision = maxBaseRevision;
        }
    }

    /// <summary>
    /// What one renderer base (e.g. Cubism MainGirlfriend r28, 3D skeleton v1) can draw, by common ids only.
    /// Built from each renderer's own mapping data (S3, S8).
    /// </summary>
    public sealed class RendererSupportManifest
    {
        public string RendererKind { get; }
        public string BaseKey { get; }
        public int BaseRevision { get; }
        public IReadOnlyList<RendererSupportEntry> Entries { get; }

        public RendererSupportManifest(string rendererKind, string baseKey, int baseRevision, IReadOnlyList<RendererSupportEntry> entries)
        {
            RendererKind = rendererKind; BaseKey = baseKey; BaseRevision = baseRevision; Entries = entries;
        }
    }

    public sealed class SupportResult
    {
        public SupportKind Kind { get; }
        public string Id { get; }
        public string VariantId { get; }
        public SupportStatus Status { get; }
        public SupportResult(SupportKind kind, string id, string variantId, SupportStatus status) { Kind = kind; Id = id; VariantId = variantId; Status = status; }
    }

    public sealed class RendererSupportReport
    {
        public string RendererKind { get; }
        public int BaseRevision { get; }
        public IReadOnlyList<SupportResult> Results { get; }
        public bool AllSupported { get; }

        public RendererSupportReport(string rendererKind, int baseRevision, IReadOnlyList<SupportResult> results)
        {
            RendererKind = rendererKind; BaseRevision = baseRevision; Results = results;
            bool all = true;
            foreach (var r in results) if (r.Status != SupportStatus.Supported) all = false;
            AllSupported = all;
        }
    }

    /// <summary>Checks a resolved appearance against what a renderer base supports (missing → placeholder, revision mismatch → warning).</summary>
    public static class RendererSupportChecker
    {
        public static RendererSupportReport Check(ResolvedAppearance appearance, RendererSupportManifest manifest)
        {
            var results = new List<SupportResult>
            {
                One(manifest, SupportKind.BodyPreset, appearance.BodyPresetId, null)
            };
            foreach (FaceFeature f in Enum.GetValues(typeof(FaceFeature)))
                results.Add(One(manifest, SupportKind.FaceStyle, appearance.Face.Get(f), null));
            foreach (var item in appearance.Items)
                results.Add(One(manifest, SupportKind.Item, item.ItemId, item.VariantId));
            return new RendererSupportReport(manifest.RendererKind, manifest.BaseRevision, results);
        }

        static SupportResult One(RendererSupportManifest m, SupportKind kind, string id, string variantId)
        {
            bool matched = false;
            foreach (var e in m.Entries)
            {
                if (e.Kind != kind || e.Id != id || (e.VariantId != null && e.VariantId != variantId)) continue;
                matched = true;
                if (m.BaseRevision >= e.MinBaseRevision && (!e.MaxBaseRevision.HasValue || m.BaseRevision <= e.MaxBaseRevision.Value))
                    return new SupportResult(kind, id, variantId, SupportStatus.Supported);
            }
            return new SupportResult(kind, id, variantId, matched ? SupportStatus.RevisionMismatch : SupportStatus.Missing);
        }
    }
}
