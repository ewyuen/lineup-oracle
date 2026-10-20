using System.Globalization;
using System.Resources;
using Microsoft.Extensions.Localization;

namespace LineupOracle.Ui.Services;

public sealed class UiTextLocalizer : IStringLocalizer<UiText>
{
    private static readonly CultureInfo EnglishCulture = CultureInfo.GetCultureInfo("en");
    private static readonly ResourceManager EnglishResources =
        new(typeof(UiText).FullName!, typeof(UiText).Assembly);

    private readonly IStringLocalizer _inner;

    public UiTextLocalizer(IStringLocalizer inner)
    {
        _inner = inner;
    }

    public LocalizedString this[string name] => GetString(_inner[name], name, []);

    public LocalizedString this[string name, params object[] arguments] =>
        GetString(_inner[name, arguments], name, arguments);

    public IEnumerable<LocalizedString> GetAllStrings(bool includeParentCultures) =>
        _inner.GetAllStrings(includeParentCultures);

    private static LocalizedString GetString(LocalizedString localized, string name, object[] arguments)
    {
        if (!localized.ResourceNotFound)
        {
            return localized;
        }

        var english = EnglishResources.GetString(name, EnglishCulture);
        if (english is null)
        {
            return localized;
        }

        var value = arguments.Length == 0
            ? english
            : string.Format(CultureInfo.CurrentCulture, english, arguments);
        return new LocalizedString(name, value, resourceNotFound: false);
    }
}
