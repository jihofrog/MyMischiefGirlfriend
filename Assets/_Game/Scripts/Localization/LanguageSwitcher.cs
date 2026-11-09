
using System.Collections;
using UnityEngine;
using UnityEngine.Localization;
using UnityEngine.Localization.Settings;

public class LanguageSwitcher : MonoBehaviour
{
    public void SetEnglish()
    {
        StartCoroutine(ChangeLanguage("en"));
    }

    public void SetKorean()
    {
        StartCoroutine(ChangeLanguage("ko"));
    }

    private IEnumerator ChangeLanguage(string languageCode)
    {
        // Wait until the Localization system is initialized.
        yield return LocalizationSettings.InitializationOperation;

        Locale locale =
            LocalizationSettings.AvailableLocales.GetLocale(languageCode);

        if (locale == null)
        {
            Debug.LogWarning(
                "Locale not found: " + languageCode
            );
            yield break;
        }

        LocalizationSettings.SelectedLocale = locale;

        Debug.Log(
            "Language changed to: " + languageCode
        );
    }
}
