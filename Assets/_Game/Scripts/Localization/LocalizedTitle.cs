using TMPro;
using UnityEngine;
using UnityEngine.Localization;

[RequireComponent(typeof(TextMeshProUGUI))]
public class LocalizedTitle : MonoBehaviour
{
    private const string TableName = "UI_Text";
    private const string EntryKey = "menu.title";

    private readonly LocalizedString localizedTitle =
        new LocalizedString(TableName, EntryKey);

    private TextMeshProUGUI titleText;

    private void Awake()
    {
        titleText = GetComponent<TextMeshProUGUI>();
    }

    private void OnEnable()
    {
        localizedTitle.StringChanged += UpdateTitle;
        localizedTitle.RefreshString();
    }

    private void OnDisable()
    {
        localizedTitle.StringChanged -= UpdateTitle;
    }

    private void UpdateTitle(string value)
    {
        titleText.text = value;
    }
}
