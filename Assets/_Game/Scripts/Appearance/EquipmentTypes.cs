using System.Collections.Generic;
using MMG.Data;

namespace MMG.Appearance
{
    /// <summary>Error codes of <see cref="EquipmentRules"/>. The server uses the same strings.</summary>
    public static class EquipErrors
    {
        public const string UnknownCharacter = "unknownCharacter";
        public const string BodyPresetNotAllowed = "bodyPresetNotAllowed";
        public const string UnknownSlot = "unknownSlot";
        public const string UnknownItem = "unknownItem";
        public const string ItemInactive = "itemInactive";
        public const string ItemNotOwned = "itemNotOwned";
        public const string UnknownVariant = "unknownVariant";
        public const string VariantMismatch = "variantMismatch";
        public const string VariantInactive = "variantInactive";
        public const string VariantNotOwned = "variantNotOwned";
        public const string SlotMismatch = "slotMismatch";
        public const string BodyTypeMismatch = "bodyTypeMismatch";
        public const string HairFormUnavailable = "hairFormUnavailable";
        public const string AccessoryLimit = "accessoryLimit";
        public const string NoDefaultForRequiredSlot = "noDefaultForRequiredSlot";
        public const string DefaultNotOwned = "defaultNotOwned";
        public const string UnresolvableConflict = "unresolvableConflict";
        // Validation only
        public const string DuplicateSlot = "duplicateSlot";
        public const string OnePieceIncomplete = "onePieceIncomplete";
        public const string RequiredSlotEmpty = "requiredSlotEmpty";
        public const string ExclusiveConflict = "exclusiveConflict";
    }

    public static class ChangeKinds
    {
        public const string Unequipped = "unequipped";
        public const string DefaultRestored = "defaultRestored";
        public const string Equipped = "equipped";
    }

    public static class ChangeReasons
    {
        /// <summary>Another item of the same kind took the slot.</summary>
        public const string Replaced = "replaced";
        /// <summary>A one-piece and a top or bottom cannot be worn together (auto, policy U8).</summary>
        public const string OnePiece = "onePiece";
        /// <summary>An exclusive-tag rule (auto, policy U8).</summary>
        public const string Exclusive = "exclusive";
        /// <summary>The player took it off.</summary>
        public const string Requested = "requested";
    }

    public sealed class CharacterContext
    {
        public string CharacterDefId { get; }
        public string BodyPresetId { get; }
        public CharacterContext(string characterDefId, string bodyPresetId) { CharacterDefId = characterDefId; BodyPresetId = bodyPresetId; }
    }

    /// <summary>One line of the change list shown to the player after an equip or unequip.</summary>
    public sealed class EquipChange
    {
        public string Change { get; }
        public IReadOnlyList<string> SlotIds { get; }
        public string ItemId { get; }
        public string VariantId { get; }
        /// <summary>Only for <see cref="ChangeKinds.Unequipped"/>.</summary>
        public string Reason { get; }

        public EquipChange(string change, IReadOnlyList<string> slotIds, string itemId, string variantId, string reason)
        {
            Change = change; SlotIds = slotIds; ItemId = itemId; VariantId = variantId; Reason = reason;
        }
    }

    public sealed class EquipResult
    {
        public bool Success { get; }
        /// <summary>One of <see cref="EquipErrors"/>, null on success.</summary>
        public string Error { get; }
        /// <summary>New state on success, the unchanged input state on failure.</summary>
        public EquipmentState State { get; }
        public IReadOnlyList<EquipChange> Changes { get; }

        public EquipResult(bool success, string error, EquipmentState state, IReadOnlyList<EquipChange> changes)
        {
            Success = success; Error = error; State = state; Changes = changes;
        }
    }

    public sealed class RuleIssue
    {
        public string Code { get; }
        public string SlotId { get; }
        public string ItemId { get; }
        public RuleIssue(string code, string slotId, string itemId) { Code = code; SlotId = slotId; ItemId = itemId; }
        public override string ToString() => Code + " slot=" + (SlotId ?? "-") + " item=" + (ItemId ?? "-");
    }
}
