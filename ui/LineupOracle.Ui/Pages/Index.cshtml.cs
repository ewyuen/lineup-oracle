using System.Globalization;
using LineupOracle.Ui;
using LineupOracle.Ui.Services;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using Microsoft.AspNetCore.Localization;
using Microsoft.Extensions.Localization;

namespace LineupOracle.Ui.Pages;

public sealed class IndexModel(
    LineupApiClient api,
    IStringLocalizer<UiText> text,
    ILogger<IndexModel> logger) : PageModel
{
    private string? _sessionId;

    public IReadOnlyList<MatchDto> Matches { get; private set; } = [];
    public MatchDto? SelectedMatch { get; private set; }
    public string SelectedMatchId { get; private set; } = "";
    public string SelectedClub { get; private set; } = "";
    public string Mode { get; private set; } = "analyst";
    public string Language => NormalizeLanguage(CultureInfo.CurrentUICulture.Name);
    public string? FavouriteClub => Request.Cookies[AppCookies.FavouriteClub];
    public LineupDto? Lineup { get; private set; }
    public bool IsUnavailable { get; private set; }
    public string? ApiError { get; private set; }
    public string? NewsMessage { get; private set; }
    public bool IsHtmx => string.Equals(Request.Headers["HX-Request"], "true", StringComparison.OrdinalIgnoreCase);

    public async Task OnGetAsync(string? matchId, string? club, string? mode, CancellationToken cancellationToken)
    {
        EnsureSessionCookie();
        Mode = NormalizeMode(mode);
        await LoadMatchesAsync(cancellationToken);
        SelectFixture(matchId, club);

        if (SelectedMatch is not null)
        {
            await LoadLineupAsync(cancellationToken);
        }
    }

    public async Task<IActionResult> OnGetLineupAsync(
        string? matchId,
        string? club,
        string? mode,
        CancellationToken cancellationToken)
    {
        EnsureSessionCookie();
        Mode = NormalizeMode(mode);
        await LoadMatchesAsync(cancellationToken);
        SelectFixture(matchId, club);

        if (SelectedMatch is null)
        {
            if (IsHtmx && IsUnavailable)
            {
                Response.Headers["HX-Retarget"] = "#service-banner";
                Response.Headers["HX-Reswap"] = "outerHTML";
                return Partial("_Banner", this);
            }

            ApiError ??= text["NoFixtures"];
            if (IsHtmx)
            {
                Response.Headers["HX-Retarget"] = "#news-message";
                Response.Headers["HX-Reswap"] = "innerHTML";
                return Partial("_NewsMessage", this);
            }

            return Page();
        }

        await LoadLineupAsync(cancellationToken);
        if (IsHtmx)
        {
            if (IsUnavailable)
            {
                Response.Headers["HX-Retarget"] = "#service-banner";
                Response.Headers["HX-Reswap"] = "outerHTML";
                return Partial("_Banner", this);
            }

            if (Lineup is null)
            {
                Response.Headers["HX-Retarget"] = "#news-message";
                Response.Headers["HX-Reswap"] = "innerHTML";
                return Partial("_NewsMessage", this);
            }

            return Partial("_Lineup", this);
        }

        return Page();
    }

    public async Task<IActionResult> OnPostNewsAsync(
        string matchId,
        string club,
        string mode,
        string? playerId,
        string? playerName,
        string? kind,
        string? newsText,
        CancellationToken cancellationToken)
    {
        EnsureSessionCookie();
        Mode = NormalizeMode(mode);
        SelectedMatchId = matchId;
        SelectedClub = club;

        var request = new TeamNewsRequest(
            matchId,
            club,
            Mode,
            Language,
            GetSessionId(),
            string.IsNullOrWhiteSpace(playerId) ? null : playerId,
            string.IsNullOrWhiteSpace(kind) ? null : kind,
            string.IsNullOrWhiteSpace(newsText) ? null : newsText);
        var result = await api.SubmitTeamNewsAsync(request, cancellationToken);

        if (!result.IsSuccess)
        {
            IsUnavailable = result.IsUnavailable;
            ApiError = result.IsUnavailable ? text["ServiceUnavailable"].Value : result.Error;
            Response.Headers["HX-Retarget"] = "#news-message";
            Response.Headers["HX-Reswap"] = "innerHTML";
            return Partial("_NewsMessage", this);
        }

        Lineup = result.Value;
        if (!string.IsNullOrWhiteSpace(playerId) && !string.IsNullOrWhiteSpace(kind))
        {
            var kindText = kind switch
            {
                "injury" => text["InjuryPast"].Value,
                "suspension" => text["SuspensionPast"].Value,
                "doubt" => text["DoubtPast"].Value,
                _ => kind
            };
            NewsMessage = text["MarkedUpdated", playerName ?? playerId, kindText].Value;
        }
        else if (!string.IsNullOrWhiteSpace(newsText))
        {
            NewsMessage = text["NewsSubmitted"].Value;
        }

        Response.Headers["HX-Retarget"] = "#lineup";
        Response.Headers["HX-Reswap"] = "outerHTML";
        return Partial("_Lineup", this);
    }

    public IActionResult OnPostLanguage(string language, string? matchId, string? club, string? mode)
    {
        var culture = NormalizeLanguage(language);
        Response.Cookies.Append(
            AppCookies.Language,
            CookieRequestCultureProvider.MakeCookieValue(new RequestCulture(culture)),
            PreferenceCookieOptions());
        return RedirectToPage("/Index", new { matchId, club, mode = NormalizeMode(mode) });
    }

    public async Task<IActionResult> OnPostFavouriteAsync(
        string favouriteClub,
        string? matchId,
        string? club,
        string? mode,
        CancellationToken cancellationToken)
    {
        if (string.IsNullOrWhiteSpace(favouriteClub))
        {
            return BadRequest();
        }

        await LoadMatchesAsync(cancellationToken);
        SelectFixture(matchId, club);
        if (SelectedMatch is null ||
            (favouriteClub != SelectedMatch.HomeClub && favouriteClub != SelectedMatch.AwayClub))
        {
            return BadRequest();
        }

        Response.Cookies.Append(AppCookies.FavouriteClub, favouriteClub, PreferenceCookieOptions());
        return RedirectToPage("/Index", new { matchId, club = favouriteClub, mode = NormalizeMode(mode) });
    }

    private async Task LoadMatchesAsync(CancellationToken cancellationToken)
    {
        var result = await api.GetMatchesAsync(cancellationToken);
        if (result.IsSuccess)
        {
            Matches = result.Value!;
            return;
        }

        IsUnavailable = result.IsUnavailable;
        ApiError = result.IsUnavailable ? text["ServiceUnavailable"].Value : result.Error;
        logger.LogWarning("Could not load matches from the lineup API: {ApiError}", ApiError);
    }

    private void SelectFixture(string? matchId, string? club)
    {
        SelectedMatch = Matches.FirstOrDefault(match => match.MatchId == matchId)
            ?? Matches.FirstOrDefault();
        if (SelectedMatch is null)
        {
            SelectedMatchId = "";
            SelectedClub = "";
            return;
        }

        SelectedMatchId = SelectedMatch.MatchId;
        SelectedClub = club is not null &&
            (club == SelectedMatch.HomeClub || club == SelectedMatch.AwayClub)
            ? club
            : FavouriteClub is not null &&
              (FavouriteClub == SelectedMatch.HomeClub || FavouriteClub == SelectedMatch.AwayClub)
                ? FavouriteClub
                : SelectedMatch.HomeClub;
    }

    private async Task LoadLineupAsync(CancellationToken cancellationToken)
    {
        if (SelectedMatch is null || string.IsNullOrWhiteSpace(SelectedClub))
        {
            return;
        }

        var result = await api.PredictAsync(
            new PredictionRequest(SelectedMatchId, SelectedClub, Mode, Language, GetSessionId()),
            cancellationToken);
        if (result.IsSuccess)
        {
            Lineup = result.Value;
            IsUnavailable = false;
            ApiError = null;
            return;
        }

        IsUnavailable = result.IsUnavailable;
        ApiError = result.IsUnavailable ? text["ServiceUnavailable"].Value : result.Error;
        logger.LogWarning("Could not load a lineup from the API: {ApiError}", ApiError);
    }

    private void EnsureSessionCookie()
    {
        if (Request.Cookies.TryGetValue(AppCookies.SessionId, out var sessionId) &&
            !string.IsNullOrWhiteSpace(sessionId) &&
            sessionId.Length <= 64)
        {
            _sessionId = sessionId;
            return;
        }

        _sessionId = Guid.NewGuid().ToString("N");
        Response.Cookies.Append(AppCookies.SessionId, _sessionId, PreferenceCookieOptions());
    }

    private string GetSessionId() =>
        _sessionId ?? throw new InvalidOperationException("The session-id cookie was not created for this request.");

    private CookieOptions PreferenceCookieOptions() => new()
    {
        HttpOnly = true,
        SameSite = SameSiteMode.Lax,
        Secure = Request.IsHttps,
        IsEssential = true,
        Expires = DateTimeOffset.UtcNow.AddDays(30)
    };

    private static string NormalizeMode(string? mode) => mode == "fan" ? "fan" : "analyst";

    private static string NormalizeLanguage(string? language) =>
        language is "es" or "zh-Hant" ? language : "en";
}
