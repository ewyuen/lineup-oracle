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
    IConfiguration configuration,
    ILogger<IndexModel> logger) : PageModel
{
    private const int RecentOnFirstPoll = 3;
    private string? _sessionId;
    private string? _favouriteClub;
    private string? _languageOverride;

    public IReadOnlyList<MatchDto> Matches { get; private set; } = [];
    public MatchDto? SelectedMatch { get; private set; }
    public string SelectedMatchId { get; private set; } = "";
    public string SelectedClub { get; private set; } = "";
    public string Mode { get; private set; } = "analyst";
    public string Language => NormalizeLanguage(_languageOverride ?? CultureInfo.CurrentUICulture.Name);
    public string? FavouriteClub => _favouriteClub ?? Request.Cookies[AppCookies.FavouriteClub];
    public LineupDto? Lineup { get; private set; }
    public bool IsUnavailable { get; private set; }
    public string? ApiError { get; private set; }
    public string? NewsMessage { get; private set; }
    public string? RetryMatchId { get; private set; }
    public string? RetryClub { get; private set; }
    public bool IsSelectionFailure { get; private set; }
    public IReadOnlyList<NewsEntry> NewsEntries { get; private set; } = [];
    public long NewsSeq { get; private set; }
    public bool RefreshNewsBar { get; private set; }
    public int PollSeconds => configuration.GetValue("News:PollSeconds", 10);
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
        CancellationToken cancellationToken,
        string? previousMatchId = null,
        string? previousClub = null,
        bool selectionUpdate = false)
    {
        EnsureSessionCookie();
        Mode = NormalizeMode(mode);
        await LoadMatchesAsync(cancellationToken);
        SelectFixture(matchId, club);

        if (SelectedMatch is null)
        {
            if (IsHtmx && selectionUpdate && IsUnavailable)
            {
                return SelectionFailure(previousMatchId, previousClub, matchId, club);
            }

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
            if (selectionUpdate && Lineup is null)
            {
                return SelectionFailure(previousMatchId, previousClub, SelectedMatchId, SelectedClub);
            }

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

            if (selectionUpdate)
            {
                PushSelectionUrl();
            }

            return Partial("_Workspace", this);
        }

        return Page();
    }

    // Background poll: 204 (no swap) when there is nothing new or the API is down.
    public async Task<IActionResult> OnGetNewsAsync(long? since, string? matchId, string? club, string? language, CancellationToken cancellationToken)
    {
        var result = await api.GetNewsAsync(since, matchId, club, language is null ? Language : NormalizeLanguage(language), cancellationToken);
        if (!result.IsSuccess)
        {
            return new StatusCodeResult(StatusCodes.Status204NoContent);
        }

        var news = result.Value!;
        var resynced = since is null || news.LatestSeq < since; // first poll, or the API restarted and numbering began again
        if (!resynced && news.Items.Count == 0)
        {
            return new StatusCodeResult(StatusCodes.Status204NoContent);
        }

        var items = resynced ? news.Items.TakeLast(RecentOnFirstPoll).ToList() : news.Items;
        NewsEntries = NewsEntry.From(items);
        NewsSeq = news.LatestSeq;
        if (news.Changed || (resynced && since is not null))
        {
            Response.Headers["HX-Trigger"] = "lineup-changed";
        }

        return Partial("_NewsItems", this);
    }

    public async Task<IActionResult> OnPostRestartFeedAsync(string? matchId, string? club, CancellationToken cancellationToken)
    {
        var restart = await api.RestartFeedAsync(cancellationToken);
        if (!restart.IsSuccess)
        {
            IsUnavailable = restart.IsUnavailable;
            ApiError = restart.IsUnavailable ? text["ServiceUnavailable"].Value : restart.Error;
            Response.Headers["HX-Retarget"] = "#news-message";
            Response.Headers["HX-Reswap"] = "innerHTML";
            return Partial("_NewsMessage", this);
        }

        SelectedMatchId = matchId ?? "";
        SelectedClub = club ?? "";
        NewsSeq = restart.Value!.LatestSeq;
        // The marker and the first item are the last two entries; show them now instead of waiting for the next poll.
        var recent = await api.GetNewsAsync(Math.Max(0, NewsSeq - 2), matchId, club, Language, cancellationToken);
        if (recent.IsSuccess)
        {
            NewsEntries = NewsEntry.From(recent.Value!.Items);
            NewsSeq = recent.Value.LatestSeq;
        }

        Response.Headers["HX-Retarget"] = "#news-bar";
        Response.Headers["HX-Reswap"] = "outerHTML";
        Response.Headers["HX-Trigger"] = "lineup-changed";
        return Partial("_NewsBar", this);
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
        if (Lineup?.News is { Outcome: "posted" })
        {
            NewsMessage = text["NewsPosted"].Value;
        }
        else if (Lineup?.News is { Outcome: "applied", Kind: not null } applied)
        {
            var name = applied.PlayerName ?? playerName ?? playerId ?? "";
            NewsMessage = applied.Club == club
                ? text["MarkedUpdated", name, KindPast(applied.Kind)].Value
                : text["MarkedUpdatedClub", name, KindPast(applied.Kind), applied.Club].Value;
        }
        else if (!string.IsNullOrWhiteSpace(playerId) && !string.IsNullOrWhiteSpace(kind))
        {
            NewsMessage = text["MarkedUpdated", playerName ?? playerId, KindPast(kind)].Value;
        }
        else if (!string.IsNullOrWhiteSpace(newsText))
        {
            NewsMessage = text["NewsSubmitted"].Value;
        }

        Response.Headers["HX-Retarget"] = "#lineup";
        Response.Headers["HX-Reswap"] = "outerHTML";
        return Partial("_Lineup", this);
    }

    private string KindPast(string kind) => kind switch
    {
        "injury" => text["InjuryPast"].Value,
        "suspension" => text["SuspensionPast"].Value,
        "doubt" => text["DoubtPast"].Value,
        "recovered" => text["RecoveredPast"].Value,
        "cleared" => text["ClearedPast"].Value,
        "fit" => text["FitPast"].Value,
        _ => kind
    };

    public async Task<IActionResult> OnPostLanguageAsync(
        string language,
        string? matchId,
        string? club,
        string? mode,
        CancellationToken cancellationToken)
    {
        var culture = NormalizeLanguage(language);
        Response.Cookies.Append(
            AppCookies.Language,
            CookieRequestCultureProvider.MakeCookieValue(new RequestCulture(culture)),
            PreferenceCookieOptions());

        if (!IsHtmx)
        {
            return RedirectToPage("/Index", new { matchId, club, mode = NormalizeMode(mode) });
        }

        _languageOverride = culture;
        EnsureSessionCookie();
        Mode = NormalizeMode(mode);
        await LoadMatchesAsync(cancellationToken);
        SelectFixture(matchId, club);

        if (SelectedMatch is null)
        {
            ApiError ??= text["NoFixtures"].Value;
            Response.Headers["HX-Retarget"] = IsUnavailable ? "#service-banner" : "#news-message";
            Response.Headers["HX-Reswap"] = IsUnavailable ? "outerHTML" : "innerHTML";
            return IsUnavailable ? Partial("_Banner", this) : Partial("_NewsMessage", this);
        }

        await LoadLineupAsync(cancellationToken);
        if (Lineup is null)
        {
            Response.Headers["HX-Retarget"] = IsUnavailable ? "#service-banner" : "#news-message";
            Response.Headers["HX-Reswap"] = IsUnavailable ? "outerHTML" : "innerHTML";
            return IsUnavailable ? Partial("_Banner", this) : Partial("_NewsMessage", this);
        }

        return Partial("_AppShell", this);
    }

    public async Task<IActionResult> OnPostFavouriteAsync(
        string favouriteClub,
        string? matchId,
        string? club,
        string? mode,
        CancellationToken cancellationToken,
        string? previousMatchId = null,
        string? previousClub = null)
    {
        if (string.IsNullOrWhiteSpace(favouriteClub))
        {
            return BadRequest();
        }

        EnsureSessionCookie();
        Mode = NormalizeMode(mode);
        await LoadMatchesAsync(cancellationToken);
        SelectFixture(matchId, club);
        if (SelectedMatch is null ||
            (favouriteClub != SelectedMatch.HomeClub && favouriteClub != SelectedMatch.AwayClub))
        {
            return BadRequest();
        }

        Response.Cookies.Append(AppCookies.FavouriteClub, favouriteClub, PreferenceCookieOptions());
        _favouriteClub = favouriteClub;
        var lastMatchId = previousMatchId ?? SelectedMatchId;
        var lastClub = previousClub ?? SelectedClub;
        SelectFixture(matchId, favouriteClub);
        await LoadLineupAsync(cancellationToken);

        if (IsHtmx)
        {
            if (Lineup is null)
            {
                return SelectionFailure(lastMatchId, lastClub, SelectedMatchId, SelectedClub);
            }

            PushSelectionUrl();
            return Partial("_Workspace", this);
        }

        return RedirectToPage("/Index", new { matchId, club = favouriteClub, mode = Mode });
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

    private IActionResult SelectionFailure(
        string? previousMatchId,
        string? previousClub,
        string? requestedMatchId,
        string? requestedClub)
    {
        RetryMatchId = requestedMatchId;
        RetryClub = requestedClub;
        IsSelectionFailure = true;

        if (!string.IsNullOrWhiteSpace(previousMatchId))
        {
            SelectFixture(previousMatchId, previousClub);
        }

        if (IsUnavailable)
        {
            Response.Headers["HX-Retarget"] = "#service-banner";
            Response.Headers["HX-Reswap"] = "outerHTML";
        }
        else
        {
            Response.Headers["HX-Retarget"] = "#news-message";
            Response.Headers["HX-Reswap"] = "innerHTML";
        }

        return Partial("_SelectionError", this);
    }

    private void PushSelectionUrl()
    {
        RefreshNewsBar = true; // a new selection starts the ticker's poll afresh, so older news cannot trigger a refresh
        Response.Headers["HX-Push-Url"] =
            $"/?matchId={Uri.EscapeDataString(SelectedMatchId)}&club={Uri.EscapeDataString(SelectedClub)}&mode={Uri.EscapeDataString(Mode)}";
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
