using System;
using System.Collections.Generic;
using MMG.Data;

namespace MMG.Appearance
{
    /// <summary>
    /// Gameplay equipment rules (05 document 7-2, 7-3). The server validates the same rules in TypeScript; both sides
    /// are checked against Shared/testcases/appearance. Rejections never change the state.
    /// </summary>
    public static class EquipmentRules
    {
        public static EquipResult Equip(Catalog catalog, CharacterContext context, EquipmentState state, string itemId, string variantId, OwnershipView owned)
        {
            if (!TryContext(catalog, context, out var character, out var body, out string error)) return Fail(error, state);
            if (!catalog.TryGetItem(itemId, out var item)) return Fail(EquipErrors.UnknownItem, state);
            if (!item.IsActive) return Fail(EquipErrors.ItemInactive, state);
            if (!owned.OwnsItem(itemId)) return Fail(EquipErrors.ItemNotOwned, state);
            if (!TryChooseVariant(catalog, item, variantId, owned, out var variant, out error)) return Fail(error, state);
            if (!item.Fits(body.BodyType)) return Fail(EquipErrors.BodyTypeMismatch, state);

            var w = new Working(catalog, state);
            bool alreadyWorn = true;
            foreach (var slotId in item.Occupies)
                if (!w.TryGet(slotId, out var cur) || cur.ItemId != item.ItemId || cur.VariantId != variant.VariantId) alreadyWorn = false;
            if (alreadyWorn) return new EquipResult(true, null, state, new EquipChange[0]);

            var changes = new List<EquipChange>();
            foreach (var slotId in w.SortSlots(item.Occupies))
            {
                if (!w.TryGet(slotId, out var occupant)) continue;
                catalog.TryGetItem(occupant.ItemId, out var occupantItem);
                bool onePiece = occupant.ItemId != item.ItemId &&
                                (item.Kind == ItemKind.OnePiece || (occupantItem != null && occupantItem.Kind == ItemKind.OnePiece));
                changes.Add(w.RemoveItem(occupant.ItemId, onePiece ? ChangeReasons.OnePiece : ChangeReasons.Replaced));
            }
            foreach (var otherId in w.ItemIdsInSlotOrder())
                if (catalog.TryGetItem(otherId, out var other) && Conflicts(catalog.Rules, item, other))
                    changes.Add(w.RemoveItem(otherId, ChangeReasons.Exclusive));

            w.Put(item, variant.VariantId);
            if (!TryRestoreDefaults(catalog, character, body, owned, w, changes, out error)) return Fail(error, state);
            if (!HairFormsSatisfied(catalog, w)) return Fail(EquipErrors.HairFormUnavailable, state);
            if (catalog.Rules.AccessoryMaxCount.HasValue && w.AccessoryCount() > catalog.Rules.AccessoryMaxCount.Value)
                return Fail(EquipErrors.AccessoryLimit, state);

            changes.Add(new EquipChange(ChangeKinds.Equipped, w.SortSlots(item.Occupies), item.ItemId, variant.VariantId, null));
            return Ok(catalog, w, state, changes);
        }

        public static EquipResult Unequip(Catalog catalog, CharacterContext context, EquipmentState state, string slotId, OwnershipView owned)
        {
            if (!TryContext(catalog, context, out var character, out var body, out string error)) return Fail(error, state);
            if (!catalog.TryGetSlot(slotId, out _)) return Fail(EquipErrors.UnknownSlot, state);
            var w = new Working(catalog, state);
            if (!w.TryGet(slotId, out var occupant)) return new EquipResult(true, null, state, new EquipChange[0]);

            var occupantSlots = w.SlotsOf(occupant.ItemId);
            bool touchesRequired = false, isDefault = true;
            foreach (var s in occupantSlots)
            {
                if (catalog.TryGetSlot(s, out var slot) && slot.Required) touchesRequired = true;
                var d = character.DefaultFor(s);
                if (d == null || d.ItemId != occupant.ItemId || d.VariantId != occupant.VariantId) isDefault = false;
            }
            if (touchesRequired && isDefault) return new EquipResult(true, null, state, new EquipChange[0]);

            var changes = new List<EquipChange> { w.RemoveItem(occupant.ItemId, ChangeReasons.Requested) };
            if (!TryRestoreDefaults(catalog, character, body, owned, w, changes, out error)) return Fail(error, state);
            if (!HairFormsSatisfied(catalog, w)) return Fail(EquipErrors.HairFormUnavailable, state);
            return Ok(catalog, w, state, changes);
        }

        /// <summary>Full check of a stored state (server on save and load). Issues are sorted by slot order, code, item.</summary>
        public static List<RuleIssue> Validate(Catalog catalog, CharacterContext context, EquipmentState state, OwnershipView owned)
        {
            var issues = new List<RuleIssue>();
            if (!TryContext(catalog, context, out _, out var body, out string error))
            {
                issues.Add(new RuleIssue(error, null, null));
                return issues;
            }

            var bySlot = new Dictionary<string, EquipmentEntry>(StringComparer.Ordinal);
            foreach (var e in state.Entries)
            {
                if (bySlot.ContainsKey(e.SlotId)) { issues.Add(new RuleIssue(EquipErrors.DuplicateSlot, e.SlotId, e.ItemId)); continue; }
                bySlot.Add(e.SlotId, e);
                if (!catalog.TryGetSlot(e.SlotId, out _)) issues.Add(new RuleIssue(EquipErrors.UnknownSlot, e.SlotId, e.ItemId));
            }

            var w = new Working(catalog, state);
            var known = new List<ItemDefinition>();
            foreach (var itemId in w.ItemIdsInSlotOrder())
            {
                var slots = w.SlotsOf(itemId);
                string first = slots[0];
                w.TryGet(first, out var entry);
                if (!catalog.TryGetItem(itemId, out var item)) { issues.Add(new RuleIssue(EquipErrors.UnknownItem, first, itemId)); continue; }
                known.Add(item);
                if (!item.IsActive) issues.Add(new RuleIssue(EquipErrors.ItemInactive, first, itemId));
                foreach (var s in slots)
                    if (!Contains(item.Occupies, s)) issues.Add(new RuleIssue(EquipErrors.SlotMismatch, s, itemId));
                if (item.Occupies.Count > 1)
                    foreach (var s in item.Occupies)
                        if (!w.TryGet(s, out var other) || other.ItemId != itemId || other.VariantId != entry.VariantId)
                            issues.Add(new RuleIssue(EquipErrors.OnePieceIncomplete, s, itemId));

                if (!catalog.TryGetVariant(entry.VariantId, out var variant)) issues.Add(new RuleIssue(EquipErrors.UnknownVariant, first, itemId));
                else if (variant.ItemId != itemId) issues.Add(new RuleIssue(EquipErrors.VariantMismatch, first, itemId));
                else if (!variant.IsActive) issues.Add(new RuleIssue(EquipErrors.VariantInactive, first, itemId));

                if (!owned.OwnsItem(itemId)) issues.Add(new RuleIssue(EquipErrors.ItemNotOwned, first, itemId));
                else if (!owned.OwnsVariant(itemId, entry.VariantId)) issues.Add(new RuleIssue(EquipErrors.VariantNotOwned, first, itemId));
                if (!item.Fits(body.BodyType)) issues.Add(new RuleIssue(EquipErrors.BodyTypeMismatch, first, itemId));
            }

            foreach (var slot in catalog.Slots)
                if (slot.Required && !w.TryGet(slot.SlotId, out _)) issues.Add(new RuleIssue(EquipErrors.RequiredSlotEmpty, slot.SlotId, null));

            catalog.TryGetItem(w.HairItemId(), out var hair);
            foreach (var item in known)
                foreach (var req in catalog.Rules.HairFormRequirements)
                    if (item.HasTag(req.Tag) && (hair == null || !hair.SupportsHairForm(req.HairForm)))
                        issues.Add(new RuleIssue(EquipErrors.HairFormUnavailable, w.SlotsOf(item.ItemId)[0], item.ItemId));

            for (int a = 0; a < known.Count; a++)
                for (int b = a + 1; b < known.Count; b++)
                    if (Conflicts(catalog.Rules, known[a], known[b]))
                        issues.Add(new RuleIssue(EquipErrors.ExclusiveConflict, w.SlotsOf(known[b].ItemId)[0], known[b].ItemId));

            if (catalog.Rules.AccessoryMaxCount.HasValue && w.AccessoryCount() > catalog.Rules.AccessoryMaxCount.Value)
                issues.Add(new RuleIssue(EquipErrors.AccessoryLimit, null, null));

            issues.Sort((x, y) =>
            {
                int c = catalog.SlotOrder(x.SlotId).CompareTo(catalog.SlotOrder(y.SlotId));
                if (c != 0) return c;
                c = string.CompareOrdinal(x.SlotId, y.SlotId);
                if (c != 0) return c;
                c = string.CompareOrdinal(x.Code, y.Code);
                return c != 0 ? c : string.CompareOrdinal(x.ItemId, y.ItemId);
            });
            return issues;
        }

        public static bool Conflicts(CatalogRules rules, ItemDefinition a, ItemDefinition b)
        {
            if (a.ItemId == b.ItemId) return false;
            foreach (var r in rules.Exclusive)
                if ((a.HasTag(r.TagA) && b.HasTag(r.TagB)) || (a.HasTag(r.TagB) && b.HasTag(r.TagA))) return true;
            return false;
        }

        static bool TryContext(Catalog catalog, CharacterContext context, out CharacterDefinition character, out BodyPreset body, out string error)
        {
            body = null;
            error = null;
            if (!catalog.TryGetCharacter(context.CharacterDefId, out character)) { error = EquipErrors.UnknownCharacter; return false; }
            if (!character.AllowsBodyPreset(context.BodyPresetId) || !catalog.TryGetBodyPreset(context.BodyPresetId, out body))
            {
                error = EquipErrors.BodyPresetNotAllowed;
                return false;
            }
            return true;
        }

        /// <summary>Requested variant, else the default variant if owned, else the first owned active variant by id (policy U3).</summary>
        static bool TryChooseVariant(Catalog catalog, ItemDefinition item, string variantId, OwnershipView owned, out ItemVariant variant, out string error)
        {
            error = null;
            if (variantId != null)
            {
                if (!catalog.TryGetVariant(variantId, out variant)) { error = EquipErrors.UnknownVariant; return false; }
                if (variant.ItemId != item.ItemId) { error = EquipErrors.VariantMismatch; return false; }
                if (!variant.IsActive) { error = EquipErrors.VariantInactive; return false; }
                if (!owned.OwnsVariant(item.ItemId, variantId)) { error = EquipErrors.VariantNotOwned; return false; }
                return true;
            }
            if (catalog.TryGetVariant(item.DefaultVariantId, out variant) && variant.IsActive && owned.OwnsVariant(item.ItemId, variant.VariantId))
                return true;
            foreach (var v in catalog.VariantsOf(item.ItemId))
                if (v.IsActive && owned.OwnsVariant(item.ItemId, v.VariantId)) { variant = v; return true; }
            variant = null;
            error = EquipErrors.VariantNotOwned;
            return false;
        }

        /// <summary>Fills empty required slots with the character's default items (policy U12).</summary>
        static bool TryRestoreDefaults(Catalog catalog, CharacterDefinition character, BodyPreset body, OwnershipView owned,
            Working w, List<EquipChange> changes, out string error)
        {
            error = null;
            foreach (var slot in catalog.Slots)
            {
                if (!slot.Required || w.TryGet(slot.SlotId, out _)) continue;
                var d = character.DefaultFor(slot.SlotId);
                if (d == null || !catalog.TryGetItem(d.ItemId, out var item) || !item.IsActive || !item.Fits(body.BodyType) ||
                    !catalog.TryGetVariant(d.VariantId, out var v) || v.ItemId != item.ItemId || !v.IsActive)
                {
                    error = EquipErrors.NoDefaultForRequiredSlot;
                    return false;
                }
                if (!owned.OwnsVariant(item.ItemId, d.VariantId)) { error = EquipErrors.DefaultNotOwned; return false; }
                foreach (var s in item.Occupies)
                    if (w.TryGet(s, out _)) { error = EquipErrors.NoDefaultForRequiredSlot; return false; }

                w.Put(item, d.VariantId);
                changes.Add(new EquipChange(ChangeKinds.DefaultRestored, w.SortSlots(item.Occupies), item.ItemId, d.VariantId, null));
                foreach (var otherId in w.ItemIdsInSlotOrder())
                {
                    if (!catalog.TryGetItem(otherId, out var other) || !Conflicts(catalog.Rules, item, other)) continue;
                    foreach (var s in w.SlotsOf(otherId))
                        if (catalog.TryGetSlot(s, out var os) && os.Required) { error = EquipErrors.UnresolvableConflict; return false; }
                    changes.Add(w.RemoveItem(otherId, ChangeReasons.Exclusive));
                }
            }
            return true;
        }

        static bool HairFormsSatisfied(Catalog catalog, Working w)
        {
            catalog.TryGetItem(w.HairItemId(), out var hair);
            foreach (var itemId in w.ItemIdsInSlotOrder())
            {
                if (!catalog.TryGetItem(itemId, out var item)) continue;
                foreach (var req in catalog.Rules.HairFormRequirements)
                    if (item.HasTag(req.Tag) && (hair == null || !hair.SupportsHairForm(req.HairForm))) return false;
            }
            return true;
        }

        static EquipResult Fail(string error, EquipmentState state) => new EquipResult(false, error, state, new EquipChange[0]);

        static EquipResult Ok(Catalog catalog, Working w, EquipmentState input, List<EquipChange> changes)
        {
            changes.Sort((a, b) =>
            {
                int c = Rank(a.Change).CompareTo(Rank(b.Change));
                if (c != 0) return c;
                c = catalog.SlotOrder(a.SlotIds[0]).CompareTo(catalog.SlotOrder(b.SlotIds[0]));
                return c != 0 ? c : string.CompareOrdinal(a.ItemId, b.ItemId);
            });
            var state = new EquipmentState(input.CharacterId, w.Entries(), input.Version, catalog.Rules.RulesVersion);
            return new EquipResult(true, null, state, changes);
        }

        static int Rank(string change) => change == ChangeKinds.Unequipped ? 0 : change == ChangeKinds.DefaultRestored ? 1 : 2;

        static bool Contains(IReadOnlyList<string> list, string s)
        {
            for (int i = 0; i < list.Count; i++) if (list[i] == s) return true;
            return false;
        }

        /// <summary>Mutable copy of an equipment state keyed by slot.</summary>
        sealed class Working
        {
            readonly Catalog catalog;
            readonly Dictionary<string, EquipmentEntry> bySlot = new Dictionary<string, EquipmentEntry>(StringComparer.Ordinal);

            public Working(Catalog catalog, EquipmentState state)
            {
                this.catalog = catalog;
                foreach (var e in state.Entries)
                    if (!bySlot.ContainsKey(e.SlotId)) bySlot.Add(e.SlotId, e);
            }

            public bool TryGet(string slotId, out EquipmentEntry entry) => bySlot.TryGetValue(slotId, out entry);

            public string HairItemId() => bySlot.TryGetValue("hair", out var e) ? e.ItemId : null;

            public List<string> SortSlots(IEnumerable<string> slots)
            {
                var list = new List<string>(slots);
                list.Sort((a, b) =>
                {
                    int c = catalog.SlotOrder(a).CompareTo(catalog.SlotOrder(b));
                    return c != 0 ? c : string.CompareOrdinal(a, b);
                });
                return list;
            }

            public List<string> SlotsOf(string itemId)
            {
                var slots = new List<string>();
                foreach (var pair in bySlot) if (pair.Value.ItemId == itemId) slots.Add(pair.Key);
                return SortSlots(slots);
            }

            /// <summary>Distinct item ids ordered by their first slot.</summary>
            public List<string> ItemIdsInSlotOrder()
            {
                var ids = new List<string>();
                foreach (var slotId in SortSlots(bySlot.Keys))
                {
                    string id = bySlot[slotId].ItemId;
                    if (!ids.Contains(id)) ids.Add(id);
                }
                return ids;
            }

            public EquipChange RemoveItem(string itemId, string reason)
            {
                var slots = SlotsOf(itemId);
                string variantId = bySlot[slots[0]].VariantId;
                foreach (var s in slots) bySlot.Remove(s);
                return new EquipChange(ChangeKinds.Unequipped, slots, itemId, variantId, reason);
            }

            public void Put(ItemDefinition item, string variantId)
            {
                foreach (var s in item.Occupies) bySlot[s] = new EquipmentEntry(s, item.ItemId, variantId);
            }

            public int AccessoryCount()
            {
                int n = 0;
                foreach (var pair in bySlot)
                    if (catalog.TryGetSlot(pair.Key, out var slot) && slot.IsAccessory) n++;
                return n;
            }

            public List<EquipmentEntry> Entries()
            {
                var list = new List<EquipmentEntry>();
                foreach (var s in SortSlots(bySlot.Keys)) list.Add(bySlot[s]);
                return list;
            }
        }
    }
}
